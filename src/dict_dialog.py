# src/dict_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt

class UserDictDialog(QDialog):
    def __init__(self, voice_client, parent=None):
        super().__init__(parent)
        self.voice_client = voice_client
        self.setWindowTitle("辞書登録")
        self.setFixedSize(320, 180)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)

        # 表記入力
        layout.addWidget(QLabel("単語 (表記):"))
        self.surface_input = QLineEdit()
        self.surface_input.setPlaceholderText("例: LEFTE")
        layout.addWidget(self.surface_input)

        # 読み入力
        layout.addWidget(QLabel("読み (カタカナ):"))
        self.yomi_input = QLineEdit()
        self.yomi_input.setPlaceholderText("例: レフティ")
        layout.addWidget(self.yomi_input)

        # ボタン
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("登録")
        self.cancel_btn = QPushButton("キャンセル")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.save_btn.clicked.connect(self.handle_save)
        self.cancel_btn.clicked.connect(self.reject)

    def handle_save(self):
        surface = self.surface_input.text().strip()
        pronunciation = self.yomi_input.text().strip()

        if not surface or not pronunciation:
            QMessageBox.warning(self, "入力エラー", "単語と読みを両方入力してください。")
            return

        # VoicevoxClient の辞書登録メソッドを呼び出す
        success = self.voice_client.register_word(surface, pronunciation)
        if success:
            QMessageBox.information(self, "完了", f"「{surface}」を辞書に登録しました。")
            self.accept()
        else:
            QMessageBox.critical(self, "エラー", "辞書の登録に失敗しました。\nVOICEVOX Engineの起動状態を確認してください。")