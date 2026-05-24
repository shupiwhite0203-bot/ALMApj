# Monster Hunter Multimodal LLM Advisor

This project flow is:

1. `screenshot.py` saves training screenshots to `MonsterHunter_Screenshots/cnn_train` and LLM situation screenshots to `MonsterHunter_Screenshots/situation`.
2. `predict.py` or `mh_llm_advisor.py` uses the trained EfficientNet checkpoint to estimate the monster name.
3. `mh_llm_advisor.py` sends the estimated monster name and screenshot to the OpenAI Responses API.
4. The LLM returns Japanese hunting advice, including likely weaknesses, useful status effects, target parts, and situational tips.

## Setup

```powershell
pip install -r requirements.txt
```

The API key can be added later. When you are ready:

```powershell
$env:OPENAI_API_KEY="sk-..."
```

You can also override the model:

```powershell
$env:OPENAI_MODEL="gpt-5.4-mini"
```

## 1. Capture Screenshots

```powershell
python screenshot.py
```

By default this saves:

- `MonsterHunter_Screenshots/cnn_train`: frequent screenshots for classifier datasets
- `MonsterHunter_Screenshots/situation`: slower screenshots for LLM analysis

## 2. Train The Monster Classifier

Put images into class folders such as:

```text
data/monsters/
  Rathalos/
  Chatacabra/
  Rey_Dau/
```

Then train:

```powershell
python train.py --data-dir data/monsters --output-dir runs/monsters --epochs 20 --pretrained
```

## 3. Test Without API Billing

This only runs local monster prediction and prints the prompt that would be sent to the LLM:

```powershell
python mh_llm_advisor.py --dry-run
```

For a specific image:

```powershell
python mh_llm_advisor.py --image MonsterHunter_Screenshots/situation/example.png --dry-run
```

## 4. Run With The OpenAI API

After setting `OPENAI_API_KEY`:

```powershell
python mh_llm_advisor.py
```

The script uses `gpt-5.4-mini` by default and the Responses API image input format. If your account exposes a different model name, set `OPENAI_MODEL` or pass `--model`.

## 5. Pseudo-Realtime Advice

Run the screenshot capture script:

```powershell
python screenshot.py
```

In another terminal, watch for new situation screenshots:

```powershell
python mh_llm_advisor.py --watch
```

For API-free testing:

```powershell
python mh_llm_advisor.py --watch --dry-run
```

`--watch` ignores screenshots that already exist when it starts, then processes only newly added images. Use this if you intentionally want to process existing screenshots too:

```powershell
python mh_llm_advisor.py --watch --process-existing
```

Advice logs are saved to `runs/llm_advice` when the API call succeeds.
