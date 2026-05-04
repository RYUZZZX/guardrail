# Guardrail 🛡
> Stop AI from draining your wallet.

A developer asked AI to review his PR. It ran for 26 hours unnoticed. He woke up to a **$6,000 bill**.

Guardrail is a local proxy that sits between your code and AI APIs — and kills runaway jobs before they cost you money.

## How it works
YOUR APP → Guardrail (localhost:4000) → api.openai.com
↓
checks budget
counts tokens
blocks if over limit

## Features

- 🚨 Hard kill switch — blocks requests before they hit the API
- 💰 Monthly budget limits with pause and kill thresholds
- 🏷️ Per-job token limits — stop any single job from going wild
- 📊 Live dashboard — real-time spend, token counts, call history
- 🔒 100% local — your API calls never touch a third-party server
- ⚡ One line to integrate
- ✅ Free and open source

## Supported providers

| Provider | Base URL |
|---|---|
| Anthropic | `http://localhost:4000/anthropic` |
| OpenAI | `http://localhost:4000/openai` |
| Gemini | `http://localhost:4000/gemini` |
| Mistral | `http://localhost:4000/mistral` |

## Install

```bash
git clone https://github.com/YOUR_USERNAME/guardrail.git
cd guardrail
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
# Terminal 1 — proxy
uvicorn main:app --port 4000

# Terminal 2 — dashboard
python3 dashboard.py
```

Open dashboard at **http://localhost:4001**

## Integrate — one line change

**Python + Anthropic:**
```python
# Before
client = Anthropic()

# After  
client = Anthropic(base_url="http://localhost:4000/anthropic")
```

**Python + OpenAI:**
```python
# Before
client = OpenAI(api_key="...")

# After
client = OpenAI(api_key="...", base_url="http://localhost:4000/openai")
```

## Tag jobs for per-job limits

```python
client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1000,
    messages=[...],
    extra_headers={"x-guardrail-job-id": "pr-review"}
)
```

Guardrail tracks tokens per job ID and kills it when it hits the ceiling.

## Set limits

```bash
# Set monthly budget to $50
curl -X POST http://localhost:4000/api/config \
  -H "Content-Type: application/json" \
  -d '{"key": "monthly_budget_usd", "value": "50"}'
```

Or just use the dashboard sliders at http://localhost:4001

## Built with

- Python 3.12
- FastAPI + Uvicorn
- SQLite
- httpx
- Jinja2

---