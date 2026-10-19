import sys
from PySide6.QtWidgets import QApplication

from src.mascot import MascotWidget
from src.chat_bubble import ChatBubble
from src.voice_client import VoicevoxClient
from src.api_client import BackendClient, HistoryFetchWorker
from src.process_manager import VoicevoxProcessManager


class DesktopAssistantApp:
    def __init__(self):
        self.mascot = MascotWidget()
        self.bubble = ChatBubble()
        self.voice = VoicevoxClient()
        self.backend = BackendClient()
        self.voice_manager = VoicevoxProcessManager()
        self.voice_manager.start_engine()

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

        # 過去ログ取得スレッドの実行
        self.history_worker = HistoryFetchWorker()
        self.history_worker.finished_fetch.connect(self.bubble.load_history)
        self.history_worker.error_occurred.connect(
            lambda err: print(f"[History Load]: 履歴取得をスキップ ({err})")
        )
        self.history_worker.start()

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

        bubble_x = work_rect.right() - self.bubble.width() + 2
        bubble_y = work_rect.bottom() - self.bubble.height() - 45
        self.bubble.move(bubble_x, bubble_y)

    def handle_user_message(self, text: str, files: list = None):
        # ユーザーのメッセージと添付ファイルをサーバーへ送信
        self.backend.send_message(text, files)

    def handle_server_response(self, reply_text: str):
        # サーバーからの返答をチャット欄に表示
        self.bubble.append_response(reply_text)
        # 返答テキストをVOICEVOXで喋らせる（口パク自動連動）
        self.voice.speak(reply_text)

    def quit_app(self):
        if hasattr(self, 'chat_window') and self.chat_window:
            try:
                if hasattr(self.chat_window, 'cleanup_and_close'):
                    self.chat_window.cleanup_and_close()
                else:
                    self.chat_window.close()
            except Exception as e:
                print(f"[Exit Error]: {e}")

        # 2. プロセスマネージャー（VOICEVOX等の停止）があれば終了
        if hasattr(self, 'process_manager') and self.process_manager:
            try:
                self.process_manager.stop_all()
            except Exception:
                pass

        # 3. アプリケーション終了
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    assistant = DesktopAssistantApp()
    app.aboutToQuit.connect(assistant.voice_manager.stop_engine)
    sys.exit(app.exec())