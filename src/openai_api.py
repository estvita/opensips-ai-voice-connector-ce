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
import asyncio
from queue import Empty
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from ai import AIEngine
from codec import get_codecs, CODECS, UnsupportedCodec
from config import Config

cfg = Config.get("openai")
OPENAI_API_MODEL = cfg.get("model", "OPENAI_API_MODEL",
                           "gpt-4o-realtime-preview-2024-10-01")
URL = f"wss://api.openai.com/v1/realtime?model={OPENAI_API_MODEL}"
URL = cfg.get("url", "OPENAI_URL", URL)
OPENAI_API_KEY = cfg.get(["key", "openai_key"], "OPENAI_API_KEY")
OPENAI_HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "OpenAI-Beta": "realtime=v1"
}
OPENAI_VOICE = cfg.get(["voice", "openai_voice"], "OPENAI_VOICE", "alloy")
OPENAI_INSTR = cfg.get("instructions", "OPENAI_INSTRUCTIONS")
OPENAI_INTRO = cfg.get("welcome_message", "OPENAI_WELCOME_MSG")


class OpenAI(AIEngine):  # pylint: disable=too-many-instance-attributes

    """ Implements WS communication with OpenAI """

    def __init__(self, call):
        self.codec = self.choose_codec(call.sdp)
        self.queue = call.rtp
        self.call = call
        self.ws = None
        self.session = None
        self.intro = None

        # normalize codec
        if self.codec.name == "mulaw":
            self.codec_name = "g711_ulaw"
        elif self.codec.name == "alaw":
            self.codec_name = "g711_alaw"

    def choose_codec(self, sdp):
        """ Returns the preferred codec from a list """
        codecs = get_codecs(sdp)
        priority = ["pcma", "pcmu"]
        cmap = {c.name.lower(): c for c in codecs}
        for codec in priority:
            if codec in cmap:
                return CODECS[codec](cmap[codec])

        raise UnsupportedCodec("No supported codec found")

    def get_audio_format(self):
        """ Returns the corresponding audio format """
        return self.codec_name

    async def start(self):
        """ Starts OpenAI connection and logs messages """
        self.ws = await connect(URL, additional_headers=OPENAI_HEADERS)
        try:
            json.loads(await self.ws.recv())
        except ConnectionClosedOK:
            logging.info("WS Connection with OpenAI is closed")
            return
        except ConnectionClosedError as e:
            logging.error(e)
            return

        self.session = {
            "turn_detection": {
                "type": "server_vad",
                "silence_duration_ms": 200,
                "threshold": 0.5,
                "prefix_padding_ms": 300,
            },
            "input_audio_format": self.get_audio_format(),
            "output_audio_format": self.get_audio_format(),
            "input_audio_transcription": {
                "model": "whisper-1",
            },
            "voice": OPENAI_VOICE,
            "tools": [
                {
                    "type": "function",
                    "name": "terminate_call",
                    "description":
                        "Call me when any of the session's parties want to terminate the call."
                        "Always say goodbye before hanging up."
                        "Send the audio first, then call this function.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    },
                },
            ],
            "tool_choice": "auto",
        }
        if OPENAI_INSTR:
            self.session["instructions"] = OPENAI_INSTR
        await self.ws.send(json.dumps({"type": "session.update",
                                      "session": self.session}))

        if OPENAI_INTRO:
            self.intro = {
                "instructions": "Please greet the user with the following: " + OPENAI_INTRO}
            await self.ws.send(json.dumps({"type": "response.create",
                                           "response": self.intro}))
        await self.handle_command()

    async def handle_command(self):  # pylint: disable=too-many-branches
        """ Handles a command from the server """
        leftovers = b''
        async for smsg in self.ws:
            msg = json.loads(smsg)
            t = msg["type"]
            if t == "response.audio.delta":
                media = base64.b64decode(msg["delta"])
                packets, leftovers = await self.run_in_thread(
                    self.codec.parse, media, leftovers)
                for packet in packets:
                    self.queue.put_nowait(packet)
            elif t == "response.audio.done":
                logging.info(t)
                if len(leftovers) > 0:
                    packet = await self.run_in_thread(self.codec.parse, None, leftovers)
                    self.queue.put_nowait(packet)
                    leftovers = b''

            elif t == "conversation.item.created":
                if msg["item"]["status"] == "completed":
                    self.drain_queue()
            elif t == "conversation.item.input_audio_transcription.completed":
                logging.info("Speaker: %s", msg["transcript"].rstrip())
            elif t == "response.audio_transcript.done":
                logging.info("Engine: %s", msg["transcript"])
            elif t == "response.function_call_arguments.done":
                if msg["name"] == "terminate_call":
                    logging.info(t)
                    self.terminate_call()
            elif t == "error":
                logging.info(msg)
            else:
                logging.info(t)

    def terminate_call(self):
        """ Terminates the call """
        self.call.terminated = True

    async def run_in_thread(self, func, *args):
        """ Runs a function in a thread """
        return await asyncio.to_thread(func, *args)

    def drain_queue(self):
        """ Drains the playback queue """
        count = 0
        try:
            while self.queue.get_nowait():
                count += 1
        except Empty:
            if count > 0:
                logging.info("dropping %d packets", count)

    async def send(self, audio):
        """ Sends audio to OpenAI """
        if not self.ws or self.call.terminated:
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
