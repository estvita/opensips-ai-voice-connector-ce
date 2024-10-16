import random
from rtp import GenerateRTPpacket
from deepgram import LiveOptions, SpeakOptions

class GenericCodec:
    def __init__(self, params, queue):
        self.marker = 1
        self.params = params
        self.queue = queue

        self.sequence_number = random.randint(0, 10000)
        self.timestamp = random.randint(0, 10000)
        self.ssrc = random.randint(0, 2**31)
        self.payload_type = params.payloadType

    def process_response(self, response):
        pass

    def parse_params(self):
        pass

    def make_live_options(self):
        return LiveOptions(
            model="nova-2",
            language="en-US",
            punctuate=True,
            filler_words=True,
            interim_results=True,
            utterance_end_ms="1000"
        )

    def make_speak_options(self):
        return SpeakOptions(
            model="aura-asteria-en"
        )

    def get_silence(self):
        pass

    def make_packet(self, payload):
        packet =  GenerateRTPpacket({
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
                        except:
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
                    except:
                        pass
                    pages.append(data[:pos])

                data = data[pos:]

        for page in pages:
            self.parse_page(page)
    
    def parse_page(self, page):
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
            segment = page[27 + page_segments + sum(segments_lens[:i]):27 + page_segments + sum(segments_lens[:i]) + segment_len]
            if i == 0 and segment.startswith(b'OpusHead'):
                return
            if i == 0 and segment.startswith(b'OpusTags'):
                return
            
            rtp_packet = self.make_packet(segment)
            self.queue.put_nowait(rtp_packet)

            self.sequence_number += 1
            self.timestamp += self.ts_increment

    def make_live_options(self):
        options = super().make_live_options()
        options.encoding = self.name
        options.sample_rate = self.sample_rate
        return options

    def make_speak_options(self):
        options = super().make_speak_options()
        options.encoding = self.name
        options.container = self.container
        options.bit_rate = self.bitrate
        return options
    
    def get_silence(self):
        return self.make_packet(b'\xf8\xff\xfe')


class G711(GenericCodec):
    def __init__(self, params, queue):
        super().__init__(params, queue)

        self.sample_rate = 8000
        self.bitrate = 64000
        self.container = 'none'

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

    def make_live_options(self):
        options = super().make_live_options()
        options.encoding = self.name
        options.sample_rate = self.sample_rate
        return options
    
    def make_speak_options(self):
        options = super().make_speak_options()
        options.encoding = self.name
        options.container = self.container
        options.sample_rate = self.sample_rate
        return options


class PCMU(G711):
    def __init__(self, params, queue):
        super().__init__(params, queue)
        self.name = 'mulaw'
    
    def get_silence(self):
        payload_len = ((self.sample_rate * 20 * 8) // 1000) // 8
        return self.make_packet(b'\xFF' * payload_len)

    
class PCMA(G711):
    def __init__(self, params, queue):
        super().__init__(params, queue)
        self.name = 'alaw'
    
    def get_silence(self):
        payload_len = ((self.sample_rate * 20 * 8) // 1000) // 8
        return self.make_packet(b'\xD5' * payload_len)
