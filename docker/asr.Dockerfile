FROM nvidia/cuda:11.8-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y python3 python3-pip ffmpeg

WORKDIR /app

COPY requirements_asr.txt .

RUN pip install -r requirements_asr.txt

COPY tts_ai_pipeline/asr.py .

EXPOSE 8000

CMD ["uvicorn", "asr:app", "--host", "0.0.0.0", "--port", "8000"]
