FROM nvidia/cuda:11.8-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y python3 python3-pip ffmpeg

WORKDIR /app

COPY requirements_tts.txt .

RUN pip install -r requirements_tts.txt

COPY tts_ai_pipeline/tts.py .

EXPOSE 8001

CMD ["uvicorn", "tts:app", "--host", "0.0.0.0", "--port", "8001"]
