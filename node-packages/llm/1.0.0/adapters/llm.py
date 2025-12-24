"""LLM adapters for cloud and local providers."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urljoin

from worker.execution import ExecutionContext

DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "openai_compatible": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
    "google": "https://generativelanguage.googleapis.com/v1beta",
    "ollama": "http://localhost:11434",
}

RESOURCE_KEYS_BY_PROVIDER = {
    "openai": ["openai_api_key"],
    "openai_compatible": ["openai_compatible_api_key", "openai_api_key"],
    "anthropic": ["anthropic_api_key"],
    "google": ["google_api_key"],
}


def _as_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except Exception:
        return default


def _as_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except Exception:
        return default


def _normalize_messages(value: Any) -> List[Dict[str, str]]:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if not isinstance(value, list):
        return []
    messages: List[Dict[str, str]] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        content = entry.get("content")
        if not role or content is None:
            continue
        messages.append({"role": str(role), "content": str(content)})
    return messages


def _build_messages(params: Dict[str, Any]) -> List[Dict[str, str]]:
    messages = _normalize_messages(params.get("messages"))
    if messages:
        return messages
    prompt = _as_str(params.get("prompt"), "").strip()
    if not prompt:
        raise ValueError("prompt or messages is required")
    system = _as_str(params.get("system"), "").strip()
    result: List[Dict[str, str]] = []
    if system:
        result.append({"role": "system", "content": system})
    result.append({"role": "user", "content": prompt})
    return result


def _resolve_api_key(params: Dict[str, Any], provider: str) -> Optional[str]:
    bindings = _extract_resource_bindings(params)
    for resource_key in RESOURCE_KEYS_BY_PROVIDER.get(provider, []):
        value = _read_binding_value(bindings.get(resource_key))
        if value:
            return value
    return None


def _ensure_no_direct_api_keys(params: Dict[str, Any]) -> None:
    for key in ("apiKey", "apiKeyEnv"):
        if key not in params:
            continue
        value = params.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        raise ValueError("Direct apiKey/apiKeyEnv parameters are disabled. Use resource grants instead.")


def _extract_resource_bindings(params: Dict[str, Any]) -> Dict[str, Any]:
    bindings = params.get("__resourceBindings") or params.get("resourceBindings")
    return bindings if isinstance(bindings, dict) else {}


def _read_binding_value(binding: Any) -> Optional[str]:
    if binding is None:
        return None
    if isinstance(binding, str):
        return binding.strip() or None
    if isinstance(binding, dict):
        value = binding.get("value")
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip() or None
        return str(value).strip() or None
    return None


def _join_url(base: str, path: str) -> str:
    base = base.rstrip("/") + "/"
    return urljoin(base, path.lstrip("/"))


def _request_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: float) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "ignore")
        raise RuntimeError(f"HTTP {exc.code}: {body or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Request failed: {exc.reason}") from exc
    return json.loads(raw.decode("utf-8"))


def _openai_chat(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: Optional[float],
    top_p: Optional[float],
    max_tokens: Optional[int],
    stop: Any,
    timeout: float,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"model": model, "messages": messages}
    if temperature is not None:
        payload["temperature"] = temperature
    if top_p is not None:
        payload["top_p"] = top_p
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if stop:
        payload["stop"] = stop
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    url = _join_url(base_url, "chat/completions")
    return _request_json(url, payload, headers, timeout)


def _anthropic_chat(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    system: str,
    temperature: Optional[float],
    top_p: Optional[float],
    max_tokens: Optional[int],
    stop: Any,
    timeout: float,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens or 1024,
    }
    if system:
        payload["system"] = system
    if temperature is not None:
        payload["temperature"] = temperature
    if top_p is not None:
        payload["top_p"] = top_p
    if stop:
        payload["stop_sequences"] = stop if isinstance(stop, list) else [stop]
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    url = _join_url(base_url, "v1/messages")
    return _request_json(url, payload, headers, timeout)


def _ollama_chat(
    *,
    base_url: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: Optional[float],
    top_p: Optional[float],
    max_tokens: Optional[int],
    timeout: float,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    options: Dict[str, Any] = {}
    if temperature is not None:
        options["temperature"] = temperature
    if top_p is not None:
        options["top_p"] = top_p
    if max_tokens is not None:
        options["num_predict"] = max_tokens
    if options:
        payload["options"] = options
    headers = {"Content-Type": "application/json"}
    url = _join_url(base_url, "api/chat")
    return _request_json(url, payload, headers, timeout)


def _google_generate(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    temperature: Optional[float],
    top_p: Optional[float],
    max_tokens: Optional[int],
    timeout: float,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ]
    }
    generation: Dict[str, Any] = {}
    if temperature is not None:
        generation["temperature"] = temperature
    if top_p is not None:
        generation["topP"] = top_p
    if max_tokens is not None:
        generation["maxOutputTokens"] = max_tokens
    if generation:
        payload["generationConfig"] = generation
    headers = {"Content-Type": "application/json"}
    url = _join_url(base_url, f"models/{model}:generateContent")
    url = f"{url}?{urlencode({'key': api_key})}"
    return _request_json(url, payload, headers, timeout)


def _extract_openai_text(response: Dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if choices:
        message = choices[0].get("message")
        if message and message.get("content") is not None:
            return str(message.get("content"))
        text = choices[0].get("text")
        if text is not None:
            return str(text)
    return ""


def _extract_anthropic_text(response: Dict[str, Any]) -> str:
    content = response.get("content") or []
    parts = [part.get("text") for part in content if isinstance(part, dict) and part.get("text")]
    return "".join(parts)


def _extract_ollama_text(response: Dict[str, Any]) -> str:
    message = response.get("message")
    if isinstance(message, dict) and message.get("content") is not None:
        return str(message.get("content"))
    if response.get("response") is not None:
        return str(response.get("response"))
    return ""


def _extract_google_text(response: Dict[str, Any]) -> str:
    candidates = response.get("candidates") or []
    if not candidates:
        return ""
    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    texts = [part.get("text") for part in parts if isinstance(part, dict) and part.get("text")]
    return "".join(texts)


def _render_messages(messages: List[Dict[str, str]]) -> str:
    lines: List[str] = []
    for message in messages:
        role = message.get("role") or ""
        content = message.get("content") or ""
        if role:
            lines.append(f"{role}: {content}")
        else:
            lines.append(content)
    return "\n".join(lines).strip()


def _build_result(
    *,
    provider: str,
    model: str,
    text: str,
    raw: Dict[str, Any],
    usage: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "status": "succeeded",
        "text": text,
        "provider": provider,
        "model": model,
        "raw": raw,
    }
    if usage is not None:
        payload["usage"] = usage
    return payload


def _build_error(provider: str, model: str, error: Exception) -> Dict[str, Any]:
    return {
        "status": "failed",
        "provider": provider,
        "model": model,
        "error": str(error),
    }


async def chat(context: ExecutionContext) -> Dict[str, Any]:
    params = context.params or {}
    provider = _as_str(params.get("provider"), "openai").lower().strip()
    model = _as_str(params.get("model")).strip()
    if not model:
        return _build_error(provider, model, ValueError("model is required"))

    try:
        _ensure_no_direct_api_keys(params)
    except Exception as exc:
        return _build_error(provider, model, exc)

    try:
        messages = _build_messages(params)
    except Exception as exc:
        return _build_error(provider, model, exc)

    system = _as_str(params.get("system"), "").strip()
    if not system:
        for message in messages:
            if message.get("role") == "system":
                system = _as_str(message.get("content"), "").strip()
                if system:
                    break
    temperature = _as_float(params.get("temperature"))
    top_p = _as_float(params.get("topP"))
    max_tokens = _as_int(params.get("maxTokens"))
    stop = params.get("stop")
    timeout = _as_float(params.get("timeoutSeconds"), 60.0) or 60.0
    base_url = _as_str(params.get("baseUrl"), "").strip() or DEFAULT_BASE_URLS.get(provider, "")

    try:
        if provider == "ollama":
            if not base_url:
                raise ValueError("baseUrl is required for ollama")
            response = await asyncio.to_thread(
                _ollama_chat,
                base_url=base_url,
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            text = _extract_ollama_text(response)
            return _build_result(provider=provider, model=model, text=text, raw=response)

        if provider == "anthropic":
            api_key = _resolve_api_key(params, provider)
            if not api_key:
                raise ValueError("API key is required for anthropic")
            anthropic_messages = [m for m in messages if m.get("role") != "system"]
            response = await asyncio.to_thread(
                _anthropic_chat,
                base_url=base_url,
                api_key=api_key,
                model=model,
                messages=anthropic_messages,
                system=system,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stop=stop,
                timeout=timeout,
            )
            text = _extract_anthropic_text(response)
            usage = response.get("usage") if isinstance(response, dict) else None
            return _build_result(provider=provider, model=model, text=text, raw=response, usage=usage)

        if provider == "google":
            api_key = _resolve_api_key(params, provider)
            if not api_key:
                raise ValueError("API key is required for google")
            prompt = _render_messages(messages)
            response = await asyncio.to_thread(
                _google_generate,
                base_url=base_url,
                api_key=api_key,
                model=model,
                prompt=prompt,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            text = _extract_google_text(response)
            usage = response.get("usageMetadata") if isinstance(response, dict) else None
            return _build_result(provider=provider, model=model, text=text, raw=response, usage=usage)

        api_key = _resolve_api_key(params, provider)
        if not api_key:
            raise ValueError("API key is required for openai-compatible providers")
        response = await asyncio.to_thread(
            _openai_chat,
            base_url=base_url or DEFAULT_BASE_URLS["openai"],
            api_key=api_key,
            model=model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stop=stop,
            timeout=timeout,
        )
        text = _extract_openai_text(response)
        usage = response.get("usage") if isinstance(response, dict) else None
        return _build_result(provider=provider, model=model, text=text, raw=response, usage=usage)
    except Exception as exc:
        return _build_error(provider, model, exc)
