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

import sys
import signal
import asyncio
import logging
import argparse

from opensips.mi import OpenSIPSMI, OpenSIPSMIException
from opensips.event import OpenSIPSEventHandler, OpenSIPSEventException

from call import Call
from config import Config
from codec import UnsupportedCodec
from utils import get_ai_flavor, UnknownSIPUser
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
                    default=None,
                    help='specify a configuration file')


parsed_args = parser.parse_args()
Config.init(parsed_args.config)

mi_cfg = Config.get("opensips")
mi_ip = mi_cfg.get("ip", "MI_IP", "127.0.0.1")
mi_port = int(mi_cfg.get("port", "MI_PORT", "8080"))

mi_conn = OpenSIPSMI(conn="datagram", datagram_ip=mi_ip, datagram_port=mi_port)

calls = {}

logging.basicConfig(
    level=logging.INFO,  # Set level to INFO or DEBUG for more verbosity
    format='%(asctime)s - %(levelname)s - %(message)s',
)


def udp_handler(data):
    """ UDP handler of events received """

    if 'params' not in data:
        return
    params = data['params']

    if 'key' not in params:
        return
    key = params['key']

    if 'method' not in params:
        return
    method = params['method']

    if method == 'INVITE':
        if 'body' not in params:
            return

        sdp_str = params['body']

        try:
            new_call = Call(key, sdp_str, mi_conn, get_ai_flavor(params))
            calls[key] = new_call
        except UnsupportedCodec:
            mi_conn.execute('ua_session_reply', {'key': key,
                                                 'method': method,
                                                 'code': 488,
                                                 'reason':
                                                 'Not Acceptable Here'})
        except UnknownSIPUser:
            logging.exception("Unknown SIP user %s")
            mi_conn.execute('ua_session_reply', {'key': key,
                                                 'method': method,
                                                 'code': 404,
                                                 'reason': 'Not Found'})
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.exception("Error creating call %s", e)
            mi_conn.execute('ua_session_reply', {'key': key,
                                                 'method': method,
                                                 'code': 500,
                                                 'reason':
                                                 'Server Internal Error'})

    if method == 'BYE':
        asyncio.create_task(calls[key].close())
        calls.pop(key, None)


async def shutdown(s, loop, event):
    """ Called when the program is shutting down """
    logging.info("Received exit signal %s...", s)
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    logging.info("Cancelling %d outstanding tasks", len(tasks))
    for call in calls.values():
        await call.close()
    try:
        event.unsubscribe()
    except OpenSIPSEventException as e:
        logging.error("Error unsubscribing from event: %s", e)
    except OpenSIPSMIException as e:
        logging.error("Error unsubscribing from event: %s", e)
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()
    logging.info("Shutdown complete.")


async def main():
    """ Main function """
    host_ip = Config.engine("event_ip", "EVENT_IP", "127.0.0.1")
    port = int(Config.engine("event_port", "EVENT_PORT", "0"))

    handler = OpenSIPSEventHandler(mi_conn, "datagram", ip=host_ip, port=port)
    try:
        event = handler.async_subscribe("E_UA_SESSION", udp_handler)
    except OpenSIPSEventException as e:
        logging.error("Error subscribing to event: %s", e)
        return

    _, port = event.socket.sock.getsockname()

    logging.info("Starting server at %s:%hu", host_ip, port)

    loop = asyncio.get_running_loop()
    stop = loop.create_future()

    loop.add_signal_handler(
        signal.SIGTERM,
        lambda: asyncio.create_task(shutdown(signal.SIGTERM,
                                             loop,
                                             event)),
    )

    loop.add_signal_handler(
        signal.SIGINT,
        lambda: asyncio.create_task(shutdown(signal.SIGINT,
                                             loop,
                                             event)),
    )

    try:
        await stop
    except asyncio.CancelledError:
        pass

if __name__ == '__main__':
    asyncio.run(main())

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
