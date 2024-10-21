""" Main module that starts the Deepgram AI integration """

import os
import json
import signal
import socket
import asyncio
import logging

from opensipscli import args, cli
from call import Call, CodecException


MI_IP = os.getenv("MI_IP", default='127.0.0.1')
MI_PORT = int(os.getenv("MI_PORT", default='8080'))

myargs = args.OpenSIPSCLIArgs(log_level='WARNING',
                              communication_type='datagram',
                              datagram_ip=MI_IP,
                              datagram_port=MI_PORT)

mycli = cli.OpenSIPSCLI(myargs)
calls = {}

logging.basicConfig(
    level=logging.INFO,  # Set level to INFO or DEBUG for more verbosity
    format='%(asctime)s - %(levelname)s - %(message)s',
)


def udp_handler(sock):
    """ UDP handler of events received """
    message = sock.recv(4096)
    data = json.loads(message)

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
            new_call = Call(key, sdp_str, mycli)
        except CodecException:
            mycli.mi('ua_session_reply', {'key': key,
                                          'method': method,
                                          'code': 488,
                                          'reason': 'Not Acceptable Here'})
            return
        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.exception("Error creating call %s", e)
            mycli.mi('ua_session_reply', {'key': key,
                                          'method': method,
                                          'code': 500,
                                          'reason':
                                          'Server Internal Error'})
            return

        calls[key] = new_call

    if method == 'BYE':
        asyncio.create_task(calls[key].close())
        calls.pop(key, None)


async def shutdown(s, loop, event_socket):
    """ Called when the program is shutting down """
    logging.info("Received exit signal %s...", s)
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    logging.info("Cancelling %d outstanding tasks", len(tasks))
    for call in calls.values():
        await call.close()
    event_socket.close()
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()
    logging.info("Shutdown complete.")


async def reregister(sock):
    """ Re-Registers a socket to OpenSIPS """
    while True:
        mycli.mi('event_subscribe', ['E_UA_SESSION', sock])
        await asyncio.sleep(3600 - 30)


async def main():
    """ Main function """
    host_ip = os.getenv("EVENT_IP", "127.0.0.1")
    port = int(os.getenv("EVENT_PORT", "0"))

    event_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    event_socket.bind((host_ip, port))
    _, port = event_socket.getsockname()

    logging.info("Starting server at %s:%hu", host_ip, port)
    sock = f'udp:{host_ip}:{port}'

    loop = asyncio.get_running_loop()
    stop = loop.create_future()

    loop.add_signal_handler(
        signal.SIGTERM,
        lambda: asyncio.create_task(shutdown(signal.SIGTERM,
                                             loop,
                                             event_socket)),
    )

    loop.add_signal_handler(
        signal.SIGINT,
        lambda: asyncio.create_task(shutdown(signal.SIGINT,
                                             loop,
                                             event_socket)),
    )
    loop.create_task(reregister(sock))

    loop.add_reader(event_socket.fileno(), udp_handler, event_socket)

    try:
        await stop
    except asyncio.CancelledError:
        pass

if __name__ == '__main__':
    asyncio.run(main())

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
