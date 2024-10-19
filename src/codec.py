""" Module that implements a generic codec """

from abc import ABC, abstractmethod
from opus import OggOpus


class GenericCodec(ABC):
    """ Generic Abstract class for a codec """
    def __init__(self, params, ptime=20):
        self.params = params
        self.ptime = ptime
        self.payload_type = params.payloadType
        self.sample_rate = params.clockRate
        self.ts_increment = int(self.sample_rate // (1000 / ptime))

    @abstractmethod
    async def process_response(self, response, queue):
        """ Processes the response from speach engine """

    @abstractmethod
    def get_silence(self):
        """ Returns a silence packet """


class Opus(GenericCodec):
    """ Opus codec handling """
    def __init__(self, params):
        super().__init__(params)

        self.name = 'opus'
        self.sample_rate = None
        self.bitrate = 96000
        self.container = 'ogg'

    async def process_response(self, response, queue):
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
                            self.parse_page(page, queue)
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
                        self.parse_page(page, queue)
                    finally:
                        pass
                    pages.append(data[:pos])

                data = data[pos:]

        for page in pages:
            self.parse_page(page, queue)

    def parse_page(self, page, queue):
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

            queue.put_nowait(rtp_packet)

    def get_silence(self):
        return b'\xf8\xff\xfe'


class G711(GenericCodec):
    """ Generic G711 Codec handling """
    def __init__(self, params):
        super().__init__(params)

        self.sample_rate = 8000
        self.bitrate = None
        self.container = 'none'
        self.name = "g711"

    async def process_response(self, response, queue):
        chunk_size = self.get_payload_len()
        buffer = bytearray()
        async for data in response.aiter_bytes():
            buffer.extend(data)
            while len(buffer) > 0:
                payload = buffer[:chunk_size]
                buffer = buffer[chunk_size:]

                if len(payload) == 0:
                    break
                if len(payload) < chunk_size:
                    # fill with silence
                    remain = chunk_size - len(payload)
                    payload = payload + self.get_silence_byte() * remain
                queue.put_nowait(payload)

    def get_silence(self):
        return self.get_silence_byte() * self.get_payload_len()

    def get_silence_byte(self):
        """ Returns the silence byte for g711 codec """
        return b'\xFF'

    def get_payload_len(self):
        """ Returns payload length """
        return ((self.sample_rate * 8 * 20) // 1000) // 8


class PCMU(G711):
    """ PCMU codec handling """
    def __init__(self, params):
        super().__init__(params)
        self.name = 'mulaw'

    def get_silence_byte(self):
        return b'\xFF'


class PCMA(G711):
    """ PCMA codec handling """
    def __init__(self, params):
        super().__init__(params)
        self.name = 'alaw'

    def get_silence(self):
        return b'\xD5'

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
