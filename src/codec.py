""" Module that implements a generic codec """

from abc import ABC, abstractmethod
import random
from rtp import generate_rtp_packet


class GenericCodec(ABC):
    """ Generic Abstract class for a codec """
    def __init__(self, params, queue):
        self.marker = 1
        self.params = params
        self.queue = queue

        self.sequence_number = random.randint(0, 10000)
        self.timestamp = random.randint(0, 10000)
        self.ssrc = random.randint(0, 2**31)
        self.payload_type = params.payloadType

    @abstractmethod
    async def process_response(self, response):
        """ Processes the response from speach engine """

    @abstractmethod
    def get_silence(self):
        """ Returns a silence packet """

    def make_packet(self, payload):
        """ Create a RTP packet """
        packet = generate_rtp_packet({
                'version': 2,
                'padding': 0,
                'extension': 0,
                'csi_count': 0,
                'marker': self.marker,
                'payload_type': self.payload_type,
                'sequence_number': self.sequence_number,
                'timestamp': self.timestamp,
                'ssrc': self.ssrc,
                'payload': payload.hex()
            })
        self.marker = 0
        return packet


class Opus(GenericCodec):
    """ Opus codec handling """
    def __init__(self, params, queue):
        super().__init__(params, queue)

        self.name = 'opus'
        self.sample_rate = 48000
        self.bitrate = 96000
        self.container = 'ogg'

        self.ts_increment = self.sample_rate // 50  # 20ms

    async def process_response(self, response):
        pages = []
        async for data in response.aiter_bytes():
            start = 0
            while True:
                pos = data.find(b'OggS', start + 1)
                if pos == -1:
                    if not data.startswith(b'OggS'):
                        if len(pages) > 0:
                            pages[-1] += data[start:]
                    else:
                        try:
                            page = pages.pop(0)
                            self.parse_page(page)
                        finally:
                            pass
                        pages.append(data)
                    break

                if not data.startswith(b'OggS'):
                    if len(pages) > 0:
                        pages[-1] += data[:pos]
                else:
                    try:
                        page = pages.pop(0)
                        self.parse_page(page)
                    finally:
                        pass
                    pages.append(data[:pos])

                data = data[pos:]

        for page in pages:
            self.parse_page(page)

    def parse_page(self, page):
        """ Parse Ogg page """
        if not page.startswith(b'OggS'):
            return

        header = page[:27]
        # capture_pattern = header[:4]
        # version = header[4]
        # header_type = header[5]
        # granule_position = header[6:14]
        # serial_number = header[14:18]
        # sequence_number = header[18:22]
        # checksum = header[22:26]
        page_segments = header[26]
        segments_lens = page[27:27 + page_segments]

        for i in range(page_segments):
            segment_len = segments_lens[i]
            segment = page[27 + page_segments +
                           sum(segments_lens[:i]):27 +
                           page_segments +
                           sum(segments_lens[:i]) +
                           segment_len]
            if i == 0 and segment.startswith(b'OpusHead'):
                return
            if i == 0 and segment.startswith(b'OpusTags'):
                return

            rtp_packet = self.make_packet(segment)
            self.queue.put_nowait(rtp_packet)

            self.sequence_number += 1
            self.timestamp += self.ts_increment

    def get_silence(self):
        return self.make_packet(b'\xf8\xff\xfe')


class G711(GenericCodec):
    """ Generic G711 Codec handling """
    def __init__(self, params, queue):
        super().__init__(params, queue)

        self.sample_rate = 8000
        self.bitrate = 64000
        self.container = 'none'
        self.name = "g711"

        self.ts_increment = self.sample_rate // 50  # 20ms

    async def process_response(self, response):
        chunk_size = ((8000 * 8 * 20) // 1000) // 8
        buffer = bytearray()
        async for data in response.aiter_bytes():
            buffer.extend(data)
            while len(buffer) >= chunk_size:
                chunk = buffer[:chunk_size]
                buffer = buffer[chunk_size:]

                buffer_size = len(chunk)
                if buffer_size > 0:
                    payload = chunk[:buffer_size]
                    rtp_packet = self.make_packet(payload)
                    self.sequence_number += 1
                    self.timestamp += self.ts_increment
                    self.queue.put_nowait(rtp_packet)

        if len(buffer) > 0:
            payload = buffer
            rtp_packet = self.make_packet(payload)
            self.queue.put_nowait(rtp_packet)

    def get_payload_len(self):
        """ Returns payload length """
        return ((self.sample_rate * 20 * 8) // 1000) // 8


class PCMU(G711):
    """ PCMU codec handling """
    def __init__(self, params, queue):
        super().__init__(params, queue)
        self.name = 'mulaw'

    def get_silence(self):
        return self.make_packet(b'\xFF' * self.get_payload_len())


class PCMA(G711):
    """ PCMA codec handling """
    def __init__(self, params, queue):
        super().__init__(params, queue)
        self.name = 'alaw'

    def get_silence(self):
        return self.make_packet(b'\xD5' * self.get_payload_len())

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
