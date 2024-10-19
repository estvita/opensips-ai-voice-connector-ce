""" Handles the a SIP call """

import os
import random
import socket
import asyncio
import logging
import datetime
from queue import Queue, Empty
from aiortc.sdp import SessionDescription
from aiortc import RTCRtpCodecParameters
from opensipscli import cli

from rtp import decode_rtp_packet, generate_rtp_packet
from codec import Opus, PCMA, PCMU
from chatgpt_api import ChatGPT
from deepgram_api import Deepgram


class CodecException(Exception):
    """ Raised when there is a codec mismatch """


API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_MODEL = os.getenv("OPENAI_API_MODEL", "gpt-4o")

deepgram = Deepgram(API_KEY)
chatgpt = ChatGPT(OPENAI_API_KEY, OPENAI_API_MODEL)


class Call():  # pylint: disable=too-many-instance-attributes
    """ Class that handles a call """
    def __init__(self,  # pylint: disable=too-many-arguments
                 b2b_key, sdp_str,
                 c: cli.OpenSIPSCLI):
        try:
            hostname = socket.gethostbyname(socket.gethostname())
        except socket.gaierror:  # unknown hostname
            hostname = "127.0.0.1"
        host_ip = os.getenv('RTP_IP', hostname)
        self.welcome_msg = os.getenv('WELCOME_MSG', None)

        self.b2b_key = b2b_key
        self.cli = c

        # remove rtcp line, since the parser throws an error on it
        sdp_str = "\n".join([line for line in sdp_str.split("\n")
                             if not line.startswith("a=rtcp:")])

        sdp = SessionDescription.parse(sdp_str)

        if sdp.media[0].host:
            self.client_addr = sdp.media[0].host
        else:
            self.client_addr = sdp.host
        self.client_port = sdp.media[0].port

        self.rtp = Queue()
        self.stop_event = asyncio.Event()
        self.stop_event.clear()
        # used to serialize the speech events
        self.speech_lock = asyncio.Lock()

        self.codec = self.get_codec(sdp)

        self.serversock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.serversock.bind((host_ip, 0))

        sdp = self.get_new_sdp(sdp, host_ip)

        call_ref = self
        chatgpt.create_call(b2b_key, self.welcome_msg)

        self.buf = []
        sentences = self.buf

        async def on_speech(__, result, **_):
            async with self.speech_lock:
                await call_ref.codec.process_response(result, self.rtp)

        async def on_text(__, result, **_):
            sentence = result.channel.alternatives[0].transcript
            if len(sentence) == 0:
                return
            if not result.is_final:
                return
            sentences.append(sentence)
            if not sentence.endswith(("?", ".", "!")):
                return
            phrase = " ".join(sentences)
            logging.info("Speaker: %s", phrase)
            asyncio.create_task(call_ref.handle_phrase(phrase))
            sentences.clear()

        self.deepgram = deepgram.new_call(self.codec, on_speech, on_text)
        asyncio.create_task(self.start_api())

        if self.welcome_msg:
            asyncio.create_task(self.speak(self.welcome_msg))

        self.cli.mi('ua_session_reply', {'key': b2b_key,
                                         'method': 'INVITE',
                                         'code': 200,
                                         'reason': 'OK',
                                         'body': str(sdp)})

    async def handle_phrase(self, phrase):
        """ handles the response of a phrase """
        response = await chatgpt.handle(self.b2b_key, phrase)
        asyncio.create_task(self.deepgram.speak(response))

    async def speak(self, phrase):
        """ Speaks the phrase received as parameter """
        await self.deepgram.speak(phrase)

    async def start_api(self):
        """ Starts a Depgram connection """
        logging.info("Starting connection for call %s", self.b2b_key)

        if await self.deepgram.start() is False:
            logging.info("Failed to start connection")
            return

        loop = asyncio.get_running_loop()
        loop.add_reader(self.serversock.fileno(), self.read_rtp)
        asyncio.create_task(self.send_rtp())

    def get_codec(self, sdp):
        """ Returns the codec to be used """
        logging.debug(sdp)
        logging.debug(sdp.media[0].rtp.codecs)

        for codec in sdp.media[0].rtp.codecs:
            if codec.name.lower() in ["pcmu", "pcma", "opus"]:
                break
        else:
            # try to find based on fmt - default values
            for pt in sdp.media[0].fmt:
                if pt in [0, 8]:
                    mime = f"audio/PCM{'U' if pt == 0 else 'A'}"
                    codec = RTCRtpCodecParameters(mimeType=mime,
                                                  clockRate=8000,
                                                  payloadType=pt)
                    break
            else:
                raise CodecException("No supported codec found")

        codec_name = codec.name.lower()
        if codec_name == "pcmu":
            return PCMU(codec)
        if codec_name == "pcma":
            return PCMA(codec)
        if codec_name == "opus":
            return Opus(codec)

    def get_new_sdp(self, sdp, host_ip):
        """ Gets a new SDP to be sent back in 200 OK """
        sdp.origin = f"{sdp.origin.rsplit(' ', 1)[0]} {host_ip}"
        sdp.media[0].port = self.serversock.getsockname()[1]
        if sdp.host:
            sdp.host = host_ip
        if sdp.media[0].host:
            sdp.media[0].host = host_ip

        # update SDP to return only chosen codec
        # as we do not accept anything else
        # Remove all other codecs
        sdp.media[0].rtp.codecs = [self.codec.params]
        sdp.media[0].fmt = [self.codec.payload_type]

        return sdp

    def read_rtp(self):
        """ Reads a RTP packet """
        data = self.serversock.recv(1024)
        try:
            packet = decode_rtp_packet(data.hex())
            audio = bytes.fromhex(packet['payload'])
            asyncio.create_task(self.deepgram.send(audio))
        except ValueError:
            pass

    async def send_rtp(self):
        """ Sends all RTP packet """

        sequence_number = random.randint(0, 10000)
        timestamp = random.randint(0, 10000)
        ssrc = random.randint(0, 2**31)
        ts_inc = self.codec.ts_increment
        ptime = self.codec.ptime
        payload_type = self.codec.payload_type
        marker = 1

        while not self.stop_event.is_set():
            last_time = datetime.datetime.now()
            try:
                payload = self.rtp.get_nowait()
            except Empty:
                payload = self.codec.get_silence()
            rtp_packet = generate_rtp_packet({
                'version': 2,
                'padding': 0,
                'extension': 0,
                'csi_count': 0,
                'marker': marker,
                'payload_type': payload_type,
                'sequence_number': sequence_number,
                'timestamp': timestamp,
                'ssrc': ssrc,
                'payload': payload.hex()
            })
            marker = 0
            sequence_number += 1
            timestamp += ts_inc

            self.serversock.sendto(bytes.fromhex(rtp_packet),
                                   (self.client_addr, self.client_port))
            next_time = last_time + datetime.timedelta(milliseconds=ptime)
            now = datetime.datetime.now()
            drift = (next_time - now).total_seconds()
            if drift > 0:
                await asyncio.sleep(float(drift))

    async def close(self):
        """ Closes the call """
        logging.info("Call %s closing", self.b2b_key)
        chatgpt.delete_call(self.b2b_key)
        self.stop_event.set()
        loop = asyncio.get_running_loop()
        loop.remove_reader(self.serversock.fileno())
        self.serversock.close()
        await self.deepgram.finish()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
