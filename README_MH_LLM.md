# 単独CLIでの分類・LLM連携

システム全体、セットアップ、データ準備・学習手順は [README.md](README.md) を参照してください。
学習済みモデルと画像は公開対象外なので、新規クローンでは先に準備します。

## 動物によるAPIなしの確認

```powershell
.\.venv\Scripts\python.exe mh_llm_advisor.py --domain animal --image "C:\path\to\animal.jpg" --dry-run
```

動物分類は検証用です。`runs/animals/best.pt` で分類し、結果と送信予定プロンプトを表示します。
API通信やLLMによる生成は行いません。

## モンスター画像の監視

```powershell
.\.venv\Scripts\python.exe mh_llm_advisor.py --watch --dry-run
```

別ターミナルで `screenshot.py` を起動します。監視は起動時の既存画像をスキップし、新規画像を処理します。
既存画像も処理する場合は `--process-existing` を付けます。

APIによる文章生成には `OPENAI_API_KEY` を設定して `--dry-run` を外します。
成功時のログは `runs/llm_advice/` に保存されます。

音声やLive2Dを含める場合は [拡張アシスタントの説明](mh_assistant/README.md) を参照してください。
