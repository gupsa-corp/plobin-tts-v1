#!/bin/bash

echo "한국어 TTS 실행 스크립트"
echo "========================"

# 가상환경 활성화
echo "1. 가상환경 활성화..."
source korean_tts_env/bin/activate

# Python 스크립트 실행
echo "2. 한국어 TTS 테스트 실행..."
python korean_tts_simple.py

echo "완료!"