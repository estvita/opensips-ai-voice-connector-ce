## Conversational AI using Deepgram

This project uses Deepgram's Speech-to-Text and Text-to-Speech APIs for Python to create a softphone that can be used to talk to a conversational AI, like ChatGPT.

### How it works
To handle the call flow, OpenSIPS is used as a SIP server, that notifys the softphone when a new call is received (and other call events). The softphone answers the call and starts transmitting the audio to Deepgram's Speech-to-Text engine. The transcribed text is then sent to the conversational AI, which generates a response. The response is then sent to Deepgram's Text-to-Speech engine, which generates the audio that is sent back to caller's phone. You can use Opus, PCMU or PCMA codecs for the audio.

### Running the project
Use the following commands to run the application and an OpenSIPS server:
```bash
cd docker
docker compose up
```

Then, you can use a softphone like Zoiper or Linphone to start a call to the OpenSIPS server. The call will be answered and you can start talking to the conversational AI.

### API Keys
You need to set the following environment variables with your API keys in the [.env](.env) file:
```bash
DEEPGRAM_API_KEY=
OPENAI_API_KEY=
```
