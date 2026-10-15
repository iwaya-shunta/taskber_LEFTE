from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QScrollArea, QLabel, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor


class MessageBubble(QWidget):
    """個別のメッセージ吹き出し"""
    def __init__(self, text: str, is_user: bool):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        if is_user:
            layout.addStretch()
            layout.addWidget(label)
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
            layout.addWidget(label)
            layout.addStretch()
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
    """ポップアップチャット画面"""
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

        header = QLabel("L.E.F.T.E. ver.2.0", self.container)
        header.setStyleSheet("color: #8E8E93; font-size: 12px; font-weight: bold;")
        container_layout.addWidget(header)

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
    
    def load_history(self, messages: list):
        """過去メッセージのリストを一括でUIに追加"""
        for item in messages:
            role = item.get("role")
            content = item.get("content")
            if not content:
                continue
            is_user = (role == "user")
            self.add_bubble(content, is_user=is_user)