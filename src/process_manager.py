import os
import subprocess
import time
from pathlib import Path
import requests
from src.config import VOICEVOX_HOST, VOICEVOX_EXE_PATH


class VoicevoxProcessManager:
    def __init__(self):
        self.process = None

    def is_engine_running(self) -> bool:
        """VOICEVOX Engineが応答しているか確認"""
        try:
            res = requests.get(f"{VOICEVOX_HOST}/version", timeout=1.0)
            return res.status_code == 200
        except Exception:
            return False

    def start_engine(self):
        """未起動ならvoicevox_engine.exeをバックグラウンド起動し、応答があるまで待機"""
        if self.is_engine_running():
            print("[ProcessManager]: VOICEVOX Engine は既に起動しています。")
            return

        exe_path = Path(VOICEVOX_EXE_PATH)
        if not exe_path.exists():
            print(f"[ProcessManager エラー]: 指定されたパスが存在しません: {exe_path}")
            return

        print(f"[ProcessManager]: VOICEVOX Engine を起動中... ({exe_path})")
        try:
            engine_dir = str(exe_path.parent)

            # 引数指定
            cmd = [str(exe_path), "--host", "127.0.0.1", "--port", "50021"]

            # ウィンドウ非表示フラグ
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            self.process = subprocess.Popen(
                cmd,
                cwd=engine_dir,
                stdout=subprocess.DEVNULL,  # バッファ詰まり防止
                stderr=subprocess.DEVNULL,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception as e:
            print(f"[ProcessManager エラー]: VOICEVOX の起動に失敗しました: {e}")
            return

        # 起動完了（ヘルスチェック成功）まで待機（最大15秒）
        for _ in range(30):
            time.sleep(0.5)
            if self.is_engine_running():
                print("[ProcessManager]: VOICEVOX Engine の準備が完了しました。")
                return

        print("[ProcessManager 警告]: VOICEVOX Engine の起動確認がタイムアウトしました。")

    def stop_engine(self):
        """アプリ側で起動したプロセスを終了"""
        if self.process and self.process.poll() is None:
            print("[ProcessManager]: VOICEVOX Engine を終了します。")
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None