import google.generativeai as genai
from mistralai import Mistral

class GeminiAttacker:
    def __init__(self, api_key, model_name="gemini-2.5-flash", system_prompt=None):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name,
            system_instruction=system_prompt
        )

    def generate(self, system_prompt, user_prompt):
        response = self.model.generate_content(user_prompt)
        return response.text


class MistralAttacker:
    def __init__(self, api_key, model_name="mistral-large-latest", system_prompt=None):
        self.client = Mistral(api_key=api_key)
        self.model_name = model_name
        self.system_prompt = system_prompt

    def generate(self, system_prompt, user_prompt):
        messages = []
        if self.system_prompt or system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt or self.system_prompt
            })
        messages.append({
            "role": "user",
            "content": user_prompt
        })
        
        response = self.client.chat.complete(
            model=self.model_name,
            messages=messages
        )
        return response.choices[0].message.content
