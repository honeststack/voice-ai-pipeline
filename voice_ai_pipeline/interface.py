"""Gradio interface for the TTS AI Pipeline."""

import os
import tempfile
from typing import Tuple, Optional
import gradio as gr
import numpy as np
import scipy.io.wavfile as wav
import asyncio
import aiohttp

# Import MCP client
try:
    from .mcp_client import MCPClient, PromptType
    MCP_AVAILABLE = True
except ImportError:
    MCPClient = None
    PromptType = None
    MCP_AVAILABLE = False

asr_url = os.getenv("ASR_URL", "http://localhost:8000/transcribe")
tts_url = os.getenv("TTS_URL", "http://localhost:8001/synthesize")
mcp_enabled = os.getenv("MCP_ENABLED", "false").lower() == "true"


async def process_audio_async(audio: Tuple[int, np.ndarray] | None, enable_mcp: bool = False) -> Tuple[str | None, str]:
    """Process audio input asynchronously: transcribe to text and synthesize back to speech.

    Args:
        audio: Tuple of (sample_rate, audio_data) from microphone input,
               or None if no audio provided.
        enable_mcp: Whether to send transcription to Copilot via MCP

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
        async with aiohttp.ClientSession() as session:
            # Send to ASR service asynchronously
            with open(temp_path, "rb") as f:
                audio_data = f.read()

            async with session.post(asr_url, data={"file": audio_data}) as response:
                if response.status != 200:
                    return None, f"ASR failed: {await response.text()}"

                asr_result = await response.json()
                text = asr_result["text"]

            # Process with MCP if enabled
            mcp_result = ""
            if enable_mcp and MCP_AVAILABLE and mcp_enabled and MCPClient is not None:
                try:
                    mcp_client = MCPClient()
                    mcp_response = await asyncio.get_event_loop().run_in_executor(
                        None, mcp_client.send_to_copilot, text
                    )
                    mcp_result = f"\n\n🤖 Copilot Response: {mcp_response.get('result', 'No response')}"
                except Exception as e:
                    mcp_result = f"\n\n⚠️ MCP Error: {str(e)}"

            # Send text to TTS service asynchronously
            async with session.post(tts_url, json={"text": text}) as response:
                if response.status != 200:
                    return None, f"TTS failed: {await response.text()}"

                audio_content = await response.read()

            output_path = "output.wav"
            with open(output_path, "wb") as f:
                f.write(audio_content)

            # Combine transcription with MCP result
            full_text = text + mcp_result

            return output_path, full_text
    finally:
        os.unlink(temp_path)


def process_audio(audio: Tuple[int, np.ndarray] | None, enable_mcp: bool = False) -> Tuple[str | None, str]:
    """Synchronous wrapper for async audio processing.

    Args:
        audio: Tuple of (sample_rate, audio_data) from microphone input,
               or None if no audio provided.
        enable_mcp: Whether to send transcription to Copilot via MCP

    Returns:
        Tuple of (output_audio_path, transcribed_text).
        Returns (None, error_message) if processing fails.
    """
    try:
        # Run async function in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(process_audio_async(audio, enable_mcp))
        loop.close()
        return result
    except Exception as e:
        return None, f"Processing failed: {str(e)}"


def create_interface() -> gr.Interface:
    """Create and configure the Gradio interface.

    Returns:
        Configured Gradio Interface object.
    """
    # Determine description based on MCP availability
    description = "Speak into the microphone, get transcribed text and synthesized speech."
    if MCP_AVAILABLE and mcp_enabled:
        description += " Optionally send transcription to Copilot for AI assistance."

    return gr.Interface(
        fn=process_audio,
        inputs=[
            gr.Audio(sources=["microphone"], type="numpy", label="Audio Input"),
            gr.Checkbox(
                label="Send to Copilot (MCP)",
                value=False,
                visible=MCP_AVAILABLE and mcp_enabled,
                info="Send transcription to Copilot for AI-powered responses"
            )
        ],
        outputs=[
            gr.Audio(label="Synthesized Speech"),
            gr.Textbox(label="Transcribed Text & Copilot Response")
        ],
        title="TTS AI Pipeline with Copilot Integration",
        description=description
    )


if __name__ == "__main__":
    iface = create_interface()
    iface.launch(server_name="0.0.0.0", server_port=7860)
