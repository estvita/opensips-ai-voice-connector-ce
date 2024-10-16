import os
import socket
import asyncio
from aiortc.sdp import SessionDescription
from deepgram.utils import verboselogs
from opensipscli import cli

from rtp import DecodeRTPpacket
from codec import Opus, PCMA, PCMU

from queue import Queue
from chatgpt import ChatGPT
import logging

from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents
)

class CodecException(Exception):
    """ Raised when there is a codec mismatch """

class Call():
    def __init__(self, b2b_key, sdp_str, deepgram: DeepgramClient, cli: cli.OpenSIPSCLI, chatgpt: ChatGPT):
        host_ip = os.getenv('RTP_IP', socket.gethostbyname(socket.gethostname()))

        self.b2b_key = b2b_key
        self.cli = cli

        self.chatgpt = chatgpt
        self.deepgram = deepgram

        # remove rtcp line, since the parser throws an error on it
        sdp_str = "\n".join([ l for l in sdp_str.split("\n") if not l.startswith("a=rtcp:")])

        sdp = SessionDescription.parse(sdp_str)
        #sdp.media[0].direction = 'recvonly'

        if sdp.media[0].host:
            self.client_addr = sdp.media[0].host
        else:
            self.client_addr = sdp.host
        self.client_port = sdp.media[0].port

        self.rtp = Queue()
        self.stop_event = asyncio.Event()
        self.stop_event.clear()

        logging.info(sdp)

        for codec in sdp.media[0].rtp.codecs:
            if codec.name.lower() in [ "pcmu", "pcma", "opus" ]:
                break
        else:
            raise CodecException("No supported codec found")
        
        self.codec = None
        
        codec_name = codec.name.lower()
        if codec_name == "pcmu":
            self.codec = PCMU(params=codec, queue=self.rtp)
        elif codec_name == "pcma":
            self.codec = PCMA(params=codec, queue=self.rtp)
        elif codec_name == "opus":
            self.codec = Opus(params=codec, queue=self.rtp)

        self.transcription_options = self.codec.make_live_options()

        # Remove all other codecs

        self.speak_options = self.codec.make_speak_options()

        self.serversock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.serversock.bind((host_ip, 0))

        sdp.origin = f"{sdp.origin.rsplit(' ', 1)[0]} {host_ip}"
        sdp.media[0].port = self.serversock.getsockname()[1]
        if sdp.host:
            sdp.host = host_ip
        if sdp.media[0].host:
            sdp.media[0].host = host_ip

        # update SDP to return only chosen codec, as we do not accept anything else
        sdp.media[0].rtp.codecs = [self.codec.params]
        sdp.media[0].fmt = [self.codec.payload_type]

        self.data = asyncio.Queue()

        self.dg_connection = deepgram.listen.asyncwebsocket.v("1")

        call_ref = self
        chatgpt.create_call(b2b_key)


        self.buf = []
        sentences = self.buf

        async def on_message(self, result, **kwargs):
            sentence = result.channel.alternatives[0].transcript
            if len(sentence) == 0:
                return
            if not result.is_final:
                return
            sentences.append(sentence)
            if not sentence.endswith(("?", ".", "!")):
                return
            try:
                phrase = " ".join([s for s in sentences])
                logging.info(f"Speaker: {phrase}")
                assistant_response = await chatgpt.send_message(b2b_key, phrase)
            except Exception as e:
                logging.info(e)
                return
            sentences.clear()
            await call_ref.speak(assistant_response)

        self.dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
        asyncio.create_task(self.start_connection())

        logging.info(cli.mi('ua_session_reply', {'key': b2b_key, 'method': 'INVITE', 'code': 200, 'reason': 'OK', 'body': str(sdp)}))

    async def speak(self, phrase):
        response = await self.deepgram.speak.asyncrest.v("1").stream_raw({"text": phrase}, self.speak_options)
        asyncio.create_task(self.codec.process_response(response))
    
    async def start_connection(self):
        logging.info(f"Starting connection for call {self.b2b_key}")

        if await self.dg_connection.start(self.transcription_options) is False:
            logging.info("Failed to start connection")
            return

        loop = asyncio.get_running_loop()
        loop.add_reader(self.serversock.fileno(), self.read_rtp)
        asyncio.create_task(self.send_rtp())

        return self.serversock
    
    def read_rtp(self):
        data = self.serversock.recv(1024)
        packet = DecodeRTPpacket(data.hex())
        self.data.put_nowait(bytes.fromhex(packet['payload']))
        asyncio.create_task(self.send_audio())

    async def send_rtp(self):
        while not self.stop_event.is_set():
            try:
                rtp_packet = self.rtp.get_nowait()
            except Exception:
                rtp_packet = self.codec.get_silence()
            self.serversock.sendto(bytes.fromhex(rtp_packet), (self.client_addr, self.client_port))
            await asyncio.sleep(float(20 * 0.001))

    async def send_audio(self):
        audio = await self.data.get()
        await self.dg_connection.send(audio)

    async def close(self):
        logging.info(f"Call {self.b2b_key} closing")
        self.chatgpt.delete_call(self.b2b_key)
        self.stop_event.set()
        loop = asyncio.get_running_loop()
        loop.remove_reader(self.serversock.fileno())
        self.serversock.close()
        await self.dg_connection.finish()
