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
| `openai`  |  `tools`  | `OPENAI_TOOLS` | no | A file or a list of files where tools available to the model are defined. You can override functions, as the model will search for a tool in the list of files and will use the last one that matches the function name. See [functions.py](../../functions.py) for examples. | not set |
