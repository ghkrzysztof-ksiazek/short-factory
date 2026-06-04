import json
from abc import ABC, abstractmethod

from anthropic import Anthropic
from openai import OpenAI

from short_factory.config.settings import settings


class LLMClient(ABC):
    @abstractmethod
    def complete(self, prompt: str, system: str = "", json_mode: bool = False) -> str:
        pass


class OpenAIClient(LLMClient):
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.openai_api_key)

    def complete(self, prompt: str, system: str = "", json_mode: bool = False) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        kwargs = {"model": settings.llm_model, "messages": messages}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""


class AnthropicClient(LLMClient):
    def __init__(self) -> None:
        self.client = Anthropic(api_key=settings.anthropic_api_key)

    def complete(self, prompt: str, system: str = "", json_mode: bool = False) -> str:
        user_content = prompt
        if json_mode:
            user_content += "\n\nRespond with valid JSON only."
        response = self.client.messages.create(
            model=settings.llm_model,
            max_tokens=4096,
            system=system or "You are a helpful assistant.",
            messages=[{"role": "user", "content": user_content}],
        )
        return response.content[0].text


class GrokClient(LLMClient):
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.grok_api_key, base_url=settings.grok_api_base)

    def complete(self, prompt: str, system: str = "", json_mode: bool = False) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        kwargs = {"model": settings.llm_model, "messages": messages}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""


def get_llm_client() -> LLMClient:
    if settings.llm_provider == "anthropic":
        return AnthropicClient()
    if settings.llm_provider == "grok":
        return GrokClient()
    return OpenAIClient()


def parse_json_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)
