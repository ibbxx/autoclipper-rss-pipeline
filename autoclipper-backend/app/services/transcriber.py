import whisper
import logging
import torch

logger = logging.getLogger(__name__)

class Transcriber:
    def __init__(self, model_size: str = "base"):
        # Force CPU to avoid macOS MPS/Metal GPU issues
        self.device = "cpu"
        logger.info(f"Loading Whisper model '{model_size}' on {self.device}...")
        self.model = whisper.load_model(model_size, device=self.device)

    def transcribe(self, audio_path: str) -> list[dict]:
        """
        Transcribe audio file.
        Returns list of segments: [{'text': str, 'start': float, 'end': float}]
        """
        logger.info(f"Transcribing {audio_path}...")
        try:
            result = self.model.transcribe(audio_path)
            segments = []
            for seg in result["segments"]:
                segments.append({
                    "text": seg["text"].strip(),
                    "start": seg["start"],
                    "end": seg["end"]
                })
            return segments
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
