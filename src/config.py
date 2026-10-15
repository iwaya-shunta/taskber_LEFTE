import os
from pathlib import Path
from dotenv import load_dotenv

# .env ファイルの読み込み
load_dotenv()

# パス設定
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
VOICEVOX_EXE_PATH = r"C:\Program Files\VOICEVOX\VOICEVOX.exe"

TEMP_VOICE_PATH = CACHE_DIR / "temp_voice.wav"

# マスコット設定
CHAR_SIZE = 65           # アイコン表示サイズ
BOUNCE_MARGIN = 10       # バウンド用の上部余白
TRAY_OFFSET_X = 230      # 画面右端からの距離（100〜120あたり）
MOUTH_INTERVAL_MS = 110  # 口パクの切り替え速度 (ms)
BLINK_MIN_MS = 4000      # まばたき最小間隔 (ms)
BLINK_MAX_MS = 9000      # まばたき最大間隔 (ms)

# VOICEVOX 設定
VOICEVOX_HOST = "http://127.0.0.1:50021"
SPEAKER_ID = 8           # デフォルトのスピーカーID (3: ずんだもん ノーマル等)

# 声の元気さ・ノリを出すパラメータ調整
VOICE_SPEED_SCALE = 1.15       # 話速: 少しキビキビと早口にする（1.1〜1.2推奨）
VOICE_PITCH_SCALE = 0.05       # 音高: ほんの少しだけ高くして明るさを出す
VOICE_INTONATION_SCALE = 1.25  # 抑揚: 感情の起伏をハッキリ大きくする（1.2〜1.3推奨）
VOICE_VOLUME_SCALE = 1.0

# 音声パラメータ微調整
VOICE_SPEED_SCALE = 1.05   # 話速 (1.0が標準。少しキビキビ喋らせるなら 1.05〜1.1)
VOICE_PITCH_SCALE = 0.0    # 音高 (-0.15 〜 0.15)
VOICE_INTONATION_SCALE = 1.0 # 抑揚 (1.0が標準)
VOICE_VOLUME_SCALE = 1.0   # 音量

# --- バックエンドサーバー（LEFTE）設定 ---
SERVER_HOST = "http://localhost:8000" # サーバーのアドレス（Raspberry Pi等のIPにする場合はここを変更）
CHAT_ENDPOINT = f"{SERVER_HOST}/chat"