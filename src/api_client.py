import os
import mimetypes
import requests
from pathlib import Path
from typing import List, Optional
from PySide6.QtCore import QObject, Signal, QThread
from src.config import SERVER_HOST, CHAT_ENDPOINT


class ServerRequestWorker(QThread):
    """サーバーへのリクエスト送信を非同期で実行（マルチパート＆MIME対応）"""
    response_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, message: str, file_paths: Optional[List[str]] = None):
        super().__init__()
        self.message = message
        self.file_paths = file_paths or []

    def run(self):
        opened_files = []
        try:
            # フォームデータ（message は必須）
            data = {"message": self.message}
            files = []

            # 添付ファイルが存在する場合はバイナリを開いて files リストを組み立て
            for file_path in self.file_paths:
                p = Path(file_path)
                if p.exists() and p.is_file():
                    f = open(p, "rb")
                    opened_files.append(f)

                    # 拡張子から MIME タイプを推測
                    mime_type, _ = mimetypes.guess_type(str(p))
                    if not mime_type:
                        ext = p.suffix.lower()
                        if ext in [".jpg", ".jpeg"]:
                            mime_type = "image/jpeg"
                        elif ext == ".png":
                            mime_type = "image/png"
                        elif ext == ".webp":
                            mime_type = "image/webp"
                        elif ext == ".mp4":
                            mime_type = "video/mp4"
                        elif ext in [".mov", ".quicktime"]:
                            mime_type = "video/quicktime"
                        elif ext == ".pdf":
                            mime_type = "application/pdf"
                        else:
                            mime_type = "text/plain"

                    # (フィールド名, (ファイル名, ファイルオブジェクト, MIMEタイプ))
                    files.append(("files", (p.name, f, mime_type)))

            # ファイルアップロードやGeminiのマルチモーダル解析時間を考慮してタイムアウトを60秒に延長
            if files:
                res = requests.post(CHAT_ENDPOINT, data=data, files=files, timeout=60)
            else:
                res = requests.post(CHAT_ENDPOINT, data=data, timeout=30)

            res.raise_for_status()

            res_data = res.json()
            reply_text = res_data.get("response") or res_data.get("reply") or res_data.get("text", "")
            
            if not reply_text:
                reply_text = "（サーバーからの応答が空でした）"

            self.response_ready.emit(reply_text)

        except requests.exceptions.ConnectionError:
            self.error_occurred.emit("サーバーに接続できませんでした。")
        except requests.exceptions.Timeout:
            self.error_occurred.emit("サーバーの応答がタイムアウトしました。")
        except Exception as e:
            self.error_occurred.emit(f"通信エラー: {e}")
        finally:
            # 開いたファイルハンドルを確実にクローズ
            for f in opened_files:
                f.close()


class BackendClient(QObject):
    """メインアプリから呼び出す通信インターフェース"""
    response_received = Signal(str)

    def __init__(self):
        super().__init__()
        self._worker = None

    def send_message(self, message: str, file_paths: Optional[List[str]] = None):
        """
        メッセージと任意のファイルパスリスト（画像・動画・PDF等）をサーバーに送信
        """
        # 前回のワーカーが動いていたら安全のため待機
        if self._worker and self._worker.isRunning():
            self._worker.wait()

        self._worker = ServerRequestWorker(message, file_paths)
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