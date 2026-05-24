import time
import os
from datetime import datetime
import pyautogui

BASE_DIR = "MonsterHunter_Screenshots"
CNN_DIR = os.path.join(BASE_DIR, "cnn_train")
SITUATION_DIR = os.path.join(BASE_DIR, "situation")

os.makedirs(CNN_DIR, exist_ok=True)
os.makedirs(SITUATION_DIR, exist_ok=True)

CNN_INTERVAL = 2
SITUATION_INTERVAL = 30

last_cnn = time.time()
last_situation = time.time()

print("スクリーンショット撮影を開始します。Ctrl + C で終了。")

try:
    while True:
        now = time.time()
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        if now - last_cnn >= CNN_INTERVAL:
            img = pyautogui.screenshot()
            path = os.path.join(CNN_DIR, f"{timestamp}.png")
            img.save(path)
            print(f"[CNN] 保存: {path}")
            last_cnn = now

        if now - last_situation >= SITUATION_INTERVAL:
            img = pyautogui.screenshot()
            path = os.path.join(SITUATION_DIR, f"{timestamp}.png")
            img.save(path)
            print(f"[Situation] 保存: {path}")
            last_situation = now

        time.sleep(0.1)

except KeyboardInterrupt:
    print("撮影を終了しました。")
