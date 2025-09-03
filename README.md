# Champ AI Code Review (Fixed)

A robust GitHub Action that posts an AI-powered review on Pull Requests using **Gemini** (if a Google API key is provided) and falls back to **OpenRouter** (if provided).

## Why this version?
- Properly discovers **PR number** from `GITHUB_EVENT_PATH`
- Clean, reliable **GitHub API** calls with pagination
- Solid prompt-building with diff excerpts
- Resilient: tries **Gemini** first, then **OpenRouter**, then minimal fallback
- Clear errors and logs

## Inputs
- `github_token` (**required**): use `${{ github.token }}`
- `google_api_key` (optional)
- `openrouter_api_key` (optional)
- `openrouter_model` (optional): defaults to `openai/gpt-4o-mini-2024-07-18`

## Setup
Create repository secrets as needed:
- `GOOGLE_API_KEY`
- `OPENROUTER_API_KEY`

Add a workflow like: `.github/workflows/ai_review.yml`

```yaml
name: Champ AI Code Review
on:
  pull_request:
    types: [opened, synchronize, reopened]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: your-org/ai-code-review-action@v1
        with:
          github_token: ${{ github.token }}
          google_api_key: ${{ secrets.GOOGLE_API_KEY }}
          openrouter_api_key: ${{ secrets.OPENROUTER_API_KEY }}
```

## Local Testing
- Build: `docker build -t ai-review .`
- Run (you must provide envs and mount a `GITHUB_EVENT_PATH` JSON file simulating a PR event):
  ```bash
  docker run --rm -e GITHUB_REPOSITORY=owner/repo \
                 -e GITHUB_TOKEN=ghp_xxx \
                 -e GOOGLE_API_KEY=... \
                 -e GITHUB_EVENT_PATH=/event.json \
                 -v $PWD/sample_event.json:/event.json \
                 ai-review
  ```

## Notes
- The action posts a single summary comment. If you want per-file comments, we can extend it to use the Reviews API and diff anchors.
- If neither API key is provided, you'll get a minimal **LGTM** placeholder.
