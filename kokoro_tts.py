"""Kokoro TTS plugin for livekit-agents"""
from livekit.agents import tts, APIConnectOptions
from livekit import rtc
from kokoro_onnx import Kokoro
import numpy as np
import asyncio
import uuid


class KokoroTTS(tts.TTS):
    def __init__(
        self,
        model_path: str = "kokoro-v1.0.onnx",
        voices_path: str = "voices-v1.0.bin",
        voice: str = "af_heart",
        speed: float = 1.0,
    ):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=24000,
            num_channels=1,
        )
        self._model_path = model_path
        self._voices_path = voices_path
        self._voice = voice
        self._speed = speed
        self._kokoro: Kokoro | None = None

    def _ensure_model(self) -> Kokoro:
        if self._kokoro is None:
            self._kokoro = Kokoro(self._model_path, self._voices_path)
        return self._kokoro

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = APIConnectOptions(),
    ) -> "KokoroChunkedStream":
        return KokoroChunkedStream(
            tts=self,
            text=text,
            conn_options=conn_options,
        )


class KokoroChunkedStream(tts.ChunkedStream):
    def __init__(
        self,
        *,
        tts: KokoroTTS,
        text: str,
        conn_options: APIConnectOptions,
    ):
        super().__init__(tts=tts, input_text=text, conn_options=conn_options)
        self._kokoro_tts = tts
        self._text = text

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        kokoro = self._kokoro_tts._ensure_model()

        # Run synthesis in a thread to avoid blocking
        samples, sample_rate = await asyncio.to_thread(
            kokoro.create,
            self._text,
            voice=self._kokoro_tts._voice,
            speed=self._kokoro_tts._speed,
        )

        # Convert to int16 PCM
        samples_int16 = (samples * 32767).astype(np.int16)

        # Initialize the emitter
        request_id = str(uuid.uuid4())
        output_emitter.initialize(
            request_id=request_id,
            sample_rate=sample_rate,
            num_channels=1,
            mime_type="audio/pcm",
        )

        # Push audio
        output_emitter.push(samples_int16.tobytes())
        output_emitter.flush()
