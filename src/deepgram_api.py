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
        self.tts = self.client.speak.asyncwebsocket.v("1")
        self.stt.on(LiveTranscriptionEvents.Transcript, thandler)
        self.tts.on(SpeakWebSocketEvents.AudioData, shandler)
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
            bit_rate=self.codec.bitrate,
            container=self.codec.container,
            sample_rate=self.codec.sample_rate)

    async def speak(self, phrase):
        """ Speaks the phrase received as parameter """
        ar = self.client.speak.asyncrest.v("1")
        response = await ar.stream_raw({"text": phrase}, self.speak_options)
        asyncio.create_task(self.codec.process_response(response))

    async def start(self):
        """ Returns start coroutines for both TTS and STT """
        #ret = await asyncio.gather(self.stt.start(self.transcription_options),
        #                           self.tts.start(self.speak_options))
        #return (ret[0] and ret[1])
        return await asyncio.gather(self.stt.start(self.transcription_options))

    async def send(self, audio):
        """ Sends an audio packet """
        await self.stt.send(audio)

    async def finish(self):
        """ Terminates a session """
        await asyncio.gather(self.stt.finish(), self.tts.finish())


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
