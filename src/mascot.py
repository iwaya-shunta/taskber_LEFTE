import random
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QPixmap

from src.config import (
    ASSETS_DIR, CHAR_SIZE, BOUNCE_MARGIN,
    MOUTH_INTERVAL_MS, BLINK_MIN_MS, BLINK_MAX_MS, TRAY_OFFSET_X
)

class MascotWidget(QWidget):
    """タスクバートレイに常駐するPNGTuberマスコット"""
    clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.char_size = CHAR_SIZE
        self.bounce_margin = BOUNCE_MARGIN
        self.resize(self.char_size, self.char_size + self.bounce_margin)

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

        self.init_position()

        # タイマー群
        self.draw_timer = QTimer(self)
        self.draw_timer.timeout.connect(self.update_animation)
        self.draw_timer.start(16)

        self.mouth_timer = QTimer(self)
        self.mouth_timer.timeout.connect(self.toggle_mouth)
        self.mouth_timer.start(MOUTH_INTERVAL_MS)

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
        self.blink_timer.start(random.randint(BLINK_MIN_MS, BLINK_MAX_MS))

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
            self.bounce_y = random.uniform(-3.5, -2.0)
            self.update()
            self.schedule_next_bounce()

    def update_animation(self):
        if abs(self.bounce_y) > 0.1:
            self.bounce_y *= 0.75
        else:
            self.bounce_y = 0.0
        self.update()

    # src/mascot.py 内の init_position を修正
    def init_position(self):
        screen = QApplication.primaryScreen()
        full_rect = screen.geometry()
        work_rect = screen.availableGeometry()

        x = full_rect.right() - TRAY_OFFSET_X
        y = full_rect.bottom() - self.height() - 4
        self.move(x, y)

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
            self.clicked.emit()
        elif event.button() == Qt.MouseButton.RightButton:
            QApplication.quit()