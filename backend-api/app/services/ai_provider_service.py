import httpx
from urllib.parse import urlparse, urlunparse

from app.models.ai_provider import utc_now

PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "OpenAI": {
        "base_url": "https://api.openai.com/v1",
        "endpoint_hint": "Leave empty — uses https://api.openai.com/v1",
        "endpoint_example": "",
    },
    "Anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "endpoint_hint": "Leave empty — uses https://api.anthropic.com/v1",
        "endpoint_example": "",
    },
    "Gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "endpoint_hint": "Leave empty — uses Google Generative Language API",
        "endpoint_example": "",
    },
    "Grok": {
        "base_url": "https://api.x.ai/v1",
        "endpoint_hint": "Leave empty — uses https://api.x.ai/v1 (xAI)",
        "endpoint_example": "",
    },
    "DeepSeek": {
        "base_url": "https://api.deepseek.com/v1",
        "endpoint_hint": "Leave empty — uses https://api.deepseek.com/v1",
        "endpoint_example": "",
    },
    "OpenRouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "endpoint_hint": "Leave empty — uses https://openrouter.ai/api/v1",
        "endpoint_example": "",
    },
    "Azure OpenAI": {
        "base_url": "",
        "endpoint_hint": "Azure resource URL — https://YOUR-RESOURCE.openai.azure.com",
        "endpoint_example": "https://your-resource.openai.azure.com",
    },
    "AWS Bedrock": {
        "base_url": "",
        "endpoint_hint": "AWS region (e.g. us-east-1) or Bedrock OpenAI base URL",
        "endpoint_example": "us-east-1",
    },
    "LM Studio": {
        "base_url": "",
        "endpoint_hint": "LM Studio OpenAI-compatible base URL (use /v1 — not the server root URL)",
        "endpoint_example": "http://host.docker.internal:1234/v1",
    },
    "OpenAI-Compatible": {
        "base_url": "",
        "endpoint_hint": "OpenAI-compatible API base URL including /v1",
        "endpoint_example": "http://127.0.0.1:8080/v1",
    },
}

# Static fallback used only when the live Anthropic /v1/models call fails
# (missing/invalid key or the API is unreachable). Keep these as CURRENT ids —
# never reintroduce retired claude-3-* / claude-sonnet-4-* ids here.
ANTHROPIC_FALLBACK_MODELS = [
    "claude-opus-4-8",
    "claude-sonnet-5",
    "claude-haiku-4-5-20251001",
    "claude-fable-5",
]

# Backwards-compatible alias (some callers/tests may import the old name).
ANTHROPIC_MODELS = ANTHROPIC_FALLBACK_MODELS

ANTHROPIC_API_BASE = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"


AZURE_OPENAI_API_VERSION = "2024-08-01-preview"

ENDPOINT_REQUIRED_PROVIDER_TYPES = frozenset(
    {"LM Studio", "OpenAI-Compatible", "Azure OpenAI", "AWS Bedrock"}
)

OPENAI_COMPAT_CHAT_PROVIDER_TYPES = frozenset(
    {
        "OpenAI",
        "Grok",
        "DeepSeek",
        "OpenRouter",
        "LM Studio",
        "OpenAI-Compatible",
        "Azure OpenAI",
        "AWS Bedrock",
    }
)


def endpoint_required(provider_type: str) -> bool:
    return provider_type in ENDPOINT_REQUIRED_PROVIDER_TYPES


def get_endpoint_hint(provider_type: str) -> str:
    return PROVIDER_DEFAULTS.get(provider_type, {}).get("endpoint_hint", "")


def get_endpoint_example(provider_type: str) -> str:
    return PROVIDER_DEFAULTS.get(provider_type, {}).get("endpoint_example", "")


def build_openai_compatible_headers(api_key: str | None = None) -> dict[str, str]:
    """Build auth headers for OpenAI-compatible APIs. Omits Authorization when key is empty."""
    headers: dict[str, str] = {}
    normalized_key = (api_key or "").strip()
    if normalized_key:
        headers["Authorization"] = f"Bearer {normalized_key}"
    return headers


def resolve_base_url(provider_type: str, endpoint: str) -> str:
    custom = endpoint.strip().rstrip("/")
    if custom:
        if provider_type == "LM Studio":
            return normalize_lm_studio_endpoint(custom)
        return custom
    default = PROVIDER_DEFAULTS.get(provider_type, {}).get("base_url", "")
    if not default:
        raise ValueError(f"Endpoint is required for {provider_type}")
    return default


def normalize_lm_studio_endpoint(endpoint: str) -> str:
    """Normalize LM Studio URL to the OpenAI-compatible /v1 base path."""
    cleaned = endpoint.strip().rstrip("/")
    if "://" not in cleaned:
        cleaned = f"http://{cleaned}"

    parsed = urlparse(cleaned)
    path = parsed.path or ""

    for suffix in ("/chat/completions", "/models", "/completions"):
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break

    if path.endswith("/api/v1"):
        path = "/v1"
    elif not path or path == "/":
        path = "/v1"
    elif not path.endswith("/v1"):
        path = "/v1"

    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def lm_studio_endpoint_candidates(endpoint: str) -> list[str]:
    """Return the LM Studio base URL plus a Docker-host fallback.

    The backend usually runs in a container. On Docker Desktop (Mac/Windows) a container
    can reach the host only via 'host.docker.internal' — NOT via the host's own LAN IP or
    localhost. So when the user enters localhost / 127.0.0.1 / a LAN IP, we also try the
    host.docker.internal equivalent (same scheme/port/path). The literal entry is tried
    first, so non-Docker deployments are unaffected; the fallback only kicks in if it fails.
    """
    primary = normalize_lm_studio_endpoint(endpoint)
    candidates = [primary]

    parsed = urlparse(primary)
    host = (parsed.hostname or "").lower()
    if host and host != "host.docker.internal":
        port = f":{parsed.port}" if parsed.port else ""
        docker_host = urlunparse(
            (parsed.scheme, f"host.docker.internal{port}", parsed.path, "", "", "")
        )
        if docker_host not in candidates:
            candidates.append(docker_host)

    return candidates


def normalize_azure_resource_endpoint(endpoint: str) -> str:
    """Reduce an Azure OpenAI URL to the resource root (scheme + host)."""
    cleaned = endpoint.strip().rstrip("/")
    if "://" not in cleaned:
        cleaned = f"https://{cleaned}"
    parsed = urlparse(cleaned)
    path = parsed.path or ""
    if "/openai" in path:
        path = path.split("/openai", 1)[0]
    if not path or path == "/":
        path = ""
    return urlunparse((parsed.scheme or "https", parsed.netloc, path, "", "", "")).rstrip("/")


def resolve_bedrock_openai_base(endpoint: str) -> str:
    """Bedrock OpenAI-compatible API base (…/openai/v1)."""
    cleaned = endpoint.strip().rstrip("/")
    if not cleaned:
        cleaned = "us-east-1"
    if "://" in cleaned:
        if cleaned.endswith("/openai/v1"):
            return cleaned
        if "/openai/" in cleaned:
            return cleaned.split("/openai/", 1)[0] + "/openai/v1"
        return f"{cleaned}/openai/v1"
    region = cleaned
    return f"https://bedrock-runtime.{region}.amazonaws.com/openai/v1"


def prepare_openai_chat_request(
    *,
    provider_type: str,
    api_key: str,
    model: str,
    messages: list,
    tools: list,
    endpoint: str = "",
    base_url: str = "",
) -> tuple[str, dict[str, str], dict]:
    """Build URL, headers, and JSON body for an OpenAI-style chat/completions call."""
    if provider_type == "Azure OpenAI":
        if not endpoint.strip():
            raise ValueError("Endpoint is required for Azure OpenAI")
        resource = normalize_azure_resource_endpoint(endpoint)
        url = (
            f"{resource}/openai/deployments/{model}/chat/completions"
            f"?api-version={AZURE_OPENAI_API_VERSION}"
        )
        headers = {
            "api-key": api_key.strip(),
            "Content-Type": "application/json",
        }
        payload = {
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
        }
        return url, headers, payload

    resolved_base = base_url or resolve_base_url(provider_type, endpoint)
    url = f"{resolved_base.rstrip('/')}/chat/completions"
    headers = build_openai_compatible_headers(api_key)
    headers["Content-Type"] = "application/json"

    if provider_type == "OpenRouter":
        headers["HTTP-Referer"] = "https://github.com/juampa/jpilot"
        headers["X-Title"] = "JPilot"

    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
    }
    return url, headers, payload


async def fetch_models(provider_type: str, api_key: str, endpoint: str) -> list[str]:
    if provider_type == "OpenAI":
        return await _fetch_openai_models(api_key, resolve_base_url(provider_type, endpoint))
    if provider_type == "Anthropic":
        # Missing key: let the caller show "API key required" (don't silently
        # serve a fallback that hides the real problem).
        if not api_key or not api_key.strip():
            raise ValueError("API key is required")
        try:
            return await _fetch_anthropic_models(api_key, resolve_base_url(provider_type, endpoint))
        except (httpx.ConnectError, httpx.TimeoutException, httpx.TransportError):
            # Provider unreachable / network hiccup: keep the form usable with a
            # small static list of CURRENT ids (never stale).
            return list(ANTHROPIC_FALLBACK_MODELS)
        # Auth/permission/quota errors (ValueError / AiProviderError) propagate so
        # the UI can tell the user to check the key — the router maps them to a
        # clean 4xx message, not a 500 stacktrace.
    if provider_type == "Gemini":
        return await _fetch_gemini_models(api_key)
    if provider_type == "Grok":
        return await _fetch_openai_models(api_key, resolve_base_url(provider_type, endpoint))
    if provider_type == "DeepSeek":
        return await _fetch_openai_models(api_key, resolve_base_url(provider_type, endpoint))
    if provider_type == "OpenRouter":
        return await _fetch_openai_models(api_key, resolve_base_url(provider_type, endpoint))
    if provider_type == "Azure OpenAI":
        return await _fetch_azure_deployments(api_key, endpoint)
    if provider_type == "AWS Bedrock":
        return await _fetch_openai_compatible_models(
            resolve_bedrock_openai_base(endpoint),
            api_key,
            provider_type=provider_type,
        )
    if provider_type in {"LM Studio", "OpenAI-Compatible"}:
        return await _fetch_openai_compatible_models(
            resolve_base_url(provider_type, endpoint),
            api_key,
            provider_type=provider_type,
        )
    raise ValueError(f"Unsupported provider type: {provider_type}")


async def test_provider(
    provider_type: str,
    api_key: str,
    endpoint: str,
    model: str = "",
) -> tuple[bool, str]:
    try:
        models = await fetch_models(provider_type, api_key, endpoint)
        if model and model not in models:
            return False, f"Connection succeeded but model '{model}' was not found"
        count = len(models)
        sample = models[0] if models else "none"
        return True, f"Connected successfully — {count} model(s) available (e.g. {sample})"
    except Exception as exc:
        from app.services.ai_provider_errors import maybe_parse_ai_provider_error

        parsed = maybe_parse_ai_provider_error(str(exc), provider_type=provider_type)
        if parsed is not None:
            return False, str(parsed)
        return False, str(exc)


async def _fetch_openai_models(api_key: str, base_url: str) -> list[str]:
    if not api_key:
        raise ValueError("API key is required")

    url = f"{base_url.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        payload = response.json()

    models = sorted(
        item["id"]
        for item in payload.get("data", [])
        if isinstance(item, dict) and item.get("id")
    )
    if not models:
        raise ValueError("No models returned from provider")
    return models


async def _fetch_anthropic_models(api_key: str, base_url: str) -> list[str]:
    """Live-list Anthropic models via GET /v1/models (paginated).

    Requires the provider's API key. Loops on `has_more` using `after_id=last_id`
    to collect every model, then returns ids sorted newest-first by `created_at`.

    On any failure (missing/invalid key, network error, unexpected payload) this
    raises so the caller can surface a clean error AND still fall back to a small
    static list of CURRENT ids — a stale id can never be the only option served.
    """
    if not api_key or not api_key.strip():
        raise ValueError("API key is required")

    url = f"{(base_url or ANTHROPIC_API_BASE).rstrip('/')}/models"
    headers = {
        "x-api-key": api_key.strip(),
        "anthropic-version": ANTHROPIC_VERSION,
    }

    collected: list[dict] = []
    after_id: str | None = None

    async with httpx.AsyncClient(timeout=20.0) as client:
        # Guard the loop so a misbehaving API can't spin forever.
        for _ in range(50):
            params: dict[str, str] = {"limit": "100"}
            if after_id:
                params["after_id"] = after_id

            response = await client.get(url, headers=headers, params=params)
            if response.status_code >= 400:
                from app.services.ai_provider_errors import raise_for_ai_provider_response

                raise_for_ai_provider_response(
                    response, provider_type="Anthropic", model=""
                )
            payload = response.json()

            page = payload.get("data", [])
            if isinstance(page, list):
                collected.extend(item for item in page if isinstance(item, dict) and item.get("id"))

            if not payload.get("has_more"):
                break
            after_id = payload.get("last_id")
            if not after_id:
                break

    if not collected:
        raise ValueError("No models returned from Anthropic")

    # Newest-first by created_at (epoch or ISO); fall back to id ordering.
    def _sort_key(item: dict):
        created = item.get("created_at")
        if isinstance(created, (int, float)):
            return (1, float(created))
        if isinstance(created, str) and created:
            return (1, created)
        return (0, item.get("id", ""))

    collected.sort(key=_sort_key, reverse=True)
    models = [item["id"] for item in collected]
    # De-dupe while preserving newest-first order.
    seen: set[str] = set()
    return [m for m in models if not (m in seen or seen.add(m))]


async def _fetch_openai_compatible_models(
    base_url: str,
    api_key: str,
    provider_type: str = "OpenAI-Compatible",
) -> list[str]:
    urls = lm_studio_endpoint_candidates(base_url) if provider_type == "LM Studio" else [base_url]
    errors: list[str] = []

    for candidate in urls:
        try:
            return await _fetch_models_at_base(candidate, api_key)
        except Exception as exc:
            errors.append(f"{candidate}: {exc}")

    hint = ""
    if provider_type == "LM Studio":
        hint = (
            " If Copilot runs in Docker and LM Studio is on your computer, use "
            "http://host.docker.internal:1234/v1 and enable 'Serve on local network' in LM Studio."
        )

    raise ValueError(f"Could not reach {provider_type}. {' | '.join(errors)}.{hint}")


async def migrate_lm_studio_endpoints(db) -> int:
    """Persist normalized /v1 LM Studio endpoints (fixes legacy /api/v1 values)."""
    updated = 0
    async for provider in db.aiProviders.find({"providerType": "LM Studio"}):
        endpoint = provider.get("endpoint", "")
        if not endpoint.strip():
            continue
        normalized = normalize_lm_studio_endpoint(endpoint)
        if normalized != endpoint:
            await db.aiProviders.update_one(
                {"_id": provider["_id"]},
                {"$set": {"endpoint": normalized, "updatedAt": utc_now()}},
            )
            updated += 1
    return updated


async def _fetch_models_at_base(base_url: str, api_key: str) -> list[str]:
    url = f"{base_url.rstrip('/')}/models"
    headers = build_openai_compatible_headers(api_key)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            payload = response.json()
    except httpx.ConnectError as exc:
        raise ValueError(f"connection refused ({exc})") from exc
    except httpx.TimeoutException as exc:
        raise ValueError("connection timed out") from exc

    if isinstance(payload, dict) and "data" in payload:
        models = [item["id"] for item in payload["data"] if isinstance(item, dict) and item.get("id")]
    elif isinstance(payload, list):
        models = [item.get("id", item.get("name", "")) for item in payload if isinstance(item, dict)]
    else:
        models = []

    models = sorted({model for model in models if model})
    if not models:
        raise ValueError(f"no models returned from {url}")
    return models


async def _fetch_azure_deployments(api_key: str, endpoint: str) -> list[str]:
    if not api_key:
        raise ValueError("API key is required")
    if not endpoint.strip():
        raise ValueError("Endpoint is required for Azure OpenAI")

    resource = normalize_azure_resource_endpoint(endpoint)
    url = f"{resource}/openai/deployments?api-version=2024-06-01"
    headers = {"api-key": api_key.strip()}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        payload = response.json()

    deployments = sorted(
        item["id"]
        for item in payload.get("data", [])
        if isinstance(item, dict) and item.get("id")
    )
    if not deployments:
        raise ValueError(
            "No Azure OpenAI deployments found. Create a deployment in Azure AI Foundry, "
            "then reload models."
        )
    return deployments


async def _fetch_gemini_models(api_key: str) -> list[str]:
    if not api_key:
        raise ValueError("API key is required")

    url = "https://generativelanguage.googleapis.com/v1beta/models"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, params={"key": api_key})
        response.raise_for_status()
        payload = response.json()

    models = sorted(
        item["name"].replace("models/", "")
        for item in payload.get("models", [])
        if isinstance(item, dict)
        and item.get("name")
        and "generateContent" in item.get("supportedGenerationMethods", [])
    )
    if not models:
        raise ValueError("No models returned from Gemini")
    return models
