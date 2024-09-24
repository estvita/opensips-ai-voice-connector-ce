from opensipscli import args, cli
import asyncio
import signal
import json
import socket
import os
from dotenv import load_dotenv
from deepgram.utils import verboselogs

from deepgram import DeepgramClient

from call import Call

from chatgpt import ChatGPT

import logging

load_dotenv()

API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

MI_IP = os.getenv("MI_IP", default='127.0.0.1')
MI_PORT = os.getenv("MI_PORT", default=8080)

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

deepgram: DeepgramClient = DeepgramClient(API_KEY)
chatgpt = ChatGPT(OPENAI_API_KEY, "gpt-4o")

def udp_handler(sock):
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
            new_call = Call(key, sdp_str, deepgram, mycli, chatgpt)
        except Exception as e:
            logging.info(f"Error creating call: {e}")
            return

        calls[key] = new_call
    
    if method == 'BYE':
        asyncio.create_task(calls[key].close())
        calls.pop(key, None)

async def shutdown(signal, loop, event_socket):
    logging.info(f"Received exit signal {signal.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    logging.info(f"Cancelling {len(tasks)} outstanding tasks")
    for call in calls.values():
        await call.close()
    event_socket.close()
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()
    logging.info("Shutdown complete.")

async def main():
    logging.info(mycli.mi('event_subscribe', ['E_UA_SESSION', 'udp:127.0.0.1:50060']))
    
    event_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    event_socket.bind(('localhost', 50060))
    
    loop = asyncio.get_running_loop()
    stop = loop.create_future()

    loop.add_signal_handler(
        signal.SIGTERM,
        lambda: asyncio.create_task(shutdown(signal.SIGTERM, loop, event_socket)),
    )

    loop.add_signal_handler(
        signal.SIGINT,
        lambda: asyncio.create_task(shutdown(signal.SIGINT, loop, event_socket)),
    )
    
    event_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    event_socket.bind(('localhost', 50060))
    loop.add_reader(event_socket.fileno(), udp_handler, event_socket)

    try:
        await stop
    except asyncio.CancelledError:
        pass

if __name__ == '__main__':
    asyncio.run(main())
