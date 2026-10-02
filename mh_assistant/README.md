# 拡張アシスタント

基本フローは [ルートREADME](../README.md) を参照してください。このパッケージは、画像分類・LLM連携に狩猟セッション管理、知識参照、音声・キャラクター表示を加える統合層です。

```text
状況画像 → EfficientNet-B0 → 狩猟セッション・プロンプト
        → LLMによる助言 → 任意の音声合成・Live2D表示
```

## CLIでの確認

学習済みモンスターモデルと画像を用意します。

```powershell
.\.venv\Scripts\python.exe mh_hunt_agent.py --checkpoint runs\monsters\best.pt --image "C:\path\to\screenshot.png" --dry-run
.\.venv\Scripts\python.exe mh_hunt_agent.py --watch --dry-run --checkpoint runs\monsters\best.pt
```

APIを使う場合は `OPENAI_API_KEY` を設定して `--dry-run` を外します。
動物専用のプロンプトで検証する場合は、統合CLIではなく `mh_llm_advisor.py --domain animal` を使います。

## 音声・表示の追加準備

以下は任意の拡張です。第三者製モデル・ランタイム・音声ファイルはリポジトリに同梱しません。

- VOICEVOX：Engineを別途起動し、`mh_voicevox_test.py --list` で利用可能な話者を確認します。`mh_hunt_agent.py` に `--voicevox` を追加すると音声合成を利用します。既定話者IDは47です。
- Live2D：利用条件を確認してモデルを取得し、SDK 5.0互換で書き出します。`mh_live2d_server.py --model-source "C:\path\to\Live2DModel" --port 18080` で指定します。
- Cubism Core：必要なランタイムを利用条件に従って準備し、`vendor/live2d/live2dcubismcore.min.js` に配置します。
- Electron：`desktop_companion/` で `npm install` を実行します。表示サーバーの起動後に `mh_desktop_companion.py` を起動します。

Live2D表示にはOpen-LLM-VTuberのfrontend成果物も必要です。保存場所を以下の環境変数で設定すると、一括起動の子プロセスにも引き継がれます。

```powershell
$env:ALMA_OPENLLM_FRONTEND = "C:\path\to\Open-LLM-VTuber\frontend"
$env:ALMA_LIVE2D_MODEL_SOURCE = "C:\path\to\Live2DModel"
.\.venv\Scripts\python.exe mh_run_assistant.py --screenshot --dry-run
```

表示サーバー単体では `--frontend-dir` と `--model-source` でも指定できます。frontendの既定値はホーム下の `Open-LLM-VTuber/frontend` です。アセットは `assets/main-*.js` と `assets/main-*.css` を各1件検出し、ビルドごとのハッシュ名をHTMLへ反映します。欠落・複数候補の場合は起動時に具体的なエラーを表示します。Open-LLM-VTuberの任意バージョンとの互換性を保証するものではありません。

準備済みの開発環境では、`mh_run_assistant.py --screenshot` で表示サーバー、監視、撮影をまとめて起動できます。`--dry-run`、`--voicevox`、`--desktop-pet` などを指定できます。通常の画像分類・LLM検証にはこの表示環境は不要です。

## 調整できる設定

`--advice-cooldown` は助言の最小間隔、`--min-confidence` は分類スコアの閾値、`--monster-lock-window` は同一モンスターを扱う時間窓です。統合CLIには連続フレームの取得や動的知識取得のオプションもあります。詳しくは各CLIの `--help` を参照してください。

画像・モデル、知識キャッシュ、イベントJSON、音声はローカルの生成物として管理します。分類の実測結果は [評価記録](../docs/EVALUATION.md) を参照してください。拡張表示の別PCでの実動作確認は今後の検証対象です。
