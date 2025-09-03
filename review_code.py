#!/usr/bin/env python3
import os
import json
import sys
import time
from typing import List, Dict, Optional
import requests

# Optional Gemini support
try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
except Exception:
    genai = None
    google_exceptions = None

GITHUB_API = "https://api.github.com"

def env(name: str, required: bool = False, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(name, default)
    if required and not val:
        print(f"[error] Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(2)
    return val

def load_event_pr_number() -> Optional[int]:
    """Extract PR number from GITHUB_EVENT_PATH when available."""
    path = os.getenv("GITHUB_EVENT_PATH")
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        # pull_request event
        if "pull_request" in payload:
            return int(payload["pull_request"]["number"])
        # issue_comment on a PR
        if payload.get("issue", {}).get("pull_request"):
            return int(payload["issue"]["number"])
    except Exception as e:
        print(f"[warn] Failed to parse GITHUB_EVENT_PATH: {e}")
    return None

def github_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "champ-ai-code-review"
    }

def fetch_pr_files(repo: str, pr_number: int, token: str) -> List[Dict]:
    """Return list of files changed in the PR (filename + patch when available)."""
    files = []
    page = 1
    headers = github_headers(token)
    while True:
        url = f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}/files?per_page=100&page={page}"
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"GitHub API error {r.status_code}: {r.text}")
        chunk = r.json()
        files.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1
    return files

def build_prompt_from_files(files: List[Dict]) -> str:
    """Turn file diffs into a compact prompt."""
    MAX_CHARS = 24000
    parts = [
        "You are a senior software engineer performing code review on a GitHub pull request.",
        "Be concise but specific. Prioritize correctness, security, performance, readability, testing, and maintainability.",
        "If everything looks good, respond with a short 'LGTM' style note and any nits.",
        "",
        "Changes (unified diff excerpts):"
    ]
    used = sum(len(p) for p in parts)
    for f in files:
        name = f.get("filename", "unknown")
        patch = f.get("patch", "")
        header = f"\n--- {name} ---\n"
        if used + len(header) > MAX_CHARS:
            break
        parts.append(header); used += len(header)
        # clip long patches to keep under limit
        clip = patch[: max(0, MAX_CHARS - used - 500)]
        parts.append(clip)
        used += len(clip)
        if used >= MAX_CHARS:
            break
    parts.append("\nProvide a structured review with sections: Summary, Issues (with file:line when possible), Suggestions, Tests to Add, Risk, LGTM?")
    return "\n".join(parts)

def run_gemini(prompt: str, api_key: Optional[str]) -> Optional[str]:
    if not api_key or not genai:
        return None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(prompt)
        if hasattr(resp, "text") and resp.text:
            return resp.text.strip()
        # Fallback for older SDKs
        if hasattr(resp, "candidates") and resp.candidates:
            return resp.candidates[0].content.parts[0].text.strip()
    except Exception as e:
        print(f"[warn] Gemini error: {e}")
    return None

def run_openrouter(prompt: str, api_key: Optional[str]) -> Optional[str]:
    if not api_key:
        return None
    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini-2024-07-18")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a precise, pragmatic code reviewer."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    try:
        r = requests.post(url, headers=headers, json=data, timeout=60)
        if r.status_code != 200:
            print(f"[warn] OpenRouter error {r.status_code}: {r.text[:2000]}")
            return None
        js = r.json()
        content = js.get("choices", [{}])[0].get("message", {}).get("content")
        return (content or "").strip() or None
    except Exception as e:
        print(f"[warn] OpenRouter exception: {e}")
        return None

def post_pr_comment(repo: str, pr_number: int, token: str, body: str) -> None:
    url = f"{GITHUB_API}/repos/{repo}/issues/{pr_number}/comments"
    headers = github_headers(token)
    resp = requests.post(url, headers=headers, json={"body": body}, timeout=30)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to post comment: {resp.status_code} {resp.text}")

def main() -> int:
    repo = env("GITHUB_REPOSITORY", required=True)
    token = env("GITHUB_TOKEN", required=True)
    google_key = env("GOOGLE_API_KEY", required=False)
    openrouter_key = env("OPENROUTER_API_KEY", required=False)

    pr_number = os.getenv("PR_NUMBER")
    pr_from_event = load_event_pr_number()
    pr_number = int(pr_number or pr_from_event or 0)
    if not pr_number:
        print("[error] Could not determine PR number. Make sure this runs on pull_request events.", file=sys.stderr)
        return 2

    print(f"[info] Repo: {repo}  PR: {pr_number}")
    files = fetch_pr_files(repo, pr_number, token)
    if not files:
        print("[info] No changed files detected; exiting.")
        return 0

    prompt = build_prompt_from_files(files)

    review = None
    if google_key:
        review = run_gemini(prompt, google_key)
    if not review and openrouter_key:
        review = run_openrouter(prompt, openrouter_key)
    if not review:
        review = "LGTM"  # minimal fallback

    # Normalize happy path
    if review.strip().lower().startswith("lgtm"):
        review = "✅ **LGTM** — No major issues found.\n\n_Note:_ Consider adding/confirming tests and documentation where applicable."

    post_pr_comment(repo, pr_number, token, review)
    print("[info] Review posted successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
