import requests
from PySide6.QtCore import QObject, Signal, QThread
from src.config import SERVER_HOST, CHAT_ENDPOINT


class ServerRequestWorker(QThread):
    """サーバーへのリクエスト送信を非同期で実行"""
    response_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def run(self):
        try:
            payload = {"message": self.message}
            res = requests.post(CHAT_ENDPOINT, json=payload, timeout=20)
            res.raise_for_status()

            data = res.json()
            # サーバーの返答キー（response / reply / text など）に対応
            reply_text = data.get("response") or data.get("reply") or data.get("text", "")
            
            if not reply_text:
                reply_text = "（サーバーからの応答が空でした）"

            self.response_ready.emit(reply_text)

        except requests.exceptions.ConnectionError:
            self.error_occurred.emit("サーバーに接続できませんでした。")
        except requests.exceptions.Timeout:
            self.error_occurred.emit("サーバーの応答がタイムアウトしました。")
        except Exception as e:
            self.error_occurred.emit(f"通信エラー: {e}")


class BackendClient(QObject):
    """メインアプリから呼び出す通信インターフェース"""
    response_received = Signal(str)

    def __init__(self):
        super().__init__()
        self._worker = None

    def send_message(self, message: str):
        self._worker = ServerRequestWorker(message)
        self._worker.response_ready.connect(self.response_received.emit)
        self._worker.error_occurred.connect(self._handle_error)
        self._worker.start()

    def _handle_error(self, err_msg: str):
        print(f"[Backend Client]: {err_msg}")
        self.response_received.emit(err_msg)


class HistoryFetchWorker(QThread):
    finished_fetch = Signal(list)
    error_occurred = Signal(str)

    def run(self):
        try:
            res = requests.get(f"{SERVER_HOST}/history?limit=30", timeout=5)
            res.raise_for_status()
            data = res.json()
            self.finished_fetch.emit(data)
        except Exception as e:
            self.error_occurred.emit(str(e))