from database import get_stats, get_config

def check_budget():
    stats = get_stats()
    config = stats["config"]

    pause_pct = float(config.get("pause_at_pct", 75))
    kill_pct  = float(config.get("kill_at_pct", 95))

    if stats["spent_pct"] >= kill_pct:
        return {"allowed": False, "message": "Budget exceeded (kill switch)"}

    if stats["spent_pct"] >= pause_pct:
        return {"allowed": False, "message": "Budget warning (paused)"}

    return {"allowed": True, "message": "ok"}


def check_job_limit(current_tokens, config):
    limit = int(config.get("per_job_token_limit", 500000))

    if current_tokens >= limit:
        return {"allowed": False, "message": "Job token limit exceeded"}

    return {"allowed": True, "message": "ok"}