# AI Voice Connector - Community Edition - OpenAI Flavor

The OpenAI flavor integrates directly with [OpenAI's Realtime
API](https://platform.openai.com/docs/guides/realtime), enabling direct
Speech-to-Speech processing for user conversations. This setup allows for
real-time interpretation and response generation, streamlining interactions
without intermediate steps.

## Implementation

The project uses the native WebSocket connection to push the decapsulated RTP
from the user to the OpenAI engine and get the response back. Then, it grabs
the response, packs it back by adding the RTP header and streams it back to
the user.

It does not have any transcoding capabilities, thus communication is limited
to g711 PCMU and PCMA
[codecs](https://platform.openai.com/docs/guides/realtime/audio-formats).

It currently uses the `gpt-4o-realtime-preview-2024-10-01` model.

## Configuration

The following parameters can be tuned for this engine:

| Section  | Parameter    | Environment | Mandatory | Description | Default |
|----------|--------------|-------------|-----------|-------------|---------|
| `openai` | `key` or `openai_key` | `OPENAI_API_KEY`   | **yes** | [OpenAI API](https://platform.openai.com/) key | not provided |
| `openai` | `model`               | `OPENAI_API_MODEL` | no | [OpenAI Realtime Model](https://platform.openai.com/docs/models/gpt-4o-realtime) used | `gpt-4o-realtime-preview-2024-10-01` |
| `openai` | `disable` | `OPENAI_DISABLE`   | no | Disables the flavor | false |
| `openai` | `voice`   | `OPENAI_VOICE`     | no | Configures the [OpenAI voice](https://platform.openai.com/docs/guides/text-to-speech#voice-options) | `alloy` |
| `openai` | `instructions`    | `OPENAI_INSTRUCTIONS` | no | Configures the OpenAI module instructions | default/none |
| `openai` | `welcome_message` | `OPENAI_WELCOME_MSG`  | no | A welcome message to be played back to the user when the call starts | no message |
| `openai` | `temperature`     | `OPENAI_TEMPERATURE`  | no | Sampling temperature for the model, limited to `[0.6, 1.2]` | 0.8 |
| `openai` | `max_tokens`      | `OPENAI_MAX_TOKENS`   | no | Configures [OpenAI Turn Detection](https://platform.openai.com/docs/api-reference/realtime-client-events/session/update) `max_response_output_tokens`, the maximum number of output tokens for a single assistant response. Possible values are `[1, 4096]` or `inf`  | `inf` |
| `openai` | `turn_detection_type`      | `OPENAI_TURN_DETECT_TYPE`      | no | Configures [OpenAI Turn Detection](https://platform.openai.com/docs/api-reference/realtime-client-events/session/update) `type` | `server_vad` |
| `openai` | `turn_detection_silence_ms`| `OPENAI_TURN_DETECT_SILENCE_MS`| no | Configures [OpenAI Turn Detection](https://platform.openai.com/docs/api-reference/realtime-client-events/session/update) `silence duration ms` | `200` |
| `openai` | `turn_detection_threshold` | `OPENAI_TURN_DETECT_THRESHOLD` | no | Configures [OpenAI Turn Detection](https://platform.openai.com/docs/api-reference/realtime-client-events/session/update) `threshold` | `0.5` |
| `openai` | `turn_detection_prefix_ms` | `OPENAI_TURN_DETECT_PREFIX_MS` | no | Configures [OpenAI Turn Detection](https://platform.openai.com/docs/api-reference/realtime-client-events/session/update) `prefix_padding_ms` | `300` |
| `openai`  |  `transfer_to`  | `OPENAI_TRANSFER_TO` | no | [SIP uri](https://en.wikipedia.org/wiki/SIP_URI_scheme) for call transfer function | not set |
| `openai`  |  `transfer_by`  | `OPENAI_TRANSFER_BY` | no | [SIP uri](https://en.wikipedia.org/wiki/SIP_URI_scheme) for call transfer function | not set |


## Function Calling

The OpenAI flavor supports [Function Calling](https://platform.openai.com/docs/guides/realtime-conversations#function-calling) capabilities, allowing the AI to execute specific actions during conversations. This enables dynamic call management and integration with external systems.

### Built-in Functions

The following functions are automatically available:

- **`terminate_call`**: Immediately ends the current call session
- **`transfer_call`**: Transfers the call to another SIP endpoint using the configured `transfer_to` and `transfer_by` parameters

### Custom API Functions

You can define custom API functions by configuring the `functions` parameter in your configuration. These functions allow the AI to interact with external APIs and services.

Example configuration:
```ini
[openai]
functions = [
    {
        "name": "get_weather",
        "description": "Get current weather information",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or coordinates"
                }
            },
            "required": ["location"]
        }
    }
]
```

## MCP Server Integration

The OpenAI flavor supports integration with [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers, enabling the AI to access external tools and data sources during conversations.

### Configuration

MCP servers can be configured using the following parameters:

- **`mcp_server_url`**: The URL endpoint of your MCP server
- **`mcp_api_key`**: Optional authentication key for the MCP server

### Advanced MCP Configuration

For more complex MCP setups, you can configure multiple MCP servers with detailed options:

```ini
[openai]
mcp_servers = [
    {
        "url": "https://your-mcp-server.com/mcp",
        "api_key": "your-api-key",
        "label": "main_server",
        "require_approval": "always"
    },
    {
        "url": "https://another-mcp-server.com/mcp",
        "label": "secondary_server",
        "require_approval": "never"
    }
]
```

### MCP Server Capabilities

MCP servers can provide various capabilities including:
- **Data Retrieval**: Access to databases, APIs, and external services
- **Tool Execution**: Running scripts, commands, or workflows
- **Context Management**: Maintaining conversation state and history
- **Custom Integrations**: Connecting to proprietary systems and services

The AI will automatically use available MCP tools when they can help fulfill user requests, making conversations more dynamic and informative.

## Examples and Use Cases

For practical examples and detailed use cases of Function Calling and MCP server integration, see [OpenAI Examples](openai-examples.md).
