import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from src.mascot import MascotWidget
from src.chat_bubble import ChatBubble
from src.voice_client import VoicevoxClient


class DesktopAssistantApp:
    def __init__(self):
        # 1. 各モジュールのインスタンス化
        self.mascot = MascotWidget()
        self.bubble = ChatBubble()
        self.voice = VoicevoxClient()

        # 2. イベント接続 (シグナル / スロット)
        self.mascot.clicked.connect(self.toggle_chat)
        self.bubble.message_sent.connect(self.handle_user_message)

        # VOICEVOX の再生開始/停止シグナルと口パクを完全同期
        self.voice.playback_started.connect(self.mascot.start_speaking)
        self.voice.playback_finished.connect(self.mascot.stop_speaking)

        self.update_bubble_position()
        self.mascot.show()

    def toggle_chat(self):
        if self.bubble.isVisible():
            self.bubble.hide()
        else:
            self.update_bubble_position()
            self.bubble.show()
            self.bubble.input_field.setFocus()

    def update_bubble_position(self):
        screen = QApplication.primaryScreen()
        work_rect = screen.availableGeometry()

        bubble_x = work_rect.right() - self.bubble.width() - 16
        bubble_y = work_rect.bottom() - self.bubble.height() - 10
        self.bubble.move(bubble_x, bubble_y)

    def handle_user_message(self, text: str):
        # テストとして入力されたテキストをオウム返しで喋らせる
        reply_text = f"{text} って言ったね！"
        self.bubble.append_response(reply_text)
        
        # VOICEVOXへテキスト送信（裏で生成して再生開始時に自動で口パク連動）
        self.voice.speak(reply_text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    assistant = DesktopAssistantApp()
    sys.exit(app.exec())