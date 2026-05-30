# Monster Hunter Assistant MVP

This package is the integration layer for the Monster Hunter desktop assistant.

Current flow:

```text
situation screenshot
  -> EfficientNet prediction
  -> hunt session event
  -> first/continuous advice prompt
  -> OpenAI Responses API or dry-run advice
  -> optional VOICEVOX wav
  -> Open-LLM-VTuber Live2D renderer
```

## One-Command Local Run

Dry-run mode, without OpenAI or VOICEVOX:

```powershell
.\.venv\Scripts\python.exe mh_run_assistant.py --dry-run --checkpoint runs/animals/best.pt --process-existing
```

With screenshot capture:

```powershell
.\.venv\Scripts\python.exe mh_run_assistant.py --dry-run --screenshot --checkpoint runs/animals/best.pt
```

Open the Live2D UI:

```text
http://127.0.0.1:18080/
```

## Separate Processes

Live2D overlay server:

```powershell
.\.venv\Scripts\python.exe mh_live2d_server.py --port 18080
```

Screenshot capture:

```powershell
.\.venv\Scripts\python.exe screenshot.py
```

Assistant watch mode:

```powershell
.\.venv\Scripts\python.exe mh_hunt_agent.py --watch --dry-run --checkpoint runs/animals/best.pt
```

Advice throttling is enabled by default so the assistant does not repeat itself for every similar screenshot:

```powershell
.\.venv\Scripts\python.exe mh_run_assistant.py --dry-run --voicevox --desktop-pet --display 2 --checkpoint runs\animals\best.pt --advice-cooldown 30
```

- `--advice-cooldown`: minimum seconds between spoken advice.
- `--same-monster-cooldown`: optional extra cooldown when the same monster keeps being inferred. Default is `0`, because one hunt usually targets one monster.
- `--confidence-delta`: allows advice sooner if confidence changes significantly.
- `--min-confidence`: suppresses repeated low-confidence advice.

## Real Advice

Set `OPENAI_API_KEY`, then omit `--dry-run`.

```powershell
$env:OPENAI_API_KEY="..."
.\.venv\Scripts\python.exe mh_hunt_agent.py --watch --checkpoint runs/monsters/best.pt
```

## VOICEVOX

Start VOICEVOX Engine first, then add `--voicevox`.

```powershell
.\.venv\Scripts\python.exe mh_hunt_agent.py --watch --voicevox --checkpoint runs/monsters/best.pt
```

VOICEVOX speaker defaults to `47` for `ナースロボ＿タイプＴ / ノーマル`.

## Live2D

The renderer serves the normalized Nurse Robot Type T model from:

```text
runs/live2d_model/nurse_robot_type_t/
```

Source model folder:

```text
C:\Users\spieler\Desktop\実況\そざい\立ち絵いろいろ\ナースロボ_タイプT\ナースロボ＿タイプＴ公式立ち絵素材2.0\ナースロボ_Live2D_V50
```

Important: export this model for SDK 5.0 compatibility. The original SDK 5.3 export produced a `.moc3` format newer than the bundled renderer could load.

The current overlay consumes:

- `runs/live2d/latest_event.json`
- `/client-ws`
- `/live2d-model/nurse_robot_type_t/nurse_robot_type_t.model3.json`
- `/libs/live2dcubismcore.js`
