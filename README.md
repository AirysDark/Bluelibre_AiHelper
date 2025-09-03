# AI Autobuilder (OpenAI preset)

This repo includes a GitHub Action that will automatically try to fix failed builds using OpenAI.

## Setup

1. Copy `tools/ai_autobuilder.py` and `.github/workflows/ai-autobuilder.yml` into your repo.
2. In GitHub → Settings → Secrets and variables → Actions:
   - **Secret**: `OPENAI_API_KEY = sk-...yourkey...`
   - **Variable**: `BUILD_CMD = pio run` (or your build command)
   - (Optional) **Variable**: `OPENAI_MODEL = gpt-4.1-mini`

## Usage

- On a failing build, the bot runs `ai_autobuilder.py`.
- It proposes and applies a patch.
- If successful, the build passes.
- If not, a branch `fix/ai-autobuilder-<run_id>` is pushed.

## Local run

```bash
export OPENAI_API_KEY=sk-...yourkey...
export PROVIDER=openai
export BUILD_CMD="pio run"
python tools/ai_autobuilder.py
```
