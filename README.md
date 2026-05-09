# EfficientNet-B0 Image Classifier

EfficientNet-B0 を使った画像分類プロジェクトです。最初は `bird` / `lion` / `dog` のような現実世界画像で動作確認し、そのままモンハンワイルズのスクリーンショット分類にも使えます。

## 1. インストール

```powershell
pip install -r requirements.txt
```

GPU 版 PyTorch が必要な場合は、環境に合うコマンドを PyTorch 公式サイトで確認してインストールしてください。

## 2. データ配置

フォルダ名がそのままラベル名になります。

```text
data/
  animals/
    bird/
      img001.jpg
      img002.jpg
    lion/
      img001.jpg
    dog/
      img001.jpg

  monsters/
    Rathalos/
      screenshot001.png
    Chatacabra/
      screenshot001.png
    Rey_Dau/
      screenshot001.png
```

`train` / `val` を手動で分けたい場合は、次の形も使えます。

```text
data/
  monsters/
    train/
      Rathalos/
      Chatacabra/
    val/
      Rathalos/
      Chatacabra/
```

## 3. 学習

鳥・ライオン・犬のテスト:

```powershell
python train.py --data-dir data/animals --output-dir runs/animals --epochs 10 --pretrained --freeze-backbone
```

モンスター分類:

```powershell
python train.py --data-dir data/monsters --output-dir runs/monsters --epochs 20 --pretrained
```

少ない枚数から始める場合は `--freeze-backbone` を付けると過学習しにくく、学習も軽くなります。データが増えたら外して微調整してください。

## 4. 識別

1 枚の画像:

```powershell
python predict.py --checkpoint runs/animals/best.pt --image path/to/image.jpg
```

フォルダ内の画像をまとめて識別:

```powershell
python predict.py --checkpoint runs/monsters/best.pt --image path/to/screenshots --top-k 3
```

## 5. スクリーンショット分類のコツ

- モンスターが画面中央に大きく写っている画像だけでなく、距離・角度・明るさ・背景が違う画像も混ぜます。
- UI やクエスト名だけで当たってしまう偏りを避けるため、同じ場面からの連続画像に偏らせすぎないようにします。
- クラスごとの枚数差が大きいと弱いクラスが出やすいので、まずは各クラス同程度の枚数を目安にします。
- ゲーム画像の利用範囲は、手元での学習・検証など権利面に配慮して扱ってください。
