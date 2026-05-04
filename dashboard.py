import uvicorn
import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from jinja2 import Environment, FileSystemLoader

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

env = Environment(loader=FileSystemLoader("templates"))

PROXY_URL = "http://localhost:4000"


@app.get("/", response_class=HTMLResponse)
async def index():
    try:
        async with httpx.AsyncClient() as client:
            stats = (await client.get(f"{PROXY_URL}/api/stats")).json()
            calls = (await client.get(f"{PROXY_URL}/api/calls?limit=10")).json()
            chart = (await client.get(f"{PROXY_URL}/api/chart")).json()
    except Exception:
        stats = {
            "spent_usd": 0,
            "budget_usd": 500,
            "spent_pct": 0,
            "call_count": 0,
            "total_tokens": 0,
            "config": {
                "monthly_budget_usd": "500",
                "pause_at_pct": "75",
                "kill_at_pct": "95",
                "per_job_token_limit": "500000",
            }
        }
        calls = []
        chart = []

    chart_labels = [row["day"]   for row in chart] if chart else []
    chart_values = [row["total"] for row in chart] if chart else []

    template = env.get_template("index.html")
    return template.render(
        stats=stats,
        calls=calls,
        chart=chart,
        chart_labels=chart_labels,
        chart_values=chart_values,
    )


@app.post("/set-config")
async def set_config(key: str, value: str):
    async with httpx.AsyncClient() as client:
        await client.post(f"{PROXY_URL}/api/config", json={"key": key, "value": value})
    return HTMLResponse('<script>window.location="/"</script>')


if __name__ == "__main__":
    uvicorn.run("dashboard:app", host="0.0.0.0", port=4001, reload=True)