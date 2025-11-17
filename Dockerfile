# TTS 전용 서버 Dockerfile
FROM python:3.12-slim

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# MeloTTS 클론 (컨테이너 내에서)
RUN git clone https://github.com/myshell-ai/MeloTTS.git

# 기본 요구사항 복사 및 설치
COPY requirements_web.txt .
RUN pip install --no-cache-dir -r requirements_web.txt

# MeloTTS 의존성 설치
RUN pip install --no-cache-dir \
    cn2an \
    pypinyin \
    unidecode \
    jieba \
    mecab-python3 \
    num2words \
    pykakasi \
    g2p-en \
    anyascii \
    gruut \
    cached_path \
    txtsplit \
    python-multipart

# 애플리케이션 파일 복사
COPY tts_only_server.py .
COPY download_korean_model.py .

# static 디렉토리 생성
RUN mkdir -p static/audio

# 모델 파일을 위한 디렉토리 생성 (볼륨 마운트용)
RUN mkdir -p models

# 포트 노출
EXPOSE 40003

# 환경 변수 설정
ENV PYTHONPATH="/app/MeloTTS:$PYTHONPATH"
ENV CUDA_VISIBLE_DEVICES=""

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:40003/api/models/status || exit 1

# 서버 실행
CMD ["python3", "tts_only_server.py"]