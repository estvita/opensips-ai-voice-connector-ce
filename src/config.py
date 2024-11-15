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
Parses the configuration file
"""

import os
import configparser


_Config = configparser.ConfigParser()


class ConfigSection(dict):
    """ class that handles a config section """

    def __init__(self, section, custom=None):
        super().__init__(section)
        self.update(custom)

    def getenv(self, env, fallback=None):
        """ returns the configuration from environment """
        if not env:
            return fallback
        if isinstance(env, list):
            # check to see whether we have any of the keys
            for e in env:
                if e in os.environ:
                    return os.getenv(e)
            # no key found - check if env is a list
            return fallback
        return os.getenv(env, fallback)

    def get(self, option, env=None, fallback=None):
        """ returns the configuration for the required option """
        if isinstance(option, list):
            # check to see whether we have any of the keys
            for o in option:
                if o in self.keys():
                    return super().get(o)
            # no key found - check if env is a list
            return self.getenv(env, fallback)
        return super().get(option, self.getenv(env, fallback))

    def getboolean(self, option, env=None, fallback=None):
        """ returns a boolean value from the configuration """
        val = self.get(option, env, None)
        if not val:
            return fallback
        if val.isnumeric():
            return int(val) != 0
        if val.lower() in ["yes", "true", "on"]:
            return True
        if val.lower() in ["no", "false", "off"]:
            return False
        return fallback


class Config():
    """ class that handles the config """

    @staticmethod
    def init(config_file):
        """ Initializes the config with a configuration file """
        config_file = config_file or os.getenv('CONFIG_FILE')
        if config_file:
            _Config.read(config_file)

    @staticmethod
    def get(section, init_data=None):
        """ Retrieves a specific section from the config file """
        if section not in _Config:
            _Config.add_section(section)
        if not init_data:
            init_data = {}
        return ConfigSection(_Config[section], init_data)

    @staticmethod
    def engine(option, env=None, fallback=None):
        """ Special handling for the engine section """
        section = Config.get("engine")
        return section.get(option, env, fallback)

    @staticmethod
    def sections():
        """ Retrieves the sections from the config file """
        return _Config.sections()


# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
