"""LLM client: unified interface for calling LLM APIs (DeepSeek, Qwen, OpenAI-compatible)."""

import httpx
from backend.config import get_settings


class LLMClient:
    def __init__(self, api_key: str = "", base_url: str = "https://api.deepseek.com", model: str = "deepseek-chat"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def chat(self, system_prompt: str, user_message: str, temperature: float = 0.3) -> str:
        url = self.base_url
        if not url.endswith("/chat/completions"):
            url = f"{url}/v1/chat/completions"
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": temperature,
                    "max_tokens": 4096,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


def get_llm_client() -> LLMClient:
    settings = get_settings()
    api_key = settings.llm_api_key
    base_url = settings.llm_base_url
    model = settings.llm_model

    try:
        from backend.database_sync import SyncSession
        from backend.models.operational import SystemSetting
        with SyncSession() as db:
            result = db.execute(SystemSetting.__table__.select())
            for row in result:
                if row.key == "llm_api_key" and row.value:
                    api_key = row.value
                elif row.key == "llm_base_url" and row.value:
                    base_url = row.value
                elif row.key == "llm_model" and row.value:
                    model = row.value
    except Exception:
        pass

    return LLMClient(api_key=api_key, base_url=base_url, model=model)
