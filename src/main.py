import sys
import random
from pathlib import Path

# --- PySide6 のインポート ---
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QPixmap

# --- パス設定 ---
# このスクリプト (src/main.py) から見て親フォルダ (taskber_LEFTE) の assets を指す
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"


class VeadotubeMascot(QWidget):
    def __init__(self):
        super().__init__()

        # --- ウィンドウ設定 ---
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |     # タイトルバーや枠線を消す
            Qt.WindowType.WindowStaysOnTopHint |    # 常に最前面
            Qt.WindowType.Tool                      # タスクバーのアプリアイコン一覧に非表示
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) # 背景透過

        # 表示サイズの設定
        self.char_size = 120       # キャラクター自体の表示サイズ（ピクセル）
        self.bounce_margin = 15  # キャラクターが上に跳ねたときに見切れないための上部余白
        
        # ウィンドウ全体のサイズ（高さは余白分を足す）
        self.resize(self.char_size, self.char_size + self.bounce_margin)

        # --- 4種類のPNGスプライト読み込み ---
        self.sprites = {
            "idle_open": self.load_sprite("idle_open.png"),
            "idle_closed": self.load_sprite("idle_closed.png"),
            "talk_open": self.load_sprite("talk_open.png"),
            "talk_closed": self.load_sprite("talk_closed.png"),
        }

        # --- アニメーション状態 ---
        self.is_speaking = False   # 発話中フラグ (True / False)
        self.mouth_open = False    # 口が開いているか
        self.eye_open = True       # 目が開いているか
        self.bounce_y = 0.0        # 跳ねている高さオフセット

        # タスクバー真上への位置合わせ
        self.init_position()

        # --- タイマー群 ---
        # 1. 描画ループ (約60FPS)
        self.draw_timer = QTimer(self)
        self.draw_timer.timeout.connect(self.update_animation)
        self.draw_timer.start(16)

        # 2. 口パクタイマー (発話中は 130ms ごとに開閉)
        self.mouth_timer = QTimer(self)
        self.mouth_timer.timeout.connect(self.toggle_mouth)
        self.mouth_timer.start(110)

        # 3. まばたきタイマー
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.start_blink)
        self.schedule_next_blink()

        # バウンド専用タイマー: 口パクとは別に、たまにピョコッと跳ねるようにする
        self.bounce_timer = QTimer(self)
        self.bounce_timer.setSingleShot(True)  # 1回ごとに間隔を変えて呼ぶ設定
        self.bounce_timer.timeout.connect(self.handle_random_bounce)

    def load_sprite(self, filename: str) -> QPixmap:
        """500x500のPNGを高画質のまま指定サイズに滑らか縮小して読み込む"""
        path = ASSETS_DIR / filename
        pixmap = QPixmap(str(path))
        
        # SmoothTransformation を指定してジャギー（ギザギザ）を出さずに縮小
        return pixmap.scaled(
            self.char_size, self.char_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

    def schedule_next_blink(self):
        """2.5秒〜5.5秒のランダムな時間で次のまばたきを予約"""
        self.blink_timer.start(random.randint(2500, 7000))
    
    def schedule_next_bounce(self):
        """次の跳ねるタイミングをランダムに予約 (0.8秒〜2.2秒の間)"""
        if self.is_speaking:
            interval = random.randint(800, 2200)
            self.bounce_timer.start(interval)

    def handle_random_bounce(self):
        """発話中ならランダムな高さでピョコッと跳ねて次を予約"""
        if self.is_speaking:
            # 跳ねる高さも少し揺らぎを持たせる（-3.0px 〜 -6.0px）
            self.bounce_y = random.uniform(-6.0, -3.0)
            self.update()
            self.schedule_next_bounce()

    def start_blink(self):
        """目を閉じる"""
        self.eye_open = False
        self.update()
        # 140ミリ秒だけ目を閉じてから開ける
        QTimer.singleShot(120, self.end_blink)

    def end_blink(self):
        """目を開けて次のまばたきを待機"""
        self.eye_open = True
        self.update()
        self.schedule_next_blink()

    def toggle_mouth(self):
        """発話時の口開閉とバウンド"""
        if self.is_speaking:
            self.mouth_open = not self.mouth_open
        else:
            self.mouth_open = False
        self.update()

    def trigger_bounce(self):
        """発話中、たまに小さく跳ねる（控えめなぽよぽよ）"""
        if self.is_speaking:
            # 控えめに -4px だけ跳ねる
            self.bounce_y = -4.0
            self.update()

    def update_animation(self):
        """跳ねた位置から元の接地位置へ減衰復帰"""
        if abs(self.bounce_y) > 0.1:
            self.bounce_y *= 0.78  # 0.78を掛けて素早く元の位置に戻す
        else:
            self.bounce_y = 0.0
        self.update()

    def init_position(self):
        """タスクバーの真上に接地するように配置"""
        screen = QApplication.primaryScreen()
        work_area = screen.availableGeometry()

        # 画面右下付近（タスクバーの上端）
        x = work_area.right() - self.width() - 40
        y = work_area.bottom() - self.height()
        self.move(x, y)

    def paintEvent(self, event):
        """現在の口と目の状態に合わせてスプライトを正確に選択"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 口が開いているかどうかの判定（発話中 かつ 口開きフラグがTrue）
        is_mouth_open = self.is_speaking and self.mouth_open

        # 4つの状態を綺麗にマッピング
        if is_mouth_open:
            key = "talk_open" if self.eye_open else "talk_closed"
        else:
            key = "idle_open" if self.eye_open else "idle_closed"

        pixmap = self.sprites[key]

        # bounce_margin（上部余白）+ bounce_y（跳ね量）の位置に描画
        draw_y = self.bounce_margin + self.bounce_y
        painter.drawPixmap(0, int(draw_y), pixmap)

    def mousePressEvent(self, event):
        """左クリックで発話トグル、右クリックで終了"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_speaking = not self.is_speaking
            if self.is_speaking:
                # 喋り始めた瞬間に最初の跳ねを予約（喋り出しでピョコッと跳ねる）
                self.bounce_y = -4.5
                self.schedule_next_bounce()
            else:
                self.bounce_timer.stop()
                self.bounce_y = 0.0

            status = "発話中（おしゃべり）" if self.is_speaking else "待機中（おとなしい）"
            print(f"[状態切り替え]: {status}")
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            print("アプリを終了します。")
            QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mascot = VeadotubeMascot()
    mascot.show()
    sys.exit(app.exec())