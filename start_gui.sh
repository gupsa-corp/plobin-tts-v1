#!/bin/bash

echo "==============================================="
echo "       한국어 TTS GUI 실행기"
echo "==============================================="

# 현재 디렉토리 확인
echo "현재 디렉토리: $(pwd)"

# 가상환경 활성화
echo "1. 가상환경 활성화..."
source korean_tts_env/bin/activate

# Python 버전 확인
echo "2. Python 버전: $(python --version)"

# 필요한 패키지 확인
echo "3. 패키지 확인..."
python -c "import customtkinter; print('✓ CustomTkinter 설치됨')" 2>/dev/null || echo "✗ CustomTkinter 없음"
python -c "import pygame; print('✓ Pygame 설치됨')" 2>/dev/null || echo "✗ Pygame 없음"

# GUI 실행
echo "4. 한국어 TTS GUI 실행..."
python korean_tts_gui_final.py

echo "GUI 종료됨."