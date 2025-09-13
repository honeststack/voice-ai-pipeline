"""TTS service using Coqui TTS for text-to-speech synthesis."""

import os
from typing import Dict
from TTS.api import TTS
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import tempfile


class TextRequest(BaseModel):
    """Request model for text synthesis."""
    text: str


class TTSService:
    """Text-to-Speech service using Coqui TTS.

    This class provides functionality to load a TTS model and synthesize
    text into audio files.
    """

    def __init__(self, model_name: str = "tts_models/en/ljspeech/tacotron2-DDC_ph", use_gpu: bool = True) -> None:
        """Initialize the TTS service.

        Args:
            model_name: The name of the TTS model to use.
            use_gpu: Whether to use GPU acceleration if available.
        """
        self.model_name = model_name
        self.use_gpu = use_gpu
        self.tts: TTS | None = None
        self.load_model()

    def load_model(self) -> None:
        """Load the TTS model into memory.

        Raises:
            RuntimeError: If model loading fails.
        """
        try:
            self.tts = TTS(self.model_name, gpu=self.use_gpu)
        except Exception as e:
            raise RuntimeError(f"Failed to load TTS model {self.model_name}: {e}")

    def synthesize(self, text: str, output_path: str) -> None:
        """Synthesize text into an audio file.

        Args:
            text: The text to synthesize.
            output_path: Path where the output audio file will be saved.

        Raises:
            RuntimeError: If the model is not loaded.
        """
        if self.tts is None:
            raise RuntimeError("TTS model not loaded")

        self.tts.tts_to_file(text=text, file_path=output_path)

    def get_model_info(self) -> Dict[str, str]:
        """Get information about the loaded model.

        Returns:
            Dictionary containing model information.
        """
        return {
            "model_name": self.model_name,
            "device": "cuda" if self.use_gpu else "cpu",
            "loaded": str(self.tts is not None)
        }

    def is_healthy(self) -> bool:
        """Check if the TTS service is healthy.

        Returns:
            True if the model is loaded and ready, False otherwise.
        """
        return self.tts is not None


app = FastAPI(title="TTS Service", description="Text-to-speech synthesis service")

tts_service = TTSService(
    model_name=os.getenv("TTS_MODEL", "tts_models/en/ljspeech/tacotron2-DDC_ph"),
    use_gpu=os.getenv("USE_GPU", "true").lower() == "true"
)


@app.post("/synthesize")
async def synthesize(request: TextRequest) -> FileResponse:
    """Synthesize text into speech audio.

    Args:
        request: The text synthesis request.

    Returns:
        The synthesized audio file.

    Raises:
        HTTPException: If synthesis fails.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        temp_path = temp_file.name

    try:
        print(f"Starting synthesis to: {temp_path}")
        tts_service.synthesize(request.text, temp_path)
        
        # Check if file was created and has content
        if not os.path.exists(temp_path):
            raise HTTPException(status_code=500, detail=f"Output file was not created: {temp_path}")
        
        file_size = os.path.getsize(temp_path)
        print(f"Synthesis completed. File size: {file_size} bytes")
        
        if file_size == 0:
            raise HTTPException(status_code=500, detail="Output file is empty")
        
        return FileResponse(
            temp_path,
            media_type="audio/wav",
            filename="output.wav"
        )
    except Exception as e:
        print(f"Synthesis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")
    finally:
        # Don't delete the file immediately - let FastAPI handle it
        pass


@app.get("/health")
async def health() -> Dict[str, bool]:
    """Check the health status of the TTS service.

    Returns:
        Dictionary indicating service health.
    """
    return {"healthy": tts_service.is_healthy()}


@app.get("/info")
async def info() -> Dict[str, str]:
    """Get information about the TTS service.

    Returns:
        Dictionary containing service information.
    """
    return tts_service.get_model_info()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
