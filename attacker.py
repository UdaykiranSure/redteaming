# import google.generativeai as genai
from mistralai import Mistral

# class GeminiAttacker:
#     def __init__(self, api_key, model_name="gemini-2.5-flash", system_prompt=None):
#         genai.configure(api_key=api_key)
#         self.model = genai.GenerativeModel(
#             model_name,
#             system_instruction=system_prompt
#         )

#     def generate(self, system_prompt, user_prompt):
#         response = self.model.generate_content(user_prompt)
#         return response.text


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


import requests
import time


class AttackerModel:
    def __init__(
        self,
        base_url="http://localhost:4141/v1/chat/completions",
        model_name="gpt-5-mini",
        timeout=120,
        max_retries=3,
    ):
        self.base_url = base_url
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries
        self.messages = []

    def generate(self, system_prompt, user_prompt):

        payload = {
            "model": self.model_name,
            "messages": [{"role":"system", "content":system_prompt},
                         {"role":"user", "content":user_prompt}],
            "temperature": 0.7,
            "max_tokens": 512,  
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.base_url, json=payload, timeout=self.timeout
                )
                response.raise_for_status()

                data = response.json()

                # ✅ Correct parsing for completions API
                return data["choices"][0]['message']['content']

            except requests.exceptions.HTTPError as e:
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    print(f"Client error (HTTP {e.response.status_code}): {e.response.text}")
                    raise

                if attempt < self.max_retries - 1:
                    wait_time = 5 * (2 ** attempt)
                    print(f"HTTP {e.response.status_code} → retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    wait_time = 5 * (2 ** attempt)
                    print(f"Timeout → retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    print(f"Request error: {e} → retrying...")
                    time.sleep(2 ** attempt)
                else:
                    raise