import requests
import time


class TargetModel:
    def __init__(
        self,
        base_url="http://localhost:8000/v1/completions",
        model_name="epfl-llm/meditron-7b",
        timeout=120,
        max_retries=3,
    ):
        self.base_url = base_url
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries

    def generate(self, prompt):
        payload = {
            "model": self.model_name,
            "prompt": prompt,
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
                return data["choices"][0]["text"]

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