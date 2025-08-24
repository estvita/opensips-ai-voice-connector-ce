# MCP Server Integration Guide

## Overview

MCP (Model Context Protocol) integration allows the voice bot to access external tools and services through a standardized protocol.

## Configuration

Add to `config.ini`:
```ini
[openai]
mcp_url = http://your-mcp-server.com/path/to/mcp
```

## How It Works

1. **Initialization**: Bot connects to MCP server on startup
2. **Tool Discovery**: Bot retrieves available tools from MCP server
3. **Format Conversion**: MCP tools are converted to OpenAI function format
4. **Session Integration**: Tools are added to OpenAI session
5. **Function Calling**: When user asks questions, bot can call MCP tools

## Tool Format

MCP tools are converted to OpenAI format:
```json
{
  "type": "function",
  "name": "tool_name",
  "description": "Tool description",
  "parameters": {
    "type": "object",
    "properties": {...},
    "required": [...]
  }
}
```

## Usage Examples

- User: "What's the weather like?"
- Bot calls: `mcp_server` with `{"user_request": "What's the weather like?"}`
- MCP server responds with weather information
- Bot speaks the response to user

## Supported Requests

- Weather information
- Current news
- General knowledge queries
- Any topic the MCP server can handle

## Logging

All MCP interactions are logged with `MCP:` prefix in `logs/app.log`
