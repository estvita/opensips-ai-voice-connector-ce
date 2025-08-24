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
OpenAI WS communication
"""

import json
import base64
import logging
import requests
import asyncio
from queue import Empty
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from ai import AIEngine
from codec import get_codecs, CODECS, UnsupportedCodec
from config import Config
from mcp_client import MCPClient


OPENAI_API_MODEL = "gpt-4o-realtime-preview-2024-10-01"
OPENAI_URL_FORMAT = "wss://api.openai.com/v1/realtime?model={}"


class OpenAI(AIEngine):  # pylint: disable=too-many-instance-attributes

    """ Implements WS communication with OpenAI """

    def __init__(self, call, cfg):
        self.codec = self.choose_codec(call.sdp)
        self.queue = call.rtp
        self.call = call
        self.ws = None
        self.session = None
        self.intro = None
        self.transfer_to = None
        self.transfer_by = None
        self.tools = None
        self.cfg = Config.get("openai", cfg)
        self.model = self.cfg.get("model", "OPENAI_API_MODEL",
                                  OPENAI_API_MODEL)
        self.url = self.cfg.get("url", "OPENAI_URL",
                                OPENAI_URL_FORMAT.format(self.model))
        self.key = self.cfg.get(["key", "openai_key"], "OPENAI_API_KEY")
        self.voice = self.cfg.get(["voice", "openai_voice"],
                                  "OPENAI_VOICE", "alloy")
        self.instructions = self.cfg.get("instructions", "OPENAI_INSTRUCTIONS")
        self.intro = self.cfg.get("welcome_message", "OPENAI_WELCOME_MSG")
        self.transfer_to = self.cfg.get("transfer_to", "OPENAI_TRANSFER_TO")
        self.transfer_by = self.cfg.get("transfer_by", "OPENAI_TRANSFER_BY", self.call.to)
        self.tools = self.cfg.get("tools", "OPENAI_TOOLS")

        # Initialize MCP client if server URL is provided
        self.mcp_client = None
        mcp_server_url = self.cfg.get("mcp_url")
        mcp_api_key = self.cfg.get("mcp_key")
        if mcp_server_url:
            self.mcp_client = MCPClient(mcp_server_url, mcp_api_key)

        # normalize codec
        if self.codec.name == "mulaw":
            self.codec_name = "g711_ulaw"
        elif self.codec.name == "alaw":
            self.codec_name = "g711_alaw"

    def choose_codec(self, sdp):
        """ Returns the preferred codec from a list """
        codecs = get_codecs(sdp)
        priority = ["pcma", "pcmu"]
        cmap = {c.name.lower(): c for c in codecs}
        for codec in priority:
            if codec in cmap:
                return CODECS[codec](cmap[codec])

        raise UnsupportedCodec("No supported codec found")

    def get_audio_format(self):
        """ Returns the corresponding audio format """
        return self.codec_name

    async def start(self):
        """ Starts OpenAI connection and logs messages """
        openai_headers = {
                "Authorization": f"Bearer {self.key}",
                "OpenAI-Beta": "realtime=v1"
        }
        self.ws = await connect(self.url, additional_headers=openai_headers)
        try:
            json.loads(await self.ws.recv())
        except ConnectionClosedOK:
            logging.info("WS Connection with OpenAI is closed")
            return
        except ConnectionClosedError as e:
            logging.error(e)
            return

        # Get MCP tools before creating session
        openai_tools = []
        if self.mcp_client:
            try:
                await self.mcp_client.initialize()
                mcp_tools = await self.mcp_client.get_tools()
                if mcp_tools:
                    logging.info(f"OpenAI: Found {len(mcp_tools)} MCP tools")
                    # Convert MCP tools to OpenAI format
                    for tool in mcp_tools:
                        openai_tool = {
                            "type": "function",
                            "name": tool["name"],
                            "description": tool["description"],
                            "parameters": tool["inputSchema"]
                        }
                        openai_tools.append(openai_tool)
                    logging.info(f"OpenAI: Converted MCP tools: {[t['name'] for t in openai_tools]}")
                else:
                    logging.info("OpenAI: No MCP tools available")
            except Exception as e:
                logging.error(f"OpenAI: Error initializing MCP client: {e}")
        else:
            logging.info("OpenAI: No MCP client configured")

        self.session = {
            "turn_detection": {
                "type": self.cfg.get("turn_detection_type",
                                     "OPENAI_TURN_DETECT_TYPE",
                                     "server_vad"),
                "silence_duration_ms": int(self.cfg.get(
                    "turn_detection_silence_ms",
                    "OPENAI_TURN_DETECT_SILENCE_MS",
                    200)),
                "threshold": float(self.cfg.get(
                    "turn_detection_threshold",
                    "OPENAI_TURN_DETECT_THRESHOLD",
                    0.5)),
                "prefix_padding_ms": int(self.cfg.get(
                    "turn_detection_prefix_ms",
                    "OPENAI_TURN_DETECT_PREFIX_MS",
                    200)),
            },
            "input_audio_format": self.get_audio_format(),
            "output_audio_format": self.get_audio_format(),
            "input_audio_transcription": {
                "model": "whisper-1",
            },
            "voice": self.voice,
            "temperature": float(self.cfg.get("temperature",
                                              "OPENAI_TEMPERATURE", 0.8)),
            "max_response_output_tokens": self.cfg.get("max_tokens",
                                                       "OPENAI_MAX_TOKENS",
                                                       "inf"),
            "tool_choice": "auto",
        }
        
        # Set tools based on what's available
        if openai_tools:
            self.session["tools"] = openai_tools
            logging.info(f"OpenAI: Using MCP tools in session: {[t['name'] for t in openai_tools]}")
        elif self.tools:
            self.session["tools"] = self.tools
            logging.info("OpenAI: Using configured tools in session")
        else:
            logging.info("OpenAI: No tools configured for session")
        
        if self.instructions:
            self.session["instructions"] = self.instructions

        try:
            logging.info(f"OpenAI: Sending session update with tools: {json.dumps(self.session.get('tools', []), indent=2)}")
            await self.ws.send(json.dumps({"type": "session.update", "session": self.session}))
            if self.intro:
                self.intro = {
                    "instructions": "Please greet the user with the following: " +
                    self.intro
                }
                await self.ws.send(json.dumps({"type": "response.create", "response": self.intro}))
            await self.handle_command()
        except ConnectionClosedError as e:
            logging.error(f"Error while communicating with OpenAI: {e}. Terminating call.")
            self.terminate_call()
        except Exception as e:
            logging.error(f"Unexpected error during session: {e}. Terminating call.")
            self.terminate_call()


    async def handle_command(self):  # pylint: disable=too-many-branches
        """ Handles a command from the server """
        leftovers = b''
        async for smsg in self.ws:
            msg = json.loads(smsg)
            t = msg["type"]
            if t == "response.audio.delta":
                media = base64.b64decode(msg["delta"])
                packets, leftovers = await self.run_in_thread(
                    self.codec.parse, media, leftovers)
                for packet in packets:
                    self.queue.put_nowait(packet)
            elif t == "response.audio.done":
                logging.info(t)
                if len(leftovers) > 0:
                    packet = await self.run_in_thread(
                            self.codec.parse, None, leftovers)
                    self.queue.put_nowait(packet)
                    leftovers = b''

            elif t == "conversation.item.created":
                if msg["item"].get('status') == "completed":
                    self.drain_queue()

            # function-calling response 
            # https://platform.openai.com/docs/guides/realtime-conversations#function-calling
            elif t == "response.done":
                response = msg["response"]
                for item in response["output"]:
                    if item.get('type') == 'function_call':
                        function_name = item.get("name")
                        arguments = item.get("arguments", "{}")
                        try:
                            params_dict = json.loads(arguments)
                        except Exception:
                            params_dict = {}
                        function_response = None
                        if function_name == "terminate_call":
                            logging.info(t)
                            self.terminate_call()
                        elif function_name == "transfer_call":
                            params = {
                                'key': self.call.b2b_key,
                                'method': "REFER",
                                'body': "",
                                'extra_headers': (
                                    f"Refer-To: <{self.transfer_to}>\r\n"
                                    f"Referred-By: {self.transfer_by}\r\n"
                                )
                            }
                            self.call.mi_conn.execute('ua_session_update', params)
                        else:
                            # Use MCP server for function calling
                            logging.info(f"OpenAI: Function calling detected - function: {function_name}, params: {params_dict}")
                            
                            if self.mcp_client:
                                logging.info(f"OpenAI: MCP client is available, calling tool")
                                try:
                                    function_response = await self.mcp_client.call_tool(function_name, params_dict)
                                    logging.info(f"OpenAI: MCP tool call completed, response: {function_response}")
                                    
                                    if isinstance(function_response, dict):
                                        if "error" in function_response:
                                            function_response = f"Error: {function_response['error']}"
                                            logging.error(f"OpenAI: MCP tool returned error: {function_response}")
                                        else:
                                            function_response = str(function_response.get("result", function_response))
                                            logging.info(f"OpenAI: MCP tool returned result: {function_response}")
                                    else:
                                        function_response = str(function_response)
                                        logging.info(f"OpenAI: MCP tool returned non-dict response: {function_response}")
                                except Exception as e:
                                    logging.error(f"OpenAI: Exception calling MCP tool {function_name}: {e}")
                                    function_response = f"Error calling function: {str(e)}"
                            else:
                                logging.warning(f"OpenAI: No MCP client available for function: {function_name}")
                                function_response = f"Function {function_name} not available"

                        if function_response:
                            payload = {
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "function_call_output",
                                    "call_id": item.get("call_id"),
                                    "output": f"Say this to the user: {function_response}"
                                }
                            }
                            await self.ws.send(json.dumps(payload))
                            await self.ws.send(json.dumps({"type": "response.create"}))

            elif t == "conversation.item.input_audio_transcription.completed":
                logging.info("Speaker: %s", msg["transcript"].rstrip())
            elif t == "response.audio_transcript.done":
                logging.info("Engine: %s", msg["transcript"])            

            elif t == "conversation.item.input_audio_transcription.failed":
                logging.error(msg)
                self.terminate_call()
            elif t == "error":
                logging.info(msg)
            else:
                logging.debug(t)

    def terminate_call(self):
        """ Terminates the call """
        self.call.terminated = True

    async def run_in_thread(self, func, *args):
        """ Runs a function in a thread """
        return await asyncio.to_thread(func, *args)

    def drain_queue(self):
        """ Drains the playback queue """
        count = 0
        try:
            while self.queue.get_nowait():
                count += 1
        except Empty:
            if count > 0:
                logging.info("dropping %d packets", count)

    async def send(self, audio):
        """ Sends audio to OpenAI """
        if not self.ws or self.call.terminated:
            return

        audio_data = base64.b64encode(audio)
        event = {
            "type": "input_audio_buffer.append",
            "audio": audio_data.decode("utf-8")
        }

        try:
            await self.ws.send(json.dumps(event))
        except ConnectionClosedError as e:
            logging.error(f"WebSocket connection closed: {e.code}, {e.reason}")
            self.terminate_call()
        except Exception as e:
            logging.error(f"Unexpected error while sending audio: {e}")
            self.terminate_call()

    async def close(self):
        if self.mcp_client:
            await self.mcp_client.close()
        await self.ws.close()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
