#!/usr/bin/env python

"""
Module that implements Deepgram communcation
"""

import asyncio

from deepgram import (  # pylint: disable=import-error
    LiveOptions,
    SpeakOptions,
    DeepgramClient,
    SpeakWebSocketEvents,
    LiveTranscriptionEvents,
)


class DeepgramSession:
    """ handles a Deepgram session """

    def __init__(self, client, codec, shandler, thandler):
        self.client = client
        self.codec = codec
        self.stt = self.client.listen.asyncwebsocket.v("1")
        self.tts = self.client.speak.asyncrest.v("1")
        self.stt.on(LiveTranscriptionEvents.Transcript, thandler)
        self.shandler = shandler
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

    async def speak(self, phrase):
        """ Speaks the phrase received as parameter """
        asyncio.create_task(self.process_speech(phrase))

    async def process_speech(self, phrase):
        """ Processes the speech received """
        response = await self.tts.stream_raw({"text": phrase},
                                             self.speak_options)
        asyncio.create_task(self.shandler(self, response))

    async def start(self):
        """ Returns start coroutines for both TTS and STT """
        return await self.stt.start(self.transcription_options)

    async def send(self, audio):
        """ Sends an audio packet """
        await self.stt.send(audio)

    async def finish(self):
        """ Terminates a session """
        await self.stt.finish()


class Deepgram:
    """ Implements Deeepgram communication """

    def __init__(self, key):
        self.client = DeepgramClient(key)

    def new_call(self, codec, shandler, thandler):
        """ adds a transcribe handler """
        return DeepgramSession(self.client, codec, shandler, thandler)

    def close(self):
        """ closes the Deepgram session """

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
