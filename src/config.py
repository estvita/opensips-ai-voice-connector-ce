#!/usr/bin/env python

"""
Parses the configuration file
"""

import os
import configparser


_Config = configparser.ConfigParser()


class ConfigSection(dict):
    """ class that handles a config section """

    def getenv(self, env, fallback=None):
        """ returns the configuration from environment """
        if isinstance(env, list):
            # check to see whether we have any of the keys
            for e in env:
                if e in os.environ:
                    return os.getenv(e)
            # no key found - check if env is a list
            return fallback
        return os.getenv(env, fallback)

    def get(self, option, env, fallback=None):
        """ returns the configuration for the required option """
        if isinstance(option, list):
            # check to see whether we have any of the keys
            for o in option:
                if o in self.keys():
                    return super().get(o)
            # no key found - check if env is a list
            return self.getenv(env, fallback)
        return super().get(option, self.getenv(env, fallback))


class Config():
    """ class that handles the config """

    @staticmethod
    def init(config_file):
        """ Initializes the config with a configuration file """
        config_file = config_file or os.getenv('CONFIG_FILE')
        if config_file:
            _Config.read(config_file)

    @staticmethod
    def get(section):
        """ Retrieves a specific section from the config file """
        return ConfigSection(_Config[section] if section in _Config else {})

    @staticmethod
    def engine(option, env, fallback=None):
        """ Special handling for the engine section """
        section = Config.get("engine")
        return section.get(option, env, fallback)


# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
