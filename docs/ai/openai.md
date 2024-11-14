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
| `openai` | `instructions`   | `OPENAI_INSTRUCTIONS`     | no | Configures the OpenAI module instructions | default/none |
| `openai` | `welcome_message` | `OPENAI_WELCOME_MSG`   | no | A welcome message to be played back to the user when the call starts | no message |
