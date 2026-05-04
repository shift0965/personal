import json
import os
import random
import subprocess
from datetime import datetime, timedelta, timezone

from config import USER_PROFILE
from leetcode import get_problem_url


def filter_and_sample(problems: list[dict], solved_ids: set[str], sent: list[dict], sample_size: int = 100) -> list[dict]:
    """Filter out solved/recently-sent problems, then uniform-random sample.

    - Removes solved problems (from Solved tab)
    - Removes problems sent in the last 16 months
    - Randomly samples `sample_size` problems (uniform, each problem has equal chance)
    """
    # Build set of recently-sent IDs (last 16 months)
    cutoff = datetime.now(timezone.utc) - timedelta(days=16 * 30)
    recently_sent_ids = set()
    for s in sent:
        try:
            sent_date = datetime.strptime(s["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if sent_date >= cutoff:
                recently_sent_ids.add(s["id"])
        except (ValueError, KeyError):
            recently_sent_ids.add(s.get("id", ""))

    # Filter
    pool = [
        p for p in problems
        if p["id"] not in solved_ids and p["id"] not in recently_sent_ids
    ]

    if not pool:
        return []

    # Uniform random sample
    if len(pool) <= sample_size:
        return pool

    return random.sample(pool, sample_size)


def pick_problems(sampled: list[dict], feedback: list[dict]) -> tuple[list[dict], dict]:
    """Ask Claude to pick 3 problems from the sampled list based on feedback.

    Returns (list of 3 problem dicts with 'reason' field, usage_info).
    """
    prompt = f"""You are a LeetCode problem recommendation engine for a software engineer preparing for Mag 7 interviews.

## User Profile
{USER_PROFILE}
"""
    if feedback:
        prompt += "\n## Recent Feedback (how the user rated previous problems)\n"
        for fb in feedback[-20:]:
            rating = fb.get("difficulty_rating", "")
            title = fb.get("title", "")
            tags = fb.get("tags", "")
            notes = fb.get("notes", "")
            if rating and title:
                prompt += f'- "{title}" ({tags}) — difficulty rating {rating}/5'
                if notes:
                    prompt += f" ({notes})"
                prompt += "\n"

    prompt += "\n## Available Problems (random sample from unsolved pool)\n"
    prompt += "ID | Title | Difficulty | Tags\n"
    prompt += "---|-------|-----------|-----\n"
    for p in sampled:
        tags = p.get("tags", "")
        if isinstance(tags, list):
            tags = ", ".join(tags)
        prompt += f'{p["id"]} | {p["title"]} | {p["difficulty"]} | {tags}\n'

    prompt += """
## Task
Pick exactly 3 problems from the available list above for this user to practice today.

Selection criteria:
1. **Weak areas first** — pick topics where the user rated difficulty high (4-5) or left struggling notes
2. **Difficulty progression** — appropriate mix of Medium/Hard based on topic mastery
3. **Topic diversity** — pick 3 DIFFERENT topics, not 3 problems from the same category
4. **Interview relevance** — prioritize patterns common in Mag 7 interviews
5. **IMPORTANT: Ignore sample distribution** — the input is a random sample from a larger pool. Do NOT pick topics just because they appear more frequently in this sample. Base your topic selection SOLELY on the user's feedback and weak areas. If there is no feedback yet, pick 3 diverse topics that are most commonly tested in FAANG interviews.

Return ONLY a valid JSON array of exactly 3 objects:
[{"id": "123", "title": "Problem Name", "slug": "problem-slug", "difficulty": "Medium", "tags": ["Tag1", "Tag2"], "reason": "One sentence explaining why this problem was chosen"}]

No markdown, no explanation. Just the raw JSON array.
"""
    raw_output, usage = _call_claude_cli(prompt)

    try:
        results = _parse_json_response(raw_output)
        if not isinstance(results, list):
            print("[WARN] Claude returned non-array.")
            return [], usage
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[WARN] Failed to parse Claude response: {e}")
        return [], usage

    # Add URLs
    for r in results:
        r["url"] = get_problem_url(r.get("slug", ""))

    return results, usage


def _call_claude_cli(prompt: str) -> tuple[str, dict]:
    """Call claude CLI using the user's Pro plan. Returns (response_text, usage_info)."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    claude_bin = os.environ.get("CLAUDE_BIN", "/opt/homebrew/bin/claude")
    result = subprocess.run(
        [claude_bin, "-p", "--model", "sonnet", "--output-format", "json",
         "--max-turns", "1", "--allowedTools", ""],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )
    if result.returncode != 0:
        details = result.stderr[:500] or result.stdout[:500]
        raise RuntimeError(f"claude CLI failed (exit {result.returncode}): {details}")

    raw = result.stdout.strip()
    try:
        data = json.loads(raw)
        response_text = data.get("result", "")
        usage = {
            "input_tokens": data.get("usage", {}).get("input_tokens", 0),
            "output_tokens": data.get("usage", {}).get("output_tokens", 0),
            "cost_usd": data.get("total_cost_usd", 0),
        }
        return response_text, usage
    except (json.JSONDecodeError, KeyError):
        return raw, {}


def _parse_json_response(text: str) -> list | dict:
    """Parse JSON from Claude's response, handling possible markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    return json.loads(cleaned)
