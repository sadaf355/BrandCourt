"""Optional, schema-validated model providers for the checking engine."""
from __future__ import annotations

import json
import os
from typing import Any, Protocol
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelStepFailed(RuntimeError):
    pass


class ClaimCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim: str = Field(min_length=1, max_length=2000)


class ClaimExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claims: list[ClaimCandidate] = Field(max_length=100)


class Adjudication(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdict: Literal["supported", "contradicted", "needs_human_review"]
    fact_id: str = Field(min_length=1, max_length=36)
    quote: str = Field(min_length=1, max_length=1000)
    reason: str = Field(min_length=1, max_length=1000)


class ModelProvider(Protocol):
    name: str
    model: str

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
    ) -> Any: ...


class DisabledProvider:
    name = "disabled"
    model = "none"

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
    ) -> Any:
        raise ModelStepFailed("Model provider is disabled.")


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
    ) -> Any:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "stream": False,
                        "format": schema,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
                response.raise_for_status()
                payload = response.json()
            content = payload.get("message", {}).get("content")
            return _decode_json(content)
        except httpx.HTTPError as exc:
            raise ModelStepFailed("Ollama request failed.") from exc


class OpenAICompatibleProvider:
    name = "openai_compatible"

    def __init__(self, base_url: str, model: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
    ) -> Any:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": {"name": "brandcourt_output", "schema": schema},
                        },
                    },
                )
                response.raise_for_status()
                payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            return _decode_json(content)
        except httpx.HTTPError as exc:
            raise ModelStepFailed("Hosted model request failed.") from exc


def _decode_json(content: Any) -> Any:
    if not isinstance(content, str):
        raise ModelStepFailed("Model response did not contain JSON text.")
    try:
        return json.loads(content)
    except (TypeError, ValueError) as exc:
        raise ModelStepFailed("Model response was not valid JSON.") from exc


def configured_provider(settings: Any, model_mode: str | None = None) -> ModelProvider:
    mode = str(model_mode or settings.model_mode).lower()
    if mode == "ollama":
        return OllamaProvider(settings.ollama_base_url, settings.ollama_model)
    if mode in {"openai", "openai_compatible", "hosted"}:
        base_url = os.environ.get("OPENAI_COMPATIBLE_BASE_URL", "").strip()
        model = os.environ.get("OPENAI_COMPATIBLE_MODEL", "").strip()
        api_key = os.environ.get("OPENAI_COMPATIBLE_API_KEY", "").strip()
        if not (base_url and model and api_key):
            raise ModelStepFailed("Hosted model provider configuration is incomplete.")
        return OpenAICompatibleProvider(base_url, model, api_key)
    return DisabledProvider()


async def validated_json(
    provider: ModelProvider,
    *,
    system_prompt: str,
    user_prompt: str,
    output_model: type[BaseModel],
    on_call: Any,
) -> BaseModel:
    """Validate provider output and retry one time; every attempt is reported to on_call."""
    schema = output_model.model_json_schema()
    last_error: Exception | None = None
    for attempt in range(2):
        await on_call("started", attempt)
        try:
            result = await provider.complete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=schema,
            )
            validated = output_model.model_validate(result)
            await on_call("completed", attempt)
            return validated
        except Exception as exc:
            last_error = exc
            await on_call("failed", attempt)
    raise ModelStepFailed(
        f"Model output failed schema validation after one retry ({type(last_error).__name__})."
    ) from last_error


def verify_adjudication_quote(
    adjudication: Adjudication,
    *,
    expected_fact_id: str,
    fact_text: str,
    masked_value_map: dict[str, str] | None = None,
) -> bool:
    quote = adjudication.quote
    for token, original in (masked_value_map or {}).items():
        quote = quote.replace(token, original)
    return adjudication.fact_id == expected_fact_id and quote in fact_text
