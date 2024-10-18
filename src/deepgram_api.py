#!/usr/bin/env python

"""
Module that implements Deepgram communcation
"""

import asyncio

from deepgram import (  # pylint: disable=import-error
    LiveOptions,
    SpeakOptions,
    DeepgramClient,
    LiveTranscriptionEvents
)


class DeepgramSession:
    """ handles a Deepgram session """

    def __init__(self, client, key, codec, handler):
        self.client = client
        self.key = key
        self.codec = codec
        self.ws = self.client.listen.asyncwebsocket.v("1")
        self.ws.on(LiveTranscriptionEvents.Transcript, handler)
        self.transcription_options = LiveOptions(
                model="nova-2",
                language="en-US",
                punctuate=True,
                filler_words=True,
                interim_results=True,
                utterance_end_ms="1000",
                encoding=self.codec.name,
                sample_rate=self.codec.sample_rate)
        self.speak_options = SpeakOptions(
            model="aura-asteria-en",
            encoding=self.codec.name,
            container=self.codec.container,
            bit_rate=self.codec.bitrate,
            sample_rate=self.codec.sample_rate)

    async def speak(self, phrase):
        """ Speaks the phrase received as parameter """
        ar = self.client.speak.asyncrest.v("1")
        response = await ar.stream_raw({"text": phrase}, self.speak_options)
        asyncio.create_task(self.codec.process_response(response))

    async def start(self):
        """ Starts a transcribe session """
        return self.ws.start(self.transcription_options)

    async def send(self, audio):
        """ Sends an audio packet """
        return self.ws.send(audio)

    async def finish(self):
        """ Terminates a session """
        return self.ws.finish()


class Deepgram:
    """ Implements Deeepgram communication """

    def __init__(self, key):
        self.client = DeepgramClient(key)

    def new_call(self, key, codec, handler):
        """ adds a transcribe handler """
        return DeepgramSession(self.client, key, codec, handler)

    def close(self):
        """ closes the Deepgram session """

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
