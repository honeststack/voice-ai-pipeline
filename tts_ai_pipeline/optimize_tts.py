import os
import time
import torch
from TTS.api import TTS

def get_gpu_memory():
    if torch.cuda.is_available():
        return torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
    return 0

def main():
    total_vram = get_gpu_memory()
    print(f"Total VRAM: {total_vram:.2f} GB")

    # Common TTS models
    models = [
        "tts_models/en/ljspeech/tacotron2-DDC_ph",
        "tts_models/en/ljspeech/tacotron2-DDC",  # if exists
        "tts_models/en/ljspeech/glow-tts",
    ]

    sample_text = "Hello, this is a test of the text to speech system."

    results = []

    for model_name in models:
        try:
            print(f"\nBenchmarking TTS {model_name}...")
            start_load = time.time()
            tts = TTS(model_name).to("cuda" if torch.cuda.is_available() else "cpu")
            load_time = time.time() - start_load

            start_synth = time.time()
            tts.tts_to_file(text=sample_text, file_path="temp_output.wav")
            synth_time = time.time() - start_synth

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            results.append({
                "model": model_name,
                "load_time": load_time,
                "synth_time": synth_time,
                "text_length": len(sample_text)
            })

            print(f"  Load time: {load_time:.2f}s")
            print(f"  Synth time: {synth_time:.2f}s")
            print(f"  Output saved as temp_output.wav")

        except Exception as e:
            print(f"  Failed to load {model_name}: {e}")
            continue

    # Recommend
    if results:
        # Fastest
        fastest = min(results, key=lambda x: x["synth_time"])
        print(f"\nRecommended model: {fastest['model']} (fastest synthesis)")

    # Clean up
    if os.path.exists("temp_output.wav"):
        os.remove("temp_output.wav")

if __name__ == "__main__":
    main()
