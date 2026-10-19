import re
import requests
import os
import tempfile
from pathlib import Path
from typing import List
from src.config import SERVER_HOST

import json
import asyncio
import websockets

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QScrollArea, QLabel, QGraphicsDropShadowEffect,
    QPushButton, QFileDialog, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QColor, QClipboard, QGuiApplication, QKeySequence, QPixmap, QPainter, QPainterPath


class MessageBubble(QWidget):
    """個別のメッセージ吹き出し（画像サムネイル対応）"""
    def __init__(self, text: str, is_user: bool, file_paths: list = None):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        # 吹き出し本体用のコンテナ
        bubble_box = QWidget()
        box_layout = QVBoxLayout(bubble_box)
        box_layout.setContentsMargins(8, 8, 8, 8)
        box_layout.setSpacing(6)

        # 添付画像のプレビュー追加
        if file_paths:
            for fpath in file_paths:
                p = Path(fpath)
                if p.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
                    img_label = QLabel()
                    pixmap = QPixmap(str(p))
                    if not pixmap.isNull():
                        # 幅最大 180px、高さ最大 140px でアスペクト比維持縮小
                        scaled_pixmap = pixmap.scaled(
                            180, 140,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                        # 角丸クリッピング
                        rounded_pixmap = self._get_rounded_pixmap(scaled_pixmap, 8)
                        img_label.setPixmap(rounded_pixmap)
                        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        box_layout.addWidget(img_label)

        # テキストがある場合はラベルを追加
        if text.strip():
            label = QLabel(text)
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            label.setStyleSheet("color: #FFFFFF; font-size: 13px; background: transparent;")
            box_layout.addWidget(label)

        # ユーザー側 / アシスタント側でスタイルと配置を切り替え
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)

        if is_user:
            bubble_box.setStyleSheet("""
                background-color: #007AFF;
                border-radius: 14px;
                border-bottom-right-radius: 4px;
            """)
            row_layout.addStretch()
            row_layout.addWidget(bubble_box)
        else:
            bubble_box.setStyleSheet("""
                background-color: #2C2C2E;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 14px;
                border-bottom-left-radius: 4px;
            """)
            row_layout.addWidget(bubble_box)
            row_layout.addStretch()

        layout.addLayout(row_layout)

    def _get_rounded_pixmap(self, src_pixmap: QPixmap, radius: int) -> QPixmap:
        """画像を角丸にクリッピングする補助関数"""
        dest_pixmap = QPixmap(src_pixmap.size())
        dest_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(dest_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, src_pixmap.width(), src_pixmap.height(), radius, radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, src_pixmap)
        painter.end()

        return dest_pixmap

class WebSocketWorker(QThread):
    # (role, content, timestamp, image_url) を通知するシグナル
    message_received = Signal(str, str, str, str)

    def __init__(self, ws_url=None):
        super().__init__()
        # SERVER_HOST が "http://localhost:8000" の場合は "ws://localhost:8000/ws" に変換
        if ws_url:
            self.ws_url = ws_url
        else:
            base = SERVER_HOST.replace("http://", "ws://").replace("https://", "wss://")
            self.ws_url = f"{base}/ws"
        self.running = True

    def run(self):
        asyncio.run(self._listen())

    async def _listen(self):
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    while self.running:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        if data.get("type") == "new_message":
                            role = data.get("role", "assistant")
                            content = data.get("content", "")
                            timestamp = data.get("timestamp", "")
                            image_url = data.get("image_url") or ""
                            self.message_received.emit(role, content, timestamp, image_url)
            except Exception as e:
                # サーバー未起動時や切断時は2秒待って再接続
                await asyncio.sleep(2)

    def stop(self):
        self.running = False
        self.wait()

class CustomLineEdit(QLineEdit):
    """Ctrl+V での画像貼り付けに対応した拡張入力欄"""
    image_pasted = Signal(str)

    def keyPressEvent(self, event):
        # QKeySequence.StandardKey.Paste を使用して判定
        if event.matches(QKeySequence.StandardKey.Paste):
            clipboard = QGuiApplication.clipboard()
            mime_data = clipboard.mimeData()

            # クリップボードに画像がある場合は一時保存して添付
            if mime_data.hasImage():
                image = clipboard.image()
                if not image.isNull():
                    temp_dir = Path(tempfile.gettempdir()) / "lefte_clipboard"
                    temp_dir.mkdir(exist_ok=True)
                    temp_file = temp_dir / f"clip_{temp_file_timestamp()}.png"
                    image.save(str(temp_file), "PNG")
                    self.image_pasted.emit(str(temp_file))
                    return

        super().keyPressEvent(event)


def temp_file_timestamp() -> str:
    import time
    return str(int(time.time() * 1000))


class ChatBubble(QWidget):
    """ポップアップチャット画面（マルチモーダル対応）"""
    # メッセージ本文(str) と 添付ファイルパスリスト(list[str]) を発信
    message_sent = Signal(str, list)

    def __init__(self):
        super().__init__()
        self.attached_files: List[str] = []

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAcceptDrops(True)  # ドラッグ＆ドロップ受け入れ
        self.resize(360, 460)

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
        container_layout.setSpacing(6)

        # ヘッダー
        header = QLabel("L.E.F.T.E. ver.2.0", self.container)
        header.setStyleSheet("color: #8E8E93; font-size: 12px; font-weight: bold;")
        container_layout.addWidget(header)

        # スクロールエリア（チャット履歴）
        self.scroll_area = QScrollArea(self.container)
        self.scroll_area.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
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

        # --- 添付ファイルプレビューバー ---
        self.preview_container = QWidget(self.container)
        self.preview_layout = QHBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(2, 2, 2, 2)
        self.preview_layout.setSpacing(6)
        self.preview_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.preview_container.hide()
        container_layout.addWidget(self.preview_container)

        # --- 入力欄 + 添付ボタン ---
        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        self.input_field = CustomLineEdit(self.container)
        self.input_field.setPlaceholderText("メッセージを入力... (Ctrl+Vで画像貼付)")
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
        self.input_field.image_pasted.connect(self.add_attachment)
        input_row.addWidget(self.input_field)

        # 📎 添付ファイル選択ボタン
        self.attach_btn = QPushButton("📎", self.container)
        self.attach_btn.setFixedSize(32, 32)
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
                border: 1px solid transparent;
                border-radius: 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.16);
            }
        """)
        self.attach_btn.clicked.connect(self.open_file_dialog)
        input_row.addWidget(self.attach_btn)

        container_layout.addLayout(input_row)
        outer_layout.addWidget(self.container)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)

        # --- WebSocket リアルタイム同期の開始 ---
        self.ws_worker = WebSocketWorker()
        self.ws_worker.message_received.connect(self.on_ws_message_received)
        self.ws_worker.start()

    def on_ws_message_received(self, role: str, content: str, timestamp: str, image_url: str):
        """WebSocket からメッセージが飛んできた時の自動描画"""
        is_user = (role == "user")

        # 添付画像のパス除去・整形
        clean_text = re.sub(r"\[img:\s*(.*?)\]", "", content).strip()
        clean_text = re.sub(r"\[file:\s*(.*?)\]", "", clean_text).strip()
        clean_text = re.sub(r"\[(slow|normal|fast)\]", "", clean_text).strip()

        # 🚀 直前の吹き出しと内容が全く同じなら二重描画を防止
        for i in range(self.chat_layout.count() - 1, -1, -1):
            item = self.chat_layout.itemAt(i)
            w = item.widget() if item else None
            if isinstance(w, MessageBubble):
                labels = w.findChildren(QLabel)
                if labels and labels[-1].text().strip() == clean_text:
                    return  # 既にHTTPレスポンス等で描画済みならスキップ
                break

        # 添付画像のキャッシュ・取得処理
        file_paths = []
        if image_url:
            cache_dir = Path(tempfile.gettempdir()) / "lefte_history_cache"
            cache_dir.mkdir(exist_ok=True)
            local_path = cache_dir / Path(image_url).name
            if not local_path.exists():
                try:
                    res = requests.get(f"{SERVER_HOST}{image_url}", timeout=3)
                    if res.status_code == 200:
                        with open(local_path, "wb") as f:
                            f.write(res.content)
                except Exception:
                    pass
            if local_path.exists():
                file_paths.append(str(local_path))

        # 吹き出しを追加
        self.add_bubble(clean_text, is_user=is_user, file_paths=file_paths if file_paths else None)
    def closeEvent(self, event):
        """アプリ終了時にスレッドを安全に停止"""
        if hasattr(self, "ws_worker"):
            self.ws_worker.stop()
        super().closeEvent(event)

    # ---------------- 添付ファイル操作 ----------------
    def open_file_dialog(self):
        """Windowsネイティブダイアログを安全に開く"""
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()  # メインウィンドウを隠す
        root.attributes("-topmost", True)  # 最前面に表示

        file_paths = filedialog.askopenfilenames(
            title="送信するファイルを選択",
            filetypes=[
                ("すべての対応形式", "*.png *.jpg *.jpeg *.webp *.mp4 *.mov *.pdf *.txt *.csv *.py"),
                ("画像", "*.png *.jpg *.jpeg *.webp"),
                ("動画", "*.mp4 *.mov"),
                ("ドキュメント", "*.pdf *.txt *.csv *.py"),
                ("すべてのファイル", "*.*"),
            ]
        )
        root.destroy()

        for path in file_paths:
            if path:
                self.add_attachment(str(Path(path)))

    def add_attachment(self, file_path: str):
        """添付リストに追加してUIを更新"""
        if file_path not in self.attached_files:
            self.attached_files.append(file_path)
            self._refresh_preview_ui()

    def remove_attachment(self, file_path: str):
        """キャンセル（削除）ボタン押下時"""
        if file_path in self.attached_files:
            self.attached_files.remove(file_path)
            self._refresh_preview_ui()

    def cleanup_and_close(self):
            """終了時に通信やスレッドを安全に止める"""
            # WebSocketスレッドやワーカーがあれば停止
            if hasattr(self, 'ws_client') and self.ws_client:
                try:
                    self.ws_client.stop()  # または disconnect
                except Exception:
                    pass
            
            # 音声再生中なら停止
            if hasattr(self, 'voice_worker') and self.voice_worker and self.voice_worker.isRunning():
                try:
                    self.voice_worker.quit()
                    self.voice_worker.wait(1000)
                except Exception:
                    pass

            self.close()

    def closeEvent(self, event):
        self.cleanup_and_close()
        event.accept()

    def _refresh_preview_ui(self):
        """添付プレビューのチップ再描画"""
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        if not self.attached_files:
            self.preview_container.hide()
            return

        for p_str in self.attached_files:
            p = Path(p_str)
            ext = p.suffix.lower()
            icon = "🎬 " if ext in [".mp4", ".mov"] else "📄 " if ext in [".pdf", ".txt", ".csv"] else "🖼️ "

            chip = QFrame()
            chip.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.15);
                    border-radius: 6px;
                }
            """)
            c_layout = QHBoxLayout(chip)
            c_layout.setContentsMargins(6, 2, 4, 2)
            c_layout.setSpacing(4)

            display_name = p.name if len(p.name) <= 12 else f"{p.name[:9]}..."
            lbl = QLabel(f"{icon}{display_name}")
            lbl.setStyleSheet("color: #FFFFFF; font-size: 11px;")
            c_layout.addWidget(lbl)

            btn_del = QPushButton("✕")
            btn_del.setFixedSize(16, 16)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #A0A0A5;
                    border: none;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    color: #FF453A;
                }
            """)
            btn_del.clicked.connect(lambda _, path=p_str: self.remove_attachment(path))
            c_layout.addWidget(btn_del)

            self.preview_layout.addWidget(chip)

        self.preview_container.show()
        self.update()

    # ---------------- ドラッグ＆ドロップ ----------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            local_path = url.toLocalFile()
            if os.path.exists(local_path):
                self.add_attachment(local_path)
        event.acceptProposedAction()

    # ---------------- 送信・描画 ----------------
    def send_message(self):
        text = self.input_field.text().strip()
        files = list(self.attached_files)

        if text or files:
            non_img_files = [Path(f).name for f in files if Path(f).suffix.lower() not in [".png", ".jpg", ".jpeg", ".webp"]]
            bubble_text = text
            if non_img_files:
                bubble_text = f"{text}\n[添付: {', '.join(non_img_files)}]" if text else f"[添付: {', '.join(non_img_files)}]"


            self.input_field.clear()
            self.attached_files.clear()
            self._refresh_preview_ui()

            # メッセージとファイルリストを発信
            self.message_sent.emit(text or "添付ファイルを確認してください。", files)

    def append_response(self, text: str):
        # 読み上げ速度タグを除去
        clean_text = re.sub(r"\[(slow|normal|fast)\]", "", text).strip()
        clean_text = re.sub(r"\[img:\s*(.*?)\]", "", clean_text).strip()
        clean_text = re.sub(r"\[file:\s*(.*?)\]", "", clean_text).strip()

        # 直前と同じ内容ならスキップ
        for i in range(self.chat_layout.count() - 1, -1, -1):
            item = self.chat_layout.itemAt(i)
            w = item.widget() if item else None
            if isinstance(w, MessageBubble):
                labels = w.findChildren(QLabel)
                if labels and labels[-1].text().strip() == clean_text:
                    return
                break

        self.add_bubble(clean_text, is_user=False)

    def add_bubble(self, text: str, is_user: bool, file_paths: list = None):
        bubble = MessageBubble(text, is_user=is_user, file_paths=file_paths)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        QTimer.singleShot(20, self.scroll_to_bottom)

    def scroll_to_bottom(self):
        bar = self.scroll_area.verticalScrollBar()
        bar.setValue(bar.maximum())
    
    def load_history(self, messages):
        """過去メッセージのリストを一括でUIに追加（サーバー画像復元対応）"""
        if isinstance(messages, dict):
            messages = messages.get("messages", [])
        if not messages:
            return
        cache_dir = Path(tempfile.gettempdir()) / "lefte_history_cache"
        cache_dir.mkdir(exist_ok=True)
        for item in messages:
            role = item.get("role")
            content = item.get("content")
            if not content:
                continue

            is_user = (role == "user")

            # [img: /uploads/...] パスを抽出
            img_pattern = r"\[img:\s*(.*?)\]"
            found_paths = re.findall(img_pattern, content)

            clean_text = re.sub(img_pattern, "", content).strip()
            clean_text = re.sub(r"\[file:\s*(.*?)\]", "", clean_text).strip()
            clean_text = re.sub(r"\[(slow|normal|fast)\]", "", clean_text).strip()

            restored_images = []
            for path_str in found_paths:
                # サーバーの相対パスからフルURLを構築
                if path_str.startswith("/uploads/"):
                    img_url = f"{SERVER_HOST}{path_str}"
                    local_cache_path = cache_dir / Path(path_str).name
                    
                    # キャッシュになければサーバーからダウンロードして表示
                    if not local_cache_path.exists():
                        try:
                            res = requests.get(img_url, timeout=3)
                            if res.status_code == 200:
                                with open(local_cache_path, "wb") as f:
                                    f.write(res.content)
                        except Exception as e:
                            print(f"[History Image Download Error]: {e}")

                    if local_cache_path.exists():
                        restored_images.append(str(local_cache_path))
                
                elif os.path.exists(path_str):
                    restored_images.append(path_str)

            self.add_bubble(clean_text, is_user=is_user, file_paths=restored_images if restored_images else None)