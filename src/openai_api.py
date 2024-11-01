#!/usr/bin/env python
#
# Copyright (C) 2024 SIP Point Consulting SRL
#
# This file is part of the OpenSIPS AI Voice Connector project
# (see https://github.com/OpenSIPS/opensips-ai-voice-connector-ce).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

"""
OpenAI WS communication
"""

import json
import base64
import logging
from websockets.asyncio.client import connect
from ai import AIEngine
from config import Config
from codec import get_match_codec


cfg = Config.get("openai")
OPENAI_API_MODEL = cfg.get("model", "OPENAI_API_MODEL",
                           "gpt-4o-realtime-preview-2024-10-01")
URL = f"wss://api.openai.com/v1/realtime?model={OPENAI_API_MODEL}"
OPENAI_API_KEY = cfg.get(["key", "openai_key"], "OPENAI_API_KEY")
OPENAI_HEADERS = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1"
}


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
