import re
import os
import requests
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QThread, QUrl, QTimer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from src.config import (
    VOICEVOX_HOST, SPEAKER_ID, TEMP_VOICE_PATH,
    VOICE_SPEED_SCALE, VOICE_PITCH_SCALE,
    VOICE_INTONATION_SCALE, VOICE_VOLUME_SCALE
)


def clean_text_for_voice(text: str) -> str:
    """VOICEVOX読み上げ用にURL、記号、（動作・感情表現）、顔文字、速度タグを除去"""
    # 1. URL・Markdown記法を除去
    text = re.sub(r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+', '', text)
    text = re.sub(r'[`*#_]', '', text)

    # 2. [slow] [normal] [fast] などのタグを除去
    text = re.sub(r'\[.*?\]', '', text)

    # 3. 全角・半角の丸括弧とその中身を除去（例：（にっこり）、(ドヤ顔)、(๑•̀ㅂ•́)و 等）
    text = re.sub(r'（.*?）', '', text)
    text = re.sub(r'\(.*?\)', '', text)

    # 4. 余分な空白のトリム
    text = re.sub(r'\s+', ' ', text).strip()
    return text


class SynthesisWorker(QThread):
    finished_synthesis = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, text: str):
        super().__init__()
        # ★ clean_text_for_voice を通して読み上げテキストをクリーン化
        self.text = clean_text_for_voice(text)

    def run(self):
        if not self.text:
            self.error_occurred.emit("テキストが空です。")
            return

        try:
            # 1. 音声合成クエリ作成
            query_res = requests.post(
                f"{VOICEVOX_HOST}/audio_query",
                params={"text": self.text, "speaker": SPEAKER_ID},
                timeout=5
            )
            query_res.raise_for_status()
            query_data = query_res.json()

            # 2. パラメータ適用
            query_data["speedScale"] = VOICE_SPEED_SCALE
            query_data["pitchScale"] = VOICE_PITCH_SCALE
            query_data["intonationScale"] = VOICE_INTONATION_SCALE
            query_data["volumeScale"] = VOICE_VOLUME_SCALE
            
            # 発声末尾の無音マージン確保（語尾切れ防止）
            query_data["postPhonemeLength"] = 0.25

            # 3. 音声合成
            synth_res = requests.post(
                f"{VOICEVOX_HOST}/synthesis",
                params={"speaker": SPEAKER_ID},
                json=query_data,
                timeout=60
            )
            synth_res.raise_for_status()

            # 4. 保存
            with open(TEMP_VOICE_PATH, "wb") as f:
                f.write(synth_res.content)
                f.flush()
                os.fsync(f.fileno())

            self.finished_synthesis.emit(str(TEMP_VOICE_PATH))

        except Exception as e:
            self.error_occurred.emit(str(e))


class VoicevoxClient(QObject):
    playback_started = Signal()
    playback_finished = Signal()

    def __init__(self):
        super().__init__()
        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)
        
        # 再生完了状態（EndOfMedia）を監視
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)

        self._worker = None

    def speak(self, text: str):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.stop()

        self._worker = SynthesisWorker(text)
        self._worker.finished_synthesis.connect(self._play_audio)
        self._worker.error_occurred.connect(self._handle_error)
        self._worker.start()

    def _play_audio(self, wav_path: str):
        self.player.setSource(QUrl.fromLocalFile(wav_path))
        self.player.play()

    def _handle_error(self, err_msg: str):
        print(f"[VOICEVOX Client]: {err_msg}")
        self.playback_finished.emit()

    def _on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.playback_started.emit()

    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            # 語尾の自然な余韻マージン
            QTimer.singleShot(150, self.playback_finished.emit)