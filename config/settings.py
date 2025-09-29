#!/usr/bin/env python3
"""
설정 관리 모듈
"""

import os
from typing import Optional

# 서버 설정
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 6001  # 기존 포트로 통합
DEBUG = True

# TTS 설정
DEFAULT_TTS_LANGUAGE = "KR"
DEFAULT_TTS_SPEED = 1.0
DEFAULT_TTS_DEVICE = "auto"

# STT 설정
STT_MODEL_SIZE = "base"  # base, small, medium, large
STT_LANGUAGE = "ko"  # 한국어 기본값
STT_TEMPERATURE = 0.0
STT_INITIAL_PROMPT = ""

# 오디오 전처리 설정
AUDIO_SAMPLE_RATE = 16000
AUDIO_TRIM_TOP_DB = 20
AUDIO_NOISE_GATE_THRESHOLD = 0.01
AUDIO_VOLUME_NORMALIZE = 0.8

# 파일 경로 설정
STATIC_DIR = "static"
AUDIO_DIR = "static/audio"
TEMPLATES_DIR = "templates"

# 자동 대화 설정
DEFAULT_AUTO_CHAT_THEME = "casual"
DEFAULT_AUTO_CHAT_INTERVAL = 30

# 모델 초기화 설정
def get_device():
    """GPU/CPU 디바이스 자동 선택"""
    try:
        import torch
        return 'cuda' if torch.cuda.is_available() else 'cpu'
    except ImportError:
        return 'cpu'

# 디렉토리 생성
def ensure_directories():
    """필요한 디렉토리들 생성"""
    os.makedirs(STATIC_DIR, exist_ok=True)
    os.makedirs(AUDIO_DIR, exist_ok=True)
    os.makedirs(TEMPLATES_DIR, exist_ok=True)