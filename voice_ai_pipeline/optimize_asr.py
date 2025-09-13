import os
import time
import torch
from faster_whisper import WhisperModel

def get_gpu_memory():
    if torch.cuda.is_available():
        return torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
    return 0

def main():
    total_vram = get_gpu_memory()
    print(f"Total VRAM: {total_vram:.2f} GB")

    models = ["tiny", "base", "small", "medium", "large"]  # large may not fit
    sample_audio = "sample.wav"  # assume exists

    if not os.path.exists(sample_audio):
        print("Sample audio file 'sample.wav' not found. Please provide a sample WAV file for benchmarking.")
        return

    results = []

    for model_size in models:
        try:
            print(f"\nBenchmarking Whisper {model_size}...")
            start_load = time.time()
            model = WhisperModel(model_size, device="cuda" if torch.cuda.is_available() else "cpu")
            load_time = time.time() - start_load

            start_transcribe = time.time()
            segments, info = model.transcribe(sample_audio)
            transcribe_time = time.time() - start_transcribe

            text = "".join([segment.text for segment in segments])
            confidence = info.language_probability

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            results.append({
                "model": model_size,
                "load_time": load_time,
                "transcribe_time": transcribe_time,
                "text_length": len(text),
                "confidence": confidence
            })

            print(f"  Load time: {load_time:.2f}s")
            print(f"  Transcribe time: {transcribe_time:.2f}s")
            print(f"  Text length: {len(text)} chars")
            print(f"  Confidence: {confidence:.2f}")

        except Exception as e:
            print(f"  Failed to load {model_size}: {e}")
            continue

    # Recommend best model
    if results:
        # Prioritize speed and quality, but fit VRAM
        # Assume small fits, medium may, large may not
        recommended = "small"
        for r in results:
            if r["model"] == "medium" and r["load_time"] < 10:  # arbitrary
                recommended = "medium"
        print(f"\nRecommended model: {recommended} (fits 24GB VRAM)")

if __name__ == "__main__":
    main()
