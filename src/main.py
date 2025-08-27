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

""" Main module that starts the Deepgram AI integration """

import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler
import argparse
from config import Config
from version import __version__


parser = argparse.ArgumentParser(description='OpenSIPS AI Voice Connector',
                                 prog=sys.argv[0],
                                 usage='%(prog)s [OPTIONS]',
                                 epilog='\n')
# Argument used to print the current version
parser.add_argument('-v', '--version',
                    action='version',
                    default=None,
                    version=f'OpenSIPS CLI {__version__}')
parser.add_argument('-c', '--config',
                    metavar='[CONFIG]',
                    type=str,
                    default='config.ini',
                    help='specify a configuration file')

parser.add_argument("-l", "--loglevel",
                    choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    default='ERROR',
                    help="Log level")

parsed_args = parser.parse_args()
Config.init(parsed_args.config)

os.makedirs('logs', exist_ok=True)
log_handler = TimedRotatingFileHandler(
    'logs/app.log', when='midnight', interval=1, backupCount=7, encoding='utf-8'
)
log_handler.setFormatter(logging.Formatter('%(asctime)s - tid: %(thread)d - %(levelname)s - %(message)s'))

# Configure root logger for general application logs only
logger = logging.getLogger()
logger.setLevel(getattr(logging, parsed_args.loglevel))
logger.addHandler(log_handler)

# Prevent call-specific loggers from propagating to root logger
logging.getLogger('call_').setLevel(logging.CRITICAL)
logging.getLogger('call_').propagate = False

if __name__ == '__main__':
    from engine import run
    run()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
