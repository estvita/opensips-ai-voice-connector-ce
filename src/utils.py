#!/usr/bin/env python

"""
Module that provides helper functions for AI
"""

import re
from deepgram_api import Deepgram
from openai_api import OpenAI
FLAVORS = {"deepgram": Deepgram,
           "openai": OpenAI}


def get_ai_flavor(params):
    """ Returns the AI flavor to be used """
    flavor = list(FLAVORS.keys())[0]
    if 'headers' not in params:
        return flavor

    # Try to get the To header
    to_lines = [line for line in params['headers'].splitlines()
                if line.startswith("To:")]
    if len(to_lines) == 0:
        return flavor
    to = to_lines[0].split(":", 1)[1]
    uri_re = re.compile(
        r'(?P<scheme>\w+):'
        + r'(?:(?P<user>[\w\.+*]+):?(?P<password>[\w\.]+)?@)?'
        + r'\[?(?P<host>'
        + r'(?:\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})|'
        + r'(?:(?:[0-9a-fA-F]{1,4}):){7}[0-9a-fA-F]{1,4}|'
        + r'(?:(?:[0-9A-Za-z]+\.)+[0-9A-Za-z]+)'
        + r')\]?:?'
        + r'(?P<port>\d{1,6})?'
        + r'(?:\;(?P<params>[^\?]*))?'
        + r'(?:\?(?P<headers>.*))?'
        )
    to_re = uri_re.search(to)
    if to_re:
        to = to_re.group("user")
    keys = list(FLAVORS.keys())
    if to in keys:
        flavor = to
    else:
        try:
            flavor_index = int(to[-1])
            flavor = keys[flavor_index % len(keys)]
        except ValueError:
            pass
    return flavor


def get_ai(flavor, key, codec, queue):
    """ Returns an AI object """
    return FLAVORS[flavor](key, codec, queue)

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
