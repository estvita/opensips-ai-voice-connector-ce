#!/usr/bin/env python

"""
Module that provides helper functions for AI
"""

import re
from deepgram_api import Deepgram
from openai_api import OpenAI
from config import Config

FLAVORS = {"deepgram": Deepgram,
           "openai": OpenAI}


class UnknownSIPUser(Exception):
    """ User is not known """


def get_user(params):
    """ Returns the User from the SIP headers """

    if 'headers' not in params:
        return None

    # Try to get the To header
    to_lines = [line for line in params['headers'].splitlines()
                if line.startswith("To:")]
    if len(to_lines) == 0:
        return None
    to = to_lines[0].split(":", 1)[1].strip()
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
        return to_re.group("user").lower()
    return None


def _dialplan_match(regex, string):
    """ Checks if a regex matches the string """
    pattern = re.compile(regex)
    return pattern.match(string)


def get_ai_flavor_default(user):
    """ Returns the default algorithm for AI choosing """
    keys = list(FLAVORS.keys())
    if user in keys:
        if Config.get(user).getboolean("disabled", False):
            return user
    # remove disabled engines
    keys = [k for k in keys if
            not Config.get(k).getboolean("disabled", False)]
    hash_index = hash(user) % len(keys)
    return keys[hash_index]


def get_ai_flavor(params):
    """ Returns the AI flavor to be used """

    user = get_user(params)
    if not user:
        raise UnknownSIPUser("cannot parse username")

    # first, get the sections in order and check if they have a dialplan
    flavor = None
    for flavor in Config.sections():
        if flavor not in FLAVORS:
            continue
        if Config.get(flavor).getboolean("disabled", False):
            continue
        dialplans = Config.get(flavor).get("match")
        if not dialplans:
            continue
        if isinstance(dialplans, list):
            for dialplan in dialplans:
                if _dialplan_match(dialplan, user):
                    return flavor
        elif _dialplan_match(dialplans, user):
            return flavor
    return get_ai_flavor_default(user)


def get_ai(flavor, key, codec, queue):
    """ Returns an AI object """
    return FLAVORS[flavor](key, codec, queue)

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
