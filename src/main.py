import sys
from PySide6.QtWidgets import QApplication

from src.mascot import MascotWidget
from src.chat_bubble import ChatBubble
from src.voice_client import VoicevoxClient
from src.api_client import BackendClient


class DesktopAssistantApp:
    def __init__(self):
        self.mascot = MascotWidget()
        self.bubble = ChatBubble()
        self.voice = VoicevoxClient()
        self.backend = BackendClient()

        # イベント接続
        self.mascot.clicked.connect(self.toggle_chat)
        self.bubble.message_sent.connect(self.handle_user_message)

        # サーバーからの応答受信時にチャット追加 ＆ VOICEVOX発話
        self.backend.response_received.connect(self.handle_server_response)

        # VOICEVOX の再生開始/停止シグナルと口パク同期
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
        bubble_y = work_rect.bottom() - self.bubble.height() - 8
        self.bubble.move(bubble_x, bubble_y)

    def handle_user_message(self, text: str):
        # ユーザーの入力をサーバーへ非同期送信
        self.backend.send_message(text)

    def handle_server_response(self, reply_text: str):
        # サーバーからの返答をチャット欄に表示
        self.bubble.append_response(reply_text)
        # 返答テキストをVOICEVOXで喋らせる（口パク自動連動）
        self.voice.speak(reply_text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    assistant = DesktopAssistantApp()
    sys.exit(app.exec())