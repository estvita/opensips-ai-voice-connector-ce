#!/usr/bin/env python

"""
Module that implements Deepgram communcation
"""

import os
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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_MODEL = os.getenv("OPENAI_API_MODEL", "gpt-4o")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
DEEPGRAM_WELCOME = os.getenv('DEEPGRAM_WELCOME_MSG', None)

chatgpt = ChatGPT(OPENAI_API_KEY, OPENAI_API_MODEL)


class Deepgram(AIEngine):  # pylint: disable=too-many-instance-attributes

    """ Implements Deeepgram communication """

    def __init__(self, key, sdp, queue):
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
        chatgpt.create_call(self.b2b_key, DEEPGRAM_WELCOME)

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
                model="nova-2",
                language="en-US",
                punctuate=True,
                filler_words=True,
                interim_results=True,
                utterance_end_ms="1000",
                encoding=self.codec.name,
                sample_rate=self.codec.sample_rate)
        # don't use sample_rate if we have a bitrate
        if self.codec.bitrate:
            self.speak_options = SpeakOptions(
                model="aura-asteria-en",
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
        response = await chatgpt.handle(self.b2b_key, phrase)
        asyncio.create_task(self.process_speech(response))

    async def close(self):
        """ closes the Deepgram session """
        chatgpt.delete_call(self.b2b_key)
        await self.stt.finish()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
