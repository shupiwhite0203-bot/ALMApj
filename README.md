# ALMA Monster Hunter Assistant

EfficientNet-B0 based image classifier plus a Live2D/VOICEVOX desktop assistant for Monster Hunter hunting support.

## Current Status

Working locally:

- screenshot capture
- EfficientNet-B0 training and prediction
- dry-run hunting advice
- Open-LLM-VTuber based Live2D display
- Live2D event delivery over local WebSocket
- optional VOICEVOX synthesis path

The current Live2D model source is:

```text
C:\Users\spieler\Desktop\実況\そざい\立ち絵いろいろ\ナースロボ_タイプT\ナースロボ＿タイプＴ公式立ち絵素材2.0\ナースロボ_Live2D_V50
```

Export the model for SDK 5.0 compatibility.

## Quick Dry Run

```powershell
.\.venv\Scripts\python.exe mh_hunt_agent.py --checkpoint runs\animals\best.pt --image data\pred\neko.png --dry-run
```

Live2D overlay:

```powershell
.\.venv\Scripts\python.exe mh_live2d_server.py --port 18080
```

Open:

```text
http://127.0.0.1:18080/
```

## Desktop Pet Mode

The browser overlay remains available, but the desktop companion uses a small Electron shell in `desktop_companion/`.
It loads the same local renderer and provides the Electron-only features: transparent window, always-on-top display, click-through, context menu, and Open-LLM-VTuber compatible `window.api`.

Electron is not bundled in this repo yet. Use one of these setups:

```powershell
# Option A: install with npm inside desktop_companion if npm is available
cd C:\Users\spieler\ALMApj\desktop_companion
npm install
```

```powershell
# Option B: place a downloaded Electron build here
C:\Users\spieler\ALMApj\vendor\electron\electron.exe
```

If you downloaded an Electron win32-x64 zip, unpack it with:

```powershell
.\.venv\Scripts\python.exe mh_install_electron_zip.py "C:\path\to\electron-vXX.X.X-win32-x64.zip" --force
```

If Open-LLM-VTuber Electron is already installed, create an ALMA shell from it:

```powershell
.\.venv\Scripts\python.exe mh_install_electron_from_openllm.py --force
```

```powershell
# Option C: point to electron.exe explicitly
$env:ALMA_ELECTRON_EXE = "C:\path\to\electron.exe"
```

Start only the desktop companion after `mh_live2d_server.py` is running:

```powershell
.\.venv\Scripts\python.exe mh_desktop_companion.py --url "http://127.0.0.1:18080/?mode=pet"
```

Use the second monitor:

```powershell
.\.venv\Scripts\python.exe mh_desktop_companion.py --url "http://127.0.0.1:18080/?mode=pet" --display 2
```

Or start it with the assistant launcher:

```powershell
.\.venv\Scripts\python.exe mh_run_assistant.py --dry-run --voicevox --desktop-pet --checkpoint runs\animals\best.pt
```

For the second monitor:

```powershell
.\.venv\Scripts\python.exe mh_run_assistant.py --dry-run --voicevox --desktop-pet --display 2 --checkpoint runs\animals\best.pt
```

## One-Command Local Run

Dry-run watch mode with screenshot capture:

```powershell
.\.venv\Scripts\python.exe mh_run_assistant.py --dry-run --screenshot --checkpoint runs\animals\best.pt
```

For trained monster mode:

```powershell
.\.venv\Scripts\python.exe mh_run_assistant.py --dry-run --screenshot --checkpoint runs\monsters\best.pt
```

## VOICEVOX

Start VOICEVOX Engine, then verify speaker `47`:

```powershell
.\.venv\Scripts\python.exe mh_voicevox_test.py --list
```

Generate a test wav:

```powershell
.\.venv\Scripts\python.exe mh_voicevox_test.py
```

Run the assistant with VOICEVOX:

```powershell
.\.venv\Scripts\python.exe mh_hunt_agent.py --checkpoint runs\animals\best.pt --image data\pred\neko.png --dry-run --voicevox
```

When the Live2D page is open, VOICEVOX wav audio is sent to the Open-LLM-VTuber renderer as a base64 wav payload. The renderer uses the model's `LipSync` group and `ParamMouthOpenY` for mouth movement.

## Target Monster Labels

The first classifier target is these five monsters:

- レ・ダウ
- リオレウス
- リオレイア
- アルシュベルド
- チャタカブラ

Create the starter folders:

```powershell
.\.venv\Scripts\python.exe mh_prepare_dataset.py
```

Check image counts:

```powershell
.\.venv\Scripts\python.exe mh_dataset_report.py
```

Dataset layout:

```text
data/monsters/
  レ・ダウ/
    image001.png
  リオレウス/
    image001.png
  リオレイア/
    image001.png
  アルシュベルド/
    image001.png
  チャタカブラ/
    image001.png
```

Train:

```powershell
.\.venv\Scripts\python.exe train.py --data-dir data\monsters --output-dir runs\monsters --epochs 20 --pretrained
```

Predict:

```powershell
.\.venv\Scripts\python.exe predict.py --checkpoint runs\monsters\best.pt --image MonsterHunter_Screenshots\situation --top-k 3
```

## Data Notes

- Keep the number of images roughly balanced between labels.
- Include different lighting, distance, camera angles, UI states, and monster poses.
- Avoid training mostly on UI text or quest overlays.
- For early tests, `--freeze-backbone` can reduce overfitting when the dataset is small.
- Once the dataset grows, train without `--freeze-backbone`.
