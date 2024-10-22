#!/usr/bin/env python

"""
Abstract class that provides the AI hooks
"""
from abc import ABC, abstractmethod


class AIEngine(ABC):
    """ Class that implements the AI logic """

    @abstractmethod
    def __init__(self, key, codec, queue):
        pass

    @abstractmethod
    async def start(self):
        """ starts a new call/session """

    @abstractmethod
    async def send(self, audio):
        """ Sends audio to AI """

    @abstractmethod
    async def close(self):
        """ closes the session """


# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
