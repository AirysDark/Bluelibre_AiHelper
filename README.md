# AI Autobuilder

Self-healing builder that catches failures, asks an LLM for a minimal patch, applies it, and retries.

## Quickstart (Local)

```bash
export BUILD_CMD="pio run"     # or make, gradle, etc.
export PROVIDER=llama          # or openai
./tools/ai_autobuilder.py
```

To use OpenAI:
```bash
export PROVIDER=openai
export OPENAI_API_KEY=sk-...yourkey...
export OPENAI_MODEL=gpt-4.1-mini
./tools/ai_autobuilder.py
```

## GitHub Actions

The included workflow `.github/workflows/ai-autobuilder.yml` will attempt a fix when CI fails, and push a branch `fix/ai-autobuilder-<run_id>`.

## Safety

- Stores `.pre_ai_fix.patch` for reverting: `git apply -R .pre_ai_fix.patch`
