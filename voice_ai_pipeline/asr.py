"""ASR service using Whisper for speech-to-text transcription."""

import os
from typing import Dict, List
from faster_whisper import WhisperModel
from fastapi import FastAPI, UploadFile, HTTPException
import tempfile
import torch


class ASR:
    """Automatic Speech Recognition service using OpenAI's Whisper model.

    This class provides functionality to load a Whisper model and transcribe
    audio files to text.
    """

    def __init__(self, model_name: str = "small", use_gpu: bool | None = None) -> None:
        """Initialize the ASR service.

        Args:
            model_name: The name/size of the Whisper model to use.
                Options: "tiny", "base", "small", "medium", "large".
            use_gpu: Whether to use GPU acceleration. If None, auto-detect GPU availability.
        """
        self.model_name = model_name
        self.use_gpu = use_gpu if use_gpu is not None else self._detect_gpu()
        self.model: WhisperModel | None = None
        self.load_model()

    def _detect_gpu(self) -> bool:
        """Detect if GPU is available for acceleration.

        Returns:
            True if GPU is available and should be used, False otherwise.
        """
        try:
            return torch.cuda.is_available() and torch.cuda.device_count() > 0
        except Exception:
            return False

    def load_model(self) -> None:
        """Load the Whisper model into memory.

        Raises:
            RuntimeError: If model loading fails.
        """
        try:
            device = "cuda" if self.use_gpu else "cpu"
            compute_type = "float16" if self.use_gpu else "int8"

            print(f"Loading ASR model '{self.model_name}' on {device} with compute_type={compute_type}")

            self.model = WhisperModel(
                self.model_name,
                device=device,
                compute_type=compute_type
            )
            print(f"ASR model loaded successfully on {device}")
        except Exception as e:
            # Try fallback to CPU if GPU failed
            if self.use_gpu:
                print(f"GPU loading failed ({e}), falling back to CPU...")
                self.use_gpu = False
                try:
                    self.model = WhisperModel(
                        self.model_name,
                        device="cpu",
                        compute_type="int8"
                    )
                    print("ASR model loaded successfully on CPU (fallback)")
                except Exception as cpu_e:
                    raise RuntimeError(f"Failed to load ASR model {self.model_name} on both GPU and CPU: GPU error: {e}, CPU error: {cpu_e}")
            else:
                raise RuntimeError(f"Failed to load ASR model {self.model_name}: {e}")

    def transcribe(self, audio_path: str) -> str:
        """Transcribe an audio file to text.

        Args:
            audio_path: Path to the audio file to transcribe.

        Returns:
            The transcribed text.

        Raises:
            RuntimeError: If the model is not loaded.
        """
        if self.model is None:
            raise RuntimeError("ASR model not loaded")

        segments, info = self.model.transcribe(audio_path)
        return "".join([segment.text for segment in segments])

    def get_supported_formats(self) -> List[str]:
        """Get the list of supported audio file formats.

        Returns:
            List of supported file extensions.
        """
        return [".wav", ".mp3", ".flac"]

    def get_model_info(self) -> Dict[str, str]:
        """Get information about the loaded model.

        Returns:
            Dictionary containing model information.
        """
        return {
            "model_name": self.model_name,
            "device": "cuda" if self.use_gpu else "cpu",
            "loaded": str(self.model is not None)
        }

    def is_healthy(self) -> bool:
        """Check if the ASR service is healthy.

        Returns:
            True if the model is loaded and ready, False otherwise.
        """
        return self.model is not None


app = FastAPI(title="ASR Service", description="Speech-to-text transcription service")

asr_service = ASR(
    model_name=os.getenv("ASR_MODEL", "small"),
    use_gpu=os.getenv("USE_GPU", "true").lower() == "true"
)


@app.post("/transcribe")
async def transcribe(file: UploadFile) -> Dict[str, str]:
    """Transcribe an uploaded audio file to text.

    Args:
        file: The uploaded audio file.

    Returns:
        Dictionary containing the transcribed text.

    Raises:
        HTTPException: If the file format is unsupported or transcription fails.
    """
    if not any(file.filename.endswith(fmt) for fmt in asr_service.get_supported_formats()):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported formats: {asr_service.get_supported_formats()}"
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        temp_file.write(await file.read())
        temp_path = temp_file.name

    try:
        text = asr_service.transcribe(temp_path)
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        os.unlink(temp_path)


@app.get("/health")
async def health() -> Dict[str, bool]:
    """Check the health status of the ASR service.

    Returns:
        Dictionary indicating service health.
    """
    return {"healthy": asr_service.is_healthy()}


@app.get("/info")
async def info() -> Dict[str, str]:
    """Get information about the ASR service.

    Returns:
        Dictionary containing service information.
    """
    return asr_service.get_model_info()


if __name__ == "__main__":
    import uvicorn

    # Support for consolidated container
    service_type = os.getenv("SERVICE_TYPE", "asr")
    port = int(os.getenv("PORT", "8000"))

    if service_type == "asr":
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        print(f"ASR service configured but SERVICE_TYPE={service_type}, skipping...")
