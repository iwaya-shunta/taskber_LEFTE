from pathlib import Path

# パス設定
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"

# マスコット設定
CHAR_SIZE = 65           # アイコン表示サイズ
BOUNCE_MARGIN = 10       # バウンド用の上部余白
MOUTH_INTERVAL_MS = 110  # 口パクの切り替え速度 (ms)
BLINK_MIN_MS = 4000      # まばたき最小間隔 (ms)
BLINK_MAX_MS = 9000      # まばたき最大間隔 (ms)

# VOICEVOX 設定
VOICEVOX_HOST = "http://127.0.0.1:50021"
SPEAKER_ID = 3           # デフォルトのスピーカーID (3: ずんだもん ノーマル等)