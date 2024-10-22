#!/usr/bin/env python

"""
OpenAI WS communication
"""

import os
import json
import base64
import logging
from websockets.asyncio.client import connect
from ai import AIEngine
from codec import get_match_codec


OPENAI_API_MODEL = os.getenv("OPENAI_API_MODEL",
                             "gpt-4o-realtime-preview-2024-10-01")
URL = f"wss://api.openai.com/v1/realtime?model={OPENAI_API_MODEL}"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_HEADERS = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1"
}


class UnsupportedCodec(Exception):
    """ Exception for Unsupported Codecs errors """


class OpenAI(AIEngine):

    """ Implements WS communication with OpenAI """

    def __init__(self, key, sdp, queue):
        self.queue = queue
        self.ws = None
        self.session = None

        self.codec = get_match_codec(sdp, ["pcmu", "pcma"])

        # normalize codec
        if self.codec.name == "mulaw":
            self.codec_name = "g711_ulaw"
        elif self.codec.name == "alaw":
            self.codec_name = "g711_alaw"

    async def start(self):
        """ Starts OpenAI connection and logs messages """
        self.ws = await connect(URL, additional_headers=OPENAI_HEADERS)
        msg = json.loads(await self.ws.recv())
        self.session = {
                "turn_detection": {
                    "type": "server_vad",
                    "silence_duration_ms": 200,
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                },
                "input_audio_format": self.codec_name,
                "output_audio_format": self.codec_name,
        }
        await self.ws.send(json.dumps({"type": "session.update",
                                      "session": self.session}))
        async for smsg in self.ws:
            msg = json.loads(smsg)
            t = msg["type"]
            if t == "response.audio.delta":
                media = base64.b64decode(msg["delta"])
                for packet in self.codec.parse(media):
                    self.queue.put_nowait(packet)
            elif t == "response.audio_transcript.done":
                logging.info(msg["transcript"])
            elif t == "error":
                logging.info(msg)
            else:
                logging.info(t)

    async def send(self, audio):
        """ Sends audio to OpenAI """
        if not self.ws:
            return
        audio_data = base64.b64encode(audio)
        event = {
                "type": "input_audio_buffer.append",
                "audio": audio_data.decode("utf-8")
        }
        await self.ws.send(json.dumps(event))

    async def close(self):
        await self.ws.close()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
