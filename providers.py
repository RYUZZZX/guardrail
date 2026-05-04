# providers.py
# Knows about every AI provider — their URL and what each model costs

PROVIDERS = {
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "models": {
            "claude-opus-4-5":    {"input": 15.00, "output": 75.00},
            "claude-sonnet-4-5":  {"input": 3.00,  "output": 15.00},
            "claude-haiku-4-5":   {"input": 0.80,  "output": 4.00},
            "claude-sonnet-4-6":  {"input": 3.00,  "output": 15.00},
            "claude-opus-4-6":    {"input": 15.00, "output": 75.00},
            "default":            {"input": 3.00,  "output": 15.00},
        }
    },
    "openai": {
        "base_url": "https://api.openai.com",
        "models": {
            "gpt-4o":             {"input": 2.50,  "output": 10.00},
            "gpt-4o-mini":        {"input": 0.15,  "output": 0.60},
            "gpt-4-turbo":        {"input": 10.00, "output": 30.00},
            "gpt-3.5-turbo":      {"input": 0.50,  "output": 1.50},
            "o1":                 {"input": 15.00, "output": 60.00},
            "o1-mini":            {"input": 3.00,  "output": 12.00},
            "default":            {"input": 2.50,  "output": 10.00},
        }
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com",
        "models": {
            "gemini-1.5-pro":     {"input": 1.25,  "output": 5.00},
            "gemini-1.5-flash":   {"input": 0.075, "output": 0.30},
            "gemini-2.0-flash":   {"input": 0.10,  "output": 0.40},
            "default":            {"input": 1.25,  "output": 5.00},
        }
    },
    "mistral": {
        "base_url": "https://api.mistral.ai",
        "models": {
            "mistral-large-latest": {"input": 2.00, "output": 6.00},
            "mistral-small-latest": {"input": 0.20, "output": 0.60},
            "default":              {"input": 2.00, "output": 6.00},
        }
    }
}


def calculate_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    provider_config = PROVIDERS.get(provider, {})
    models = provider_config.get("models", {})
    pricing = models.get(model) or models.get("default") or {"input": 0, "output": 0}

    input_cost  = (input_tokens  / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return input_cost + output_cost