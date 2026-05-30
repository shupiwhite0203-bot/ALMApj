# Monster Hunter LLM Advisor

This file describes the older standalone advisor flow. For the current Live2D-integrated assistant, prefer `mh_hunt_agent.py` or `mh_run_assistant.py`.

## Standalone Flow

1. `screenshot.py` saves screenshots.
2. `predict.py` estimates the label with a trained EfficientNet checkpoint.
3. `mh_llm_advisor.py` sends the screenshot and prediction to the OpenAI Responses API.
4. The LLM returns Japanese hunting advice.

## Dry Run

```powershell
.\.venv\Scripts\python.exe mh_llm_advisor.py --domain animal --image data\pred\neko.png --dry-run
```

## Live2D-Integrated Dry Run

```powershell
.\.venv\Scripts\python.exe mh_hunt_agent.py --checkpoint runs\animals\best.pt --image data\pred\neko.png --dry-run
```

## Watch Mode

```powershell
.\.venv\Scripts\python.exe mh_hunt_agent.py --watch --dry-run --checkpoint runs\monsters\best.pt
```

Add `--voicevox` after starting VOICEVOX Engine.
