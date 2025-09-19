import os, time, requests, logging
logger = logging.getLogger("llm")

class LLM:
    def __init__(self, url: str | None = None, model: str | None = None):
        self.url = url or os.getenv("LLM_URL", "http://llm-brain:11434/api/chat")
        self.model = model or os.getenv("LLM_MODEL", "mistral")

    def chat(self, messages, temperature: float = 0.7):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature}
        }
        start = time.time()
        res = requests.post(self.url, json=payload, timeout=120)
        res.raise_for_status()
        elapsed = time.time() - start
        data = res.json()
        msg = data.get("message", {}) or {}
        text = (msg.get("content") or "").strip()
        tokens = data.get("eval_count") or len(text.split())
        logger.info(f"LLM '{self.model}' responded in {elapsed:.2f}s")
        return text, tokens
