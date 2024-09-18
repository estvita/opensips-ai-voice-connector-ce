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

load_dotenv()

API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

myargs = args.OpenSIPSCLIArgs(config='./cfg/opensips-cli.cfg')
mycli = cli.OpenSIPSCLI(myargs)
calls = {}

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
            print(f"Error creating call: {e}")
            return

        calls[key] = new_call
    
    if method == 'BYE':
        asyncio.create_task(calls[key].close())
        calls.pop(key, None)

async def shutdown(signal, loop, event_socket):
    print(f"Received exit signal {signal.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    print(f"Cancelling {len(tasks)} outstanding tasks")
    for call in calls.values():
        await call.close()
    event_socket.close()
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()
    print("Shutdown complete.")

async def main():
    print(mycli.mi('event_subscribe', ['E_UA_SESSION', 'udp:127.0.0.1:50060']))
    
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
