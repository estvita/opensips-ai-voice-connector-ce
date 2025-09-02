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


OPENAI_API_MODEL = "gpt-4o-realtime-preview-2024-10-01"
OPENAI_URL_FORMAT = "wss://api.openai.com/v1/realtime?model={}"


class OpenAI(AIEngine):  # pylint: disable=too-many-instance-attributes

    """ Implements WS communication with OpenAI """

    def __init__(self, call, cfg, logger=None):
        self.codec = self.choose_codec(call.sdp)
        self.queue = call.rtp
        self.call = call
        self.logger = logger or logging.getLogger()
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
        self.logger.info(f"OpenAI: WebSocket connection established: {self.ws}")
        
        try:
            first_message = await self.ws.recv()
            self.logger.info(f"OpenAI: First message received: {first_message}")
            json.loads(first_message)
        except ConnectionClosedOK:
            self.logger.info("WS Connection with OpenAI is closed")
            return
        except ConnectionClosedError as e:
            self.logger.error(e)
            return


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
            "tools": [],
            "tool_choice": "auto",
        }

        if self.transfer_to:
            self.session["tools"].append({
                "type": "function",
                "name": "transfer_call",
                "description": "call the function if a request was received to transfer a call with an operator, a person, or a department",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            })
        if self.tools:
            self.session["tools"] = self.tools
            self.logger.info("OpenAI: Using configured tools in session")
        else:
            self.logger.info("OpenAI: No tools configured for session")
        
        # Process API functions from bot config
        api_functions = []
        if hasattr(self, 'cfg') and isinstance(self.cfg, dict) and 'functions' in self.cfg and self.cfg['functions']:
            for func in self.cfg['functions']:
                if isinstance(func, dict) and 'function' in func:
                    # Extract function definition and add to session
                    api_functions.append(func['function'])
                    # Store URL and token for later use
                    if not hasattr(self, 'api_functions'):
                        self.api_functions = {}
                    self.api_functions[func['function']['name']] = {
                        'url': func.get('url'),
                        'token': func.get('token'),
                        'api_template': func.get('input_schema', {})
                    }
        
        # Add API functions to tools
        if api_functions:
            self.session["tools"].extend(api_functions)
            self.logger.info(f"OpenAI: Added API functions: {[f['name'] for f in api_functions]}")
        
        # Process MCP servers from bot config
        if hasattr(self, 'cfg') and isinstance(self.cfg, dict) and 'mcp_servers' in self.cfg and self.cfg['mcp_servers']:
            for mcp_server in self.cfg['mcp_servers']:
                if isinstance(mcp_server, dict) and 'url' in mcp_server:
                    mcp_tool = {
                        "type": "mcp",
                        "server_label": mcp_server.get('label', 'mcp_server'),
                        "server_url": mcp_server['url'],
                        "require_approval": mcp_server.get('require_approval', 'never')
                    }
                    if mcp_server.get('api_key'):
                        mcp_tool['api_key'] = mcp_server['api_key']
                    self.session["tools"].append(mcp_tool)
                    self.logger.info(f"OpenAI: Added MCP server: {mcp_server.get('label', 'mcp_server')} at {mcp_server['url']}")
        
        if self.instructions:
            self.session["instructions"] = self.instructions

        try:
            self.logger.info(f"OpenAI: Sending session update with tools: {json.dumps(self.session.get('tools', []), indent=2)}")
            await self.ws.send(json.dumps({"type": "session.update", "session": self.session}))
            if self.intro:
                self.intro = {
                    "instructions": "Please greet the user with the following: " +
                    self.intro
                }
                await self.ws.send(json.dumps({"type": "response.create", "response": self.intro}))
            await self.handle_command()
        except ConnectionClosedError as e:
            self.logger.error(f"Error while communicating with OpenAI: {e}. Terminating call.")
            self.terminate_call()
        except Exception as e:
            self.logger.error(f"Unexpected error during session: {e}. Terminating call.")
            self.terminate_call()


    async def handle_command(self):  # pylint: disable=too-many-branches
        """ Handles a command from the server """
        leftovers = b''
        async for smsg in self.ws:
            msg = json.loads(smsg)
            self.logger.info(f"Received message: {msg}")
            t = msg["type"]
            if t == "response.audio.delta":
                media = base64.b64decode(msg["delta"])
                packets, leftovers = await self.run_in_thread(
                    self.codec.parse, media, leftovers)
                for packet in packets:
                    self.queue.put_nowait(packet)
            elif t == "response.audio.done":
                self.logger.info(t)
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
                
                # Check for failed status
                if response.get("status") == "failed":                    
                    self.logger.error(f"OpenAI: Response failed: {response}")                    
                    # Terminate call on failure
                    self.terminate_call()
                    return
                
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
                            self.logger.info(t)
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
                        elif hasattr(self, 'api_functions') and function_name in self.api_functions:
                            function_response = await self.call_api_function(function_name, params_dict)

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

            elif t == "response.output_item.done":
                item = msg.get("item")
                if item and item.get("type") == "mcp_call":
                    output = item.get("output")
                    print(output)
                    if output:
                        payload = {
                            "type": "conversation.item.create",
                            "item": {
                                "type": "message",
                                "role": "assistant",
                                "content": [
                                    {"type": "text", "text": output}
                                ]
                            }
                        }
                        await self.ws.send(json.dumps(payload))
                        response_payload = {
                            "type": "response.create",
                            "response": {
                                "conversation": "auto",
                                "instructions": "Be sure to voice the latest results from the MCP server"
                            }
                        }
                        await self.ws.send(json.dumps(response_payload))

            elif t == "conversation.item.input_audio_transcription.completed":
                self.logger.info("Speaker: %s", msg["transcript"].rstrip())
            elif t == "response.audio_transcript.done":
                self.logger.info("Engine: %s", msg["transcript"])       
            elif t == "mcp_list_tools.in_progress":
                self.logger.info(f"OpenAI: MCP list tools in progress: {msg}")
            elif t == "conversation.item.input_audio_transcription.failed":
                self.logger.error(f"OpenAI: Audio transcription failed: {msg}")
                self.terminate_call()
            elif t == "error":
                self.logger.error(f"OpenAI: Error message received: {msg}")
                self.terminate_call()
            elif t == "response.failed":
                self.logger.error(f"OpenAI: Response failed: {msg}")
                self.terminate_call()
            else:
                self.logger.debug(f"OpenAI: Unhandled message type: {t}")

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
                self.logger.info("dropping %d packets", count)

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
            self.logger.error(f"WebSocket connection closed: {e.code}, {e.reason}")
            self.terminate_call()
        except Exception as e:
            self.logger.error(f"Unexpected error while sending audio: {e}")
            self.terminate_call()

    async def close(self):
        await self.ws.close()

    async def call_api_function(self, function_name, params):
        """Calls external API function"""
        try:
            func_config = self.api_functions[function_name]
            url = func_config['url']
            token = func_config.get('token')
            template = func_config.get('api_template', {})
            
            headers = {'Content-Type': 'application/json'}
            if token:
                headers['Authorization'] = f'Bearer {token}'
            
            # Prepare variables for template
            variables = {
                'function_name': function_name,
                'parameters': params,
                'user': self.call.user,
                'bot_id': getattr(self.call, 'bot_id', 'unknown'),
                'call_id': self.call.b2b_key
            }
            
            # Add function_name to parameters for template substitution
            if isinstance(params, dict):
                params['function_name'] = function_name
            
            # Apply template with variable substitution
            self.logger.info(f"Template: {template}")
            self.logger.info(f"Variables: {variables}")
            payload = self.apply_template(template, variables)
            self.logger.info(f"Final payload: {payload}")
            
            response = requests.post(url, json=payload, headers=headers)
            print(response.json())
            response.raise_for_status()
            
            result = response.json()
            self.logger.info(f"API function {function_name} called successfully: {result}")
            return str(result)
            
        except Exception as e:
            self.logger.error(f"Error calling API function {function_name}: {e}")
            return f"Error: {str(e)}"

    def apply_template(self, template, variables):
        """Apply template with variable substitution"""
        import json
        import re
        
        # Convert template to string for replacement
        template_str = json.dumps(template)
        
        # Create combined variables dict
        all_vars = variables.copy()
        if 'parameters' in variables and isinstance(variables['parameters'], dict):
            all_vars.update(variables['parameters'])
        
        # Replace any variables in format {variable_name}
        for var_name, var_value in all_vars.items():
            placeholder = f"{{{var_name}}}"
            if isinstance(var_value, dict):
                var_value = json.dumps(var_value)
            template_str = template_str.replace(placeholder, str(var_value))
        
        return json.loads(template_str)

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
