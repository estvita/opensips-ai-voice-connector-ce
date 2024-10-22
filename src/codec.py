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

    @abstractmethod
    def parse(self, data):
        """ Parses codec packets """


class Opus(GenericCodec):
    """ Opus codec handling """
    def __init__(self, params):
        super().__init__(params)

        self.name = 'opus'
        self.sample_rate = 48000
        self.bitrate = 96000
        self.container = 'ogg'

    async def process_response(self, response, queue):
        async for data in response.aiter_bytes():
            for packet in self.parse(data):
                queue.put_nowait(packet)

    def parse(self, data):
        return OggOpus(data).packets()

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
        async for data in response.aiter_bytes():
            for payload in self.parse(data):
                queue.put_nowait(payload)

    def parse(self, data):
        chunk_size = self.get_payload_len()
        packets = []
        while len(data) > 0:
            payload = data[:chunk_size]
            data = data[chunk_size:]

            if len(payload) == 0:
                break
            if len(payload) < chunk_size:
                # fill with silence
                remain = chunk_size - len(payload)
                payload = payload + self.get_silence_byte() * remain
            packets.append(payload)
        return packets

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
