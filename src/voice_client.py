import requests
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QThread, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from .config import VOICEVOX_HOST, SPEAKER_ID, BASE_DIR


class SynthesisWorker(QThread):
    """VOICEVOX APIとの通信を裏スレッドで行うワーカー"""
    finished_synthesis = Signal(str)  # 保存先ファイルパスを返す
    error_occurred = Signal(str)

    def __init__(self, text: str, host: str, speaker_id: int):
        super().__init__()
        self.text = text
        self.host = host
        self.speaker_id = speaker_id

    def run(self):
        try:
            # 1. 音声クエリ作成
            query_res = requests.post(
                f"{self.host}/audio_query",
                params={"text": self.text, "speaker": self.speaker_id},
                timeout=5
            )
            query_res.raise_for_status()

            # 2. 音声合成
            synth_res = requests.post(
                f"{self.host}/synthesis",
                params={"speaker": self.speaker_id},
                json=query_res.json(),
                timeout=10
            )
            synth_res.raise_for_status()

            # 3. 一時保存
            temp_path = BASE_DIR / "temp_voice.wav"
            with open(temp_path, "wb") as f:
                f.write(synth_res.content)

            self.finished_synthesis.emit(str(temp_path))
        except Exception as e:
            self.error_occurred.emit(str(e))


class VoicevoxClient(QObject):
    """VOICEVOXでの発話制御と音声再生を行う"""
    playback_started = Signal()
    playback_finished = Signal()

    def __init__(self, host: str = VOICEVOX_HOST, speaker_id: int = SPEAKER_ID):
        super().__init__()
        self.host = host
        self.speaker_id = speaker_id

        # プレイヤー設定
        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)

        self._worker = None

    def speak(self, text: str):
        """非同期で音声を生成して再生"""
        self._worker = SynthesisWorker(text, self.host, self.speaker_id)
        self._worker.finished_synthesis.connect(self._play_audio)
        self._worker.error_occurred.connect(self._handle_error)
        self._worker.start()

    def _play_audio(self, wav_path: str):
        self.player.setSource(QUrl.fromLocalFile(wav_path))
        self.player.play()

    def _handle_error(self, err_msg: str):
        print(f"[VOICEVOX エラー]: {err_msg}")
        self.playback_finished.emit()

    def _on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.playback_started.emit()
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            self.playback_finished.emit()