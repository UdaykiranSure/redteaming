import requests
import time


class TargetModel:
    def __init__(
        self,
        base_url="http://localhost:8000/v1/chat/completions",
        model_name="BioMistral/BioMistral-7B",
        timeout=120,
        max_retries=3,
    ):
        self.base_url = base_url
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries

    def _is_chat_endpoint(self):
        return self.base_url.rstrip("/").endswith("/chat/completions")

    def _build_payload(self, prompt):
        common = {
            "model": self.model_name,
            "temperature": 0.7,
            "max_tokens": 512,
        }

        if self._is_chat_endpoint():
            return {
                **common,
                "messages": [{"role": "user", "content": prompt}],
            }

        return {
            **common,
            "prompt": prompt,
        }

    def _parse_response_text(self, data):
        choices = data.get("choices") or []
        if not choices:
            raise ValueError(f"Invalid completion response: missing choices. Raw: {data}")

        first = choices[0]

        # Chat-completions format
        message = first.get("message")
        if isinstance(message, dict) and "content" in message:
            return message["content"]

        # Legacy completions format
        if "text" in first:
            return first["text"]

        raise ValueError(f"Unsupported completion response format. Raw: {data}")

    def generate(self, prompt):
        payload = self._build_payload(prompt)

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.base_url, json=payload, timeout=self.timeout
                )
                response.raise_for_status()

                data = response.json()

                return self._parse_response_text(data)

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