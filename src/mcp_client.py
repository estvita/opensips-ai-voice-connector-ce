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
MCP (Model Context Protocol) Client
"""

import json
import logging
import aiohttp
from typing import Dict, List, Any


class MCPClient:
    """MCP Client for interacting with MCP servers"""
    
    def __init__(self, server_url: str, api_key: str = None):
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.session = None
        self.available_tools = []
        self.initialized = False
        
    async def initialize(self):
        """Initialize connection to MCP server and get available tools"""
        if self.initialized:
            return
      
        try:
            self.session = aiohttp.ClientSession()
            
            # Initialize MCP connection
            init_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {
                        "name": "opensips-ai-voice-connector",
                        "version": "1.0.0"
                    }
                }
            }
            
            headers = {'Content-Type': 'application/json'}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'            
           
            async with self.session.post(self.server_url, json=init_payload, headers=headers) as response:
                logging.debug(f"MCP: Init response status: {response.status}")
                
                if response.status == 200:
                    init_result = await response.json()
                    logging.info(f"MCP: Init response: {json.dumps(init_result, indent=2)}")
                else:
                    error_text = await response.text()
                    logging.error(f"MCP: Failed to initialize client: {response.status} - {error_text}")
                    return
            
            # Now get the tools list
            tools = await self._get_tools()
            if tools:
                self.available_tools = tools
                logging.info(f"MCP: Client initialized with {len(self.available_tools)} available tools")
                self.initialized = True
            else:
                logging.warning("MCP: No tools found from MCP server, but client initialized")
                self.initialized = True
                    
        except Exception as e:
            logging.error(f"MCP: Exception during initialization: {e}")
            
    async def _get_tools(self) -> List[Dict[str, Any]]:
        """Get available tools from MCP server using JSON-RPC format"""
        try:
            headers = {'Content-Type': 'application/json'}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            # Get the tools list
            tools_payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list"
            }
                        
            async with self.session.post(self.server_url, json=tools_payload, headers=headers) as response:
                logging.debug(f"MCP: Tools response status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    logging.debug(f"MCP: Raw tools response: {json.dumps(data, indent=2)}")
                    
                    # Handle JSON-RPC response format
                    if isinstance(data, dict) and 'result' in data:
                        result = data['result']
                        if 'tools' in result:
                            tools = result['tools']
                            logging.debug(f"MCP: Found {len(tools)} tools")
                            return tools
                        else:
                            logging.debug(f"MCP: No tools in result. Available keys: {list(result.keys())}")
                    else:
                        logging.info(f"MCP: Unexpected response format: {type(data)}")
                    
                    logging.info(f"MCP: Found tools from MCP server")
                else:
                    error_text = await response.text()
                    logging.error(f"MCP: Tools error response: {error_text}")
        except Exception as e:
            logging.error(f"MCP: Exception during MCP server connection: {e}")
                
        return []
    
    async def get_tools(self) -> List[Dict[str, Any]]:
        """Get available tools from MCP server"""
        if not self.initialized:
            await self.initialize()
        return self.available_tools
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool on the MCP server"""
        if not self.initialized:
            await self.initialize()
            
        logging.info(f"MCP: Starting tool call for '{tool_name}' with parameters: {parameters}")
        
        try:
            headers = {'Content-Type': 'application/json'}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            call_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": parameters
                }
            }
            
            logging.info(f"MCP: Request payload: {json.dumps(call_payload, indent=2)}")
            
            async with self.session.post(self.server_url, json=call_payload, headers=headers) as response:
                logging.info(f"MCP: Response status: {response.status}")
                logging.info(f"MCP: Response headers: {dict(response.headers)}")
                
                if response.status == 200:
                    result = await response.json()
                    logging.info(f"MCP: Response body: {json.dumps(result, indent=2)}")
                    
                    # Extract text content from JSON-RPC response
                    if isinstance(result, dict) and 'result' in result:
                        result_data = result['result']
                        if 'content' in result_data:
                            content = result_data['content']
                            if isinstance(content, list) and len(content) > 0:
                                text_content = content[0].get('text', '')
                                logging.info(f"MCP: Extracted text content: {text_content}")
                                return {"result": text_content}
                            else:
                                logging.info(f"MCP: Content is not a list: {content}")
                                return {"result": str(content)}
                        else:
                            logging.info(f"MCP: No content in result: {result_data}")
                            return {"result": str(result_data)}
                    else:
                        logging.info(f"MCP: Unexpected response format: {result}")
                        return {"result": str(result)}
                else:
                    error_text = await response.text()
                    logging.error(f"MCP: Tool call failed with status {response.status}: {error_text}")
                    return {"error": f"HTTP {response.status}: {error_text}"}
                    
        except Exception as e:
            logging.error(f"MCP: Exception during tool call '{tool_name}': {e}")
            return {"error": str(e)}
    
    async def close(self):
        """Close the MCP client session"""
        if self.session:
            await self.session.close()
            self.session = None
            self.initialized = False
