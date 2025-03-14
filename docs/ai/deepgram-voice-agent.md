# AI Voice Connector - Community Edition - Deepgram's Voice Agent Flavor

The Deepgram's Voice Agent flavor uses the [Deepgram's](https://deepgram.com/) 
new Voice Agent API that provides direct Speech-to-Speech interpretation of 
the user's conversation. This setup allows for real-time interpretation and 
response generation, streamlining interactions without intermediate steps.

## Implementation

The project uses the native WebSocket connection to push the decapsulated RTP 
from the user to the Deepgram engine and get the response back. Then, it grabs 
the response, packs it back by adding the RTP header, and streams it back to 
the user.

It does not have any transcoding capabilities, thus communication is limited 
to g711 PCMU and PCMA 
[codecs](https://developers.deepgram.com/docs/configure-voice-agent).

## Configuration

The following parameters can be tuned for this engine:

| Section  | Parameter    | Environment | Mandatory | Description | Default |
|----------|--------------|-------------|-----------|-------------|---------|
| `deepgram_agent` | `key` | `DEEPGRAM_API_KEY`   | **yes** | [Deepgram API](https://deepgram.com/) key | not provided |
| `deepgram_agent` | `speech_model` | `DEEPGRAM_AGENT_SPEECH_MODEL` | no | [Deepgram's speech detection model](https://developers.deepgram.com/docs/models-languages-overview) | `nova-2-conversationalai` |
| `deepgram_agent` | `voice` | `DEEPGRAM_AGENT_VOICE`   | no | [Deepgram's voice](https://developers.deepgram.com/docs/tts-models) used for speaking back the response | `aura-asteria-en` |
| `deepgram_agent` | `welcome_message` | `DEEPGRAM_AGENT_WELCOME_MSG`   | no | A welcome message to be played back to the user when the call starts | `` |
| `deepgram_agent` | `instructions` | `DEEPGRAM_INSTRUCTIONS` | no | Configures the LLM instructions | `` |
| `deepgram_agent` | `llm_url` | `DEEPGRAM_LLM_URL` | no | Configures the LLM URL | `` |
| `deepgram_agent` | `llm_auth` | `DEEPGRAM_LLM_KEY` | no | Configures the LLM API key | `` |
| `deepgram_agent` | `llm_model` | `DEEPGRAM_LLM_MODEL` | no | Configures the LLM model | `` |
| `deepgram_agent` | `disable` | `DEEPGRAM_AGENT_DISABLE`   | no | Disables the flavor | false |
