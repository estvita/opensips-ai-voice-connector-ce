from openai import AsyncOpenAI

class ChatGPT:
    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model
        self.api = AsyncOpenAI(api_key=api_key)
        self.contexts = {}
    
    def create_call(self, b2b_key):
        self.contexts[b2b_key] = []

    def delete_call(self, b2b_key):
        self.contexts.pop(b2b_key)

    async def send_message(self, b2b_key, message):
        self.contexts[b2b_key].append({"role": "user", "content": message})

        response = await self.api.chat.completions.create(
            model=self.model,
            messages=self.contexts[b2b_key]
        )

        role = response.choices[0].message.role
        content = response.choices[0].message.content
        self.contexts[b2b_key].append({"role": role, "content": content})
        print(f"assistant: {content}")
        return content
