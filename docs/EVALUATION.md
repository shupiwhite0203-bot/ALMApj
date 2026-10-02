# 動作デモと評価記録

## デモの範囲

[demo.gif](demo.gif) は次のコマンドの実際の出力をGIFとして再生したものです。分類器を実行し、LLMへ送るプロンプトまで確認しています。LLM生成結果やゲーム画面の録画ではありません。APIは呼び出していません。

```powershell
.\.venv\Scripts\python.exe mh_llm_advisor.py --domain animal --image data\pred\lion1.jpg --device cpu --dry-run
```

この画像ではライオン0.4789、犬0.2484、猫0.1855でした。分類スコアは正答確率ではありません。デモ元画像・学習済みモデルは配布していないので、再実行には自分の画像と学習済みモデルを用意します。

## 実測結果

2026-10-02に手元の全データで測定しました。**学習に使用した画像が含まれる診断用の結果であり、独立テストセットでの精度ではありません。**

| 対象 | 枚数 | Accuracy | Macro F1 | 画像読み込み～分類 p50 / p95 |
| --- | ---: | ---: | ---: | ---: |
| 動物4クラス | 200 | 90.5% | 0.9044 | 40.6 / 46.6 ms |
| モンスター5クラス | 1,137 | 100.0% | 1.0000 | 73.2 / 80.3 ms |

モンスター100%という値を、未知の狩猟画面での認識性能とは解釈できません。学習データとの重複や連続スクリーンショット間の類似性が影響している可能性があります。次の評価では撮影セッション・狩猟単位で学習とテストを分ける必要があります。

環境：Windows AMD64、Python 3.10.11、PyTorch 2.11.0+cpu、torchvision 0.26.0+cpu、CPU 2スレッド、バッチサイズ1。モデルを1回ウォームアップしてから測定しました。他プロセスの負荷は統制していません。

時間は画像読み込み・前処理・モデル推論を含みます。撮影、モデル読み込み、API通信、LLM生成、音声合成は含みません。30秒周期のシステム全体の遅延を表すものではありません。

クラス別Precision/Recall/F1、混同行列、推論のみの時間、モデルSHA-256、環境情報は [動物のJSON](evaluation/animals.json) と [モンスターのJSON](evaluation/monsters.json) に保存しています。

## 再測定

リポジトリルートから実行します。データはフォルダ名を正解ラベルとするImageFolder形式で、モデルと同じクラスを用意します。

```powershell
.\.venv\Scripts\python.exe evaluate.py --checkpoint runs/animals/best.pt --data-dir data/animals --output runs/evaluation/animals.json
.\.venv\Scripts\python.exe evaluate.py --checkpoint runs/monsters/best.pt --data-dir data/monsters --output runs/evaluation/monsters.json
```

独立テストデータを準備したら `--data-dir` をそのフォルダに変更します。スクリプトは学習データとの独立性を自動検証しません。公開用JSONに画像そのもの・画像の個別パス・APIキーは含めません。

## 未検証の項目

- 独立した狩猟セッションに対する分類精度と対象外画像の判定。
- ゲーム画面取得からLLM応答までの時間、API利用量、助言の正確性。
- 別PC・別frontendバージョンでのLive2D動作。

これらは、動物dry-runや学習データ上の高精度だけでは検証できません。
