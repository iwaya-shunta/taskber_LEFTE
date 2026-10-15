import sys
import random
import ctypes
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QScrollArea, QLabel, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QPixmap, QColor

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"


class RECT(ctypes.Structure):
    _fields_ = [
        ('left', ctypes.c_long),
        ('top', ctypes.c_long),
        ('right', ctypes.c_long),
        ('bottom', ctypes.c_long)
    ]


def get_taskbar_rect():
    """Windowsタスクバーの正確な位置とサイズを取得"""
    hwnd = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
    rect = RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect


class MessageBubble(QWidget):
    """LINE/Instagram風の個別メッセージ吹き出し"""
    def __init__(self, text: str, is_user: bool):
        super().__init__()
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(4, 2, 4, 2)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        if is_user:
            main_layout.addStretch()
            main_layout.addWidget(label)
            label.setStyleSheet("""
                QLabel {
                    background-color: #007AFF;
                    color: #FFFFFF;
                    border-radius: 14px;
                    border-bottom-right-radius: 4px;
                    padding: 8px 12px;
                    font-size: 13px;
                    max-width: 220px;
                }
            """)
        else:
            main_layout.addWidget(label)
            main_layout.addStretch()
            label.setStyleSheet("""
                QLabel {
                    background-color: #2C2C2E;
                    color: #F2F2F7;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 14px;
                    border-bottom-left-radius: 4px;
                    padding: 8px 12px;
                    font-size: 13px;
                    max-width: 220px;
                }
            """)


class ChatBubble(QWidget):
    """左下からポップアップするチャットウィンドウ"""
    message_sent = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(340, 420)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)

        self.container = QWidget(self)
        self.container.setObjectName("MainContainer")
        self.container.setStyleSheet("""
            QWidget#MainContainer {
                background-color: rgba(22, 24, 30, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 16px;
            }
        """)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(12, 12, 12, 12)
        container_layout.setSpacing(8)

        # ヘッダー
        header = QLabel("AI相棒", self.container)
        header.setStyleSheet("color: #8E8E93; font-size: 12px; font-weight: bold;")
        container_layout.addWidget(header)

        # チャットスクロールエリア
        self.scroll_area = QScrollArea(self.container)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { background: transparent; width: 4px; margin: 0; }
            QScrollBar::handle:vertical { background: rgba(255, 255, 255, 0.25); border-radius: 2px; }
        """)

        self.chat_content = QWidget()
        self.chat_content.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.setSpacing(6)
        self.chat_layout.addStretch()

        self.scroll_area.setWidget(self.chat_content)
        container_layout.addWidget(self.scroll_area)

        # 入力欄
        self.input_field = QLineEdit(self.container)
        self.input_field.setPlaceholderText("メッセージを入力...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
                border: 1px solid transparent;
                border-radius: 16px;
                padding: 8px 14px;
                font-size: 13px;
            }
            QLineEdit:focus {
                background-color: rgba(255, 255, 255, 0.14);
                border: 1px solid #007AFF;
            }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        container_layout.addWidget(self.input_field)

        outer_layout.addWidget(self.container)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(2, 6)
        self.container.setGraphicsEffect(shadow)

    def send_message(self):
        text = self.input_field.text().strip()
        if text:
            self.add_bubble(text, is_user=True)
            self.input_field.clear()
            self.message_sent.emit(text)

    def append_response(self, text: str):
        self.add_bubble(text, is_user=False)

    def add_bubble(self, text: str, is_user: bool):
        bubble = MessageBubble(text, is_user=is_user)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        QTimer.singleShot(20, self.scroll_to_bottom)

    def scroll_to_bottom(self):
        bar = self.scroll_area.verticalScrollBar()
        bar.setValue(bar.maximum())


class VeadotubeMascot(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # --- タスクバー枠内に収まるサイズ設定 ---
        self.char_size = 80       # タスクバー内のアイコンと同等のサイズ
        self.bounce_margin = 12     # 小さめの跳ね用余白
        self.resize(self.char_size, self.char_size + self.bounce_margin)

        # スプライト読み込み
        self.sprites = {
            "idle_open": self.load_sprite("idle_open.png"),
            "idle_closed": self.load_sprite("idle_closed.png"),
            "talk_open": self.load_sprite("talk_open.png"),
            "talk_closed": self.load_sprite("talk_closed.png"),
        }

        self.is_speaking = False
        self.mouth_open = False
        self.eye_open = True
        self.bounce_y = 0.0

        # タスクバー左端に配置
        self.init_position()

        # チャット吹き出し
        self.bubble = ChatBubble()
        self.bubble.message_sent.connect(self.on_user_message)
        self.update_bubble_position()

        # タイマー群
        self.draw_timer = QTimer(self)
        self.draw_timer.timeout.connect(self.update_animation)
        self.draw_timer.start(16)

        self.mouth_timer = QTimer(self)
        self.mouth_timer.timeout.connect(self.toggle_mouth)
        self.mouth_timer.start(110)

        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.start_blink)
        self.schedule_next_blink()

        self.bounce_timer = QTimer(self)
        self.bounce_timer.setSingleShot(True)
        self.bounce_timer.timeout.connect(self.handle_random_bounce)

    def load_sprite(self, filename: str) -> QPixmap:
        path = ASSETS_DIR / filename
        pixmap = QPixmap(str(path))
        return pixmap.scaled(
            self.char_size, self.char_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

    def schedule_next_blink(self):
        self.blink_timer.start(random.randint(4000, 9000))

    def start_blink(self):
        self.eye_open = False
        self.update()
        QTimer.singleShot(120, self.end_blink)

    def end_blink(self):
        self.eye_open = True
        self.update()
        self.schedule_next_blink()

    def toggle_mouth(self):
        if self.is_speaking:
            self.mouth_open = not self.mouth_open
        else:
            self.mouth_open = False
        self.update()

    def schedule_next_bounce(self):
        if self.is_speaking:
            self.bounce_timer.start(random.randint(800, 2200))

    def handle_random_bounce(self):
        if self.is_speaking:
            # アイコンが小さいので跳ね幅も控えめ (-2.0px 〜 -3.5px)
            self.bounce_y = random.uniform(-3.5, -2.0)
            self.update()
            self.schedule_next_bounce()

    def update_animation(self):
        if abs(self.bounce_y) > 0.1:
            self.bounce_y *= 0.75
        else:
            self.bounce_y = 0.0
        self.update()

    def init_position(self):
        """タスクバー右側のトレイ領域（赤マークの位置）に埋め込む"""
        screen = QApplication.primaryScreen()
        full_rect = screen.geometry()          # 画面全体の領域
        work_rect = screen.availableGeometry()  # タスクバーを除いた領域

        # タスクバーの高さ（通常40〜48px程度）
        taskbar_height = full_rect.bottom() - work_rect.bottom()
        if taskbar_height <= 0:
            taskbar_height = 48

        # --- X座標の調整 ---
        # 画面右端から時計・クイック設定・IMEを避けた「^」の右横付近
        # ※ もし少しズレている場合は「215」の数値を増減（±20px程度）して微調整できます
        x = full_rect.right() - 350

        # --- Y座標の調整 ---
        # タスクバーの上下中央にキャラクターが来るように配置
        y = work_rect.bottom() + (taskbar_height - self.char_size) // 2 - self.bounce_margin
        
        self.move(x, y)
        print(f"[Debug] トレイ配置座標: X={x}, Y={y}")

    def update_bubble_position(self):
        """チャット画面を画面右端側にしっかり寄せて配置"""
        screen = QApplication.primaryScreen()
        work_rect = screen.availableGeometry()

        # 画面右端から 16px の余白を空けてピタッと配置
        bubble_x = work_rect.right() - self.bubble.width() - 16

        # タスクバーの上端から 10px 浮かせた位置
        bubble_y = work_rect.bottom() - self.bubble.height() - 10

        self.bubble.move(bubble_x, bubble_y)
        print(f"[Debug] チャット画面配置: X={bubble_x}, Y={bubble_y}")

    def on_user_message(self, text: str):
        # ユーザー送信時は待機し、1.2秒後に返答テスト
        QTimer.singleShot(1200, self.simulate_ai_response)

    def simulate_ai_response(self):
        self.bubble.append_response("メッセージ受け取ったよ！")
        self.start_speaking()
        QTimer.singleShot(2200, self.stop_speaking)

    def start_speaking(self):
        self.is_speaking = True
        self.bounce_y = -2.5
        self.schedule_next_bounce()
        self.update()

    def stop_speaking(self):
        self.is_speaking = False
        self.bounce_timer.stop()
        self.bounce_y = 0.0
        self.mouth_open = False
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        is_mouth_open = self.is_speaking and self.mouth_open
        if is_mouth_open:
            key = "talk_open" if self.eye_open else "talk_closed"
        else:
            key = "idle_open" if self.eye_open else "idle_closed"

        pixmap = self.sprites[key]
        draw_y = self.bounce_margin + self.bounce_y
        painter.drawPixmap(0, int(draw_y), pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.bubble.isVisible():
                self.bubble.hide()
            else:
                self.update_bubble_position()
                self.bubble.show()
                self.bubble.input_field.setFocus()
        elif event.button() == Qt.MouseButton.RightButton:
            print("アプリを終了します。")
            self.bubble.close()
            QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mascot = VeadotubeMascot()
    mascot.show()
    sys.exit(app.exec())