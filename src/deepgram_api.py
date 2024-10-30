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
Module that implements Deepgram communcation
"""

import logging
import asyncio

from deepgram import (  # pylint: disable=import-error
    LiveOptions,
    SpeakOptions,
    DeepgramClient,
    LiveTranscriptionEvents,
)

from ai import AIEngine
from chatgpt_api import ChatGPT
from codec import get_match_codec
from config import Config

cfg = Config.get("deepgram")
CHATGPT_API_KEY = cfg.get(["chatgpt_key", "openai_key"],
                          ["CHATGPT_API_KEY", "OPENAI_API_KEY"])
CHATGPT_API_MODEL = cfg.get("chatgpt_model", "CHATGPT_API_MODEL", "gpt-4o")
DEEPGRAM_API_KEY = cfg.get("key", "DEEPGRAM_API_KEY")
DEEPGRAM_LANGUAGE = cfg.get("language", "DEEPGRAM_LANGUAGE", "en-US")
DEEPGRAM_VOICE = cfg.get("voice", "DEEPGRAM_VOICE", "aura-asteria-en")
DEEPGRAM_SPEECH_MODEL = cfg.get("speech_model", "DEEPGRAM_SPEECH_MODEL",
                                "nova-2-conversationalai")
DEEPGRAM_WELCOME = cfg.get("welcome_message", "DEEPGRAM_WELCOME_MSG")


class Deepgram(AIEngine):  # pylint: disable=too-many-instance-attributes

    """ Implements Deeepgram communication """

    chatgpt = None

    def __init__(self, key, sdp, queue):

        if not Deepgram.chatgpt:
            Deepgram.chatgpt = ChatGPT(CHATGPT_API_KEY, CHATGPT_API_MODEL)
        self.deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        self.b2b_key = key
        self.codec = get_match_codec(sdp, ["pcmu", "pcma", "opus"])
        self.queue = queue
        self.stt = self.deepgram.listen.asyncwebsocket.v("1")
        self.tts = self.deepgram.speak.asyncrest.v("1")
        # used to serialize the speech events
        self.speech_lock = asyncio.Lock()

        self.buf = []
        sentences = self.buf
        call_ref = self
        Deepgram.chatgpt.create_call(self.b2b_key, DEEPGRAM_WELCOME)

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

        self.stt.on(LiveTranscriptionEvents.Transcript, on_text)
        self.transcription_options = LiveOptions(
                model=DEEPGRAM_SPEECH_MODEL,
                language=DEEPGRAM_LANGUAGE,
                punctuate=True,
                filler_words=True,
                interim_results=True,
                utterance_end_ms="1000",
                encoding=self.codec.name,
                sample_rate=self.codec.sample_rate)
        # don't use sample_rate if we have a bitrate
        if self.codec.bitrate:
            self.speak_options = SpeakOptions(
                model=DEEPGRAM_VOICE,
                encoding=self.codec.name,
                bit_rate=self.codec.bitrate,
                container=self.codec.container)
        else:
            self.speak_options = SpeakOptions(
                model="aura-asteria-en",
                encoding=self.codec.name,
                sample_rate=self.codec.sample_rate,
                container=self.codec.container)

    async def send(self, audio):
        """ Sends audio to Deepgram """
        await self.stt.send(audio)

    async def process_speech(self, phrase):
        """ Processes the speech received """
        response = await self.tts.stream_raw({"text": phrase},
                                             self.speak_options)
        async with self.speech_lock:
            await self.codec.process_response(response, self.queue)

    async def start(self):
        """ Starts a Depgram connection """
        if await self.stt.start(self.transcription_options) is False:
            return

        if DEEPGRAM_WELCOME:
            asyncio.create_task(self.process_speech(DEEPGRAM_WELCOME))

    async def handle_phrase(self, phrase):
        """ handles the response of a phrase """
        response = await Deepgram.chatgpt.handle(self.b2b_key, phrase)
        asyncio.create_task(self.process_speech(response))

    async def close(self):
        """ closes the Deepgram session """
        Deepgram.chatgpt.delete_call(self.b2b_key)
        await self.stt.finish()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
