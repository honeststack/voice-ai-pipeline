FROM python:3.10-slim

RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app

COPY requirements_interface.txt .

RUN pip install -r requirements_interface.txt

COPY tts_ai_pipeline/interface.py .

EXPOSE 7860

CMD ["python", "interface.py"]
