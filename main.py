import time
import json
import httpx

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from providers import PROVIDERS, calculate_cost
from database  import init_db, record_call, get_stats, get_recent_calls, get_config, set_config, get_daily_spend
from enforcer  import check_budget, check_job_limit

app = FastAPI(title="Guardrail")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

job_token_counts: dict[str, int] = {}


@app.on_event("startup")
def startup():
    init_db()
    print("\n🛡  Guardrail running on http://localhost:4000")
    print("   Change your base URL to:")
    for key in PROVIDERS:
        print(f"   {key:12} → http://localhost:4000/{key}")
    print()


@app.get("/api/stats")
def api_stats():
    return get_stats()


@app.get("/api/calls")
def api_calls(limit: int = 50):
    return get_recent_calls(limit)


@app.get("/api/chart")
def api_chart(days: int = 30):
    return get_daily_spend(days)


@app.get("/api/config")
def api_config():
    return get_config()


@app.post("/api/config")
async def api_set_config(request: Request):
    body = await request.json()
    set_config(body["key"], body["value"])
    return {"ok": True}


@app.get("/health")
def health():
    return {"status": "ok", "providers": list(PROVIDERS.keys())}


@app.api_route("/{provider}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(provider: str, path: str, request: Request):

    if provider not in PROVIDERS:
        raise HTTPException(404, f"Unknown provider '{provider}'. Supported: {list(PROVIDERS.keys())}")

    budget_check = check_budget()
    if not budget_check["allowed"]:
        return JSONResponse(status_code=429, content={
            "error":   "guardrail_budget_exceeded",
            "message": budget_check["message"],
        })

    job_id = request.headers.get("x-guardrail-job-id")
    if job_id:
        current_tokens = job_token_counts.get(job_id, 0)
        config         = get_config()
        job_check      = check_job_limit(current_tokens, config)
        if not job_check["allowed"]:
            return JSONResponse(status_code=429, content={
                "error":   "guardrail_job_limit",
                "message": job_check["message"],
            })

    body_bytes = await request.body()
    try:
        body_json = json.loads(body_bytes)
        model     = body_json.get("model", "default")
    except Exception:
        body_json = {}
        model     = "default"

    provider_config = PROVIDERS[provider]
    target_url      = f"{provider_config['base_url']}/{path}"
    if request.query_params:
        target_url += f"?{request.query_params}"

    forward_headers = dict(request.headers)
    forward_headers.pop("host", None)
    forward_headers.pop("content-length", None)

    start_time = time.time()

    async def stream_response():
        full_response = b""
        input_tokens  = 0
        output_tokens = 0

        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream(
                method  = request.method,
                url     = target_url,
                headers = forward_headers,
                content = body_bytes,
            ) as upstream:
                async for chunk in upstream.aiter_bytes():
                    full_response += chunk
                    yield chunk

        try:
            data  = json.loads(full_response)
            usage = data.get("usage", {})

            if provider == "anthropic":
                input_tokens  = usage.get("input_tokens",          0)
                output_tokens = usage.get("output_tokens",         0)
            elif provider in ("openai", "mistral"):
                input_tokens  = usage.get("prompt_tokens",         0)
                output_tokens = usage.get("completion_tokens",     0)
            elif provider == "gemini":
                input_tokens  = usage.get("promptTokenCount",      0)
                output_tokens = usage.get("candidatesTokenCount",  0)
        except Exception:
            pass

        duration_ms = int((time.time() - start_time) * 1000)
        cost_usd    = calculate_cost(provider, model, input_tokens, output_tokens)

        record_call(
            provider      = provider,
            model         = model,
            job_id        = job_id,
            input_tokens  = input_tokens,
            output_tokens = output_tokens,
            cost_usd      = cost_usd,
            duration_ms   = duration_ms,
        )

        if job_id:
            job_token_counts[job_id] = job_token_counts.get(job_id, 0) + input_tokens + output_tokens

        icon = {"anthropic": "🟣", "openai": "🟢", "gemini": "🔵", "mistral": "🟡"}.get(provider, "⚪")
        print(f"{icon} {provider}/{model} | in:{input_tokens:,} out:{output_tokens:,} | ${cost_usd:.4f} | {duration_ms}ms"
              + (f" | job:{job_id}" if job_id else ""))

    return StreamingResponse(stream_response(), media_type="application/json")