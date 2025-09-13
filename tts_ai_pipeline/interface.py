"""Gradio interface for the TTS AI Pipeline."""

import os
import tempfile
from typing import Tuple
import gradio as gr
import numpy as np
import requests
import scipy.io.wavfile as wav

asr_url = os.getenv("ASR_URL", "http://asr-service:8000/transcribe")
tts_url = os.getenv("TTS_URL", "http://tts-service:8001/synthesize")


def process_audio(audio: Tuple[int, np.ndarray] | None) -> Tuple[str | None, str]:
    """Process audio input: transcribe to text and synthesize back to speech.

    Args:
        audio: Tuple of (sample_rate, audio_data) from microphone input,
               or None if no audio provided.

    Returns:
        Tuple of (output_audio_path, transcribed_text).
        Returns (None, error_message) if processing fails.
    """
    if audio is None:
        return None, "No audio provided"

    sample_rate, data = audio
    # Whisper handles various sample rates, but we save as WAV
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        wav.write(temp_file.name, sample_rate, data.astype(np.int16))
        temp_path = temp_file.name

    try:
        # Send to ASR service
        with open(temp_path, "rb") as f:
            response = requests.post(asr_url, files={"file": f})
        if response.status_code != 200:
            return None, f"ASR failed: {response.text}"

        text = response.json()["text"]

        # Send text to TTS service
        response = requests.post(tts_url, json={"text": text})
        if response.status_code != 200:
            return None, f"TTS failed: {response.text}"

        output_path = "output.wav"
        with open(output_path, "wb") as f:
            f.write(response.content)

        return output_path, text
    finally:
        os.unlink(temp_path)


def create_interface() -> gr.Interface:
    """Create and configure the Gradio interface.

    Returns:
        Configured Gradio Interface object.
    """
    return gr.Interface(
        fn=process_audio,
        inputs=gr.Audio(source="microphone", type="numpy"),
        outputs=[
            gr.Audio(label="Synthesized Speech"),
            gr.Textbox(label="Transcribed Text")
        ],
        title="TTS AI Pipeline",
        description="Speak into the microphone, get transcribed text and synthesized speech."
    )


if __name__ == "__main__":
    iface = create_interface()
    iface.launch(server_name="0.0.0.0", server_port=7860)
