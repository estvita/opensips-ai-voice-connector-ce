""" Communicates with ChatGPT AI """

import logging
from openai import AsyncOpenAI  # pylint: disable=import-error


class ChatGPT:
    """ Class that implements ChatGPT communication """
    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model
        self.api = AsyncOpenAI(api_key=api_key)
        self.contexts = {}

    def create_call(self, b2b_key):
        """ Creates a ChatGPT context """
        self.contexts[b2b_key] = []
        hint = "Please answer with simple text messages."
        self.contexts[b2b_key].append({"role": "system",
                                       "content": hint})

    def delete_call(self, b2b_key):
        """ Deletes a ChatGPT context """
        self.contexts.pop(b2b_key)

    async def send_message(self, b2b_key, message):
        """ Sends a ChatGPT message """
        self.contexts[b2b_key].append({"role": "user", "content": message})

        response = await self.api.chat.completions.create(
            model=self.model,
            messages=self.contexts[b2b_key]
        )

        role = response.choices[0].message.role
        content = response.choices[0].message.content
        self.contexts[b2b_key].append({"role": role, "content": content})
        logging.info("Assistant: %s", content)
        return content

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
