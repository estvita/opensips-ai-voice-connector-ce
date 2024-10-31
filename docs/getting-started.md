# AI Voice Connector - Community Edition - Getting Started

The simplest way to get the project running is using the Docker Compose file found in the [docker/](docker) directory. In order to use it, you need to setup [Docker](https://www.docker.com/) on your host and then:

* **Clone the repository**
``` shell
git clone https://github.com/OpenSIPS/opensips-ai-voice-connector-ce.git
```

* **Navigate to the docker directory**
``` shell
cd opensips-ai-voice-connector-ce/docker
```

* **Edit the .env file and adjust the settings accordingly**
``` shell
DEEPGRAM_API_KEY= # here you should put your Deepgram API key
OPENAI_API_KEY= # here you should put your OpenAI API key
MI_IP=127.0.0.1 # these are the default values
MI_PORT=8080
```

* **Alternatively, create a configuration file**, for example `config.ini` at the root of the project:
```
[opensips]
ip = 127.0.0.1
port = 8080

[engine]
event_ip = 127.0.0.1

[deepgram]
disabled = false
key = # here you should put your Deepgram API key
chatgpt_key = # here you should put your OpenAI API key

[openai]
disabled = false
key = # here you should put your OpenAI API key
```

* **If you use the configuration file, you need to set the `CONFIG_FILE` in the `.env` file**
``` shell
DEEPGRAM_API_KEY= ... # may be overwritten by the configuration file, if present there
OPENAI_API_KEY= ... # may be overwritten by the configuration file, if present there
...
CONFIG_FILE=config.ini
```

* **Pull the latest images**
``` shell
docker compose pull
```

* **Start the engine**
``` shell
docker compose up

# or if you want to rebuild the Conversational AI image
docker compose up --build
```

* **Now you should have the engine up and running**. You can test it by using a softphone like Zoiper or Linphone to send a call to OpenSIPS by dialling one of the supported flavors (i.e. `openai` - see [flavor selection](docs/ai-flavors.md#flavor-selection)). You should be able to talk to an AI assistant - ask him a question and get a response back.
