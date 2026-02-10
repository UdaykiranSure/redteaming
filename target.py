import requests
import time

class TargetModel:
    def __init__(self, base_url, model_name="biomistral/biomistral-7b", timeout=120, max_retries=3):
        self.base_url = base_url
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries

    def generate(self, prompt):
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 8192,
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.base_url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    wait_time = 5 * (2 ** attempt)  # Exponential backoff: 5s, 10s, 20s
                    print(f"Timeout on attempt {attempt + 1}/{self.max_retries}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    print(f"Request error on attempt {attempt + 1}/{self.max_retries}: {e}. Retrying...")
                    time.sleep(2 ** attempt)
                else:
                    raise
