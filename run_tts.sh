#!/bin/bash

# MeloTTS 실행 스크립트
# 사용법: ./run_tts.sh "변환할 텍스트" [언어] [디바이스]

# 기본값 설정
TEXT=${1:-"안녕하세요 테스트입니다"}
LANGUAGE=${2:-"KR"}
DEVICE=${3:-"auto"}

echo "=== MeloTTS 실행 ==="
echo "텍스트: $TEXT"
echo "언어: $LANGUAGE"
echo "디바이스: $DEVICE"
echo "========================"

# 가상환경 활성화 및 실행
source korean_tts_env/bin/activate
python3 korean_tts.py --text "$TEXT" --language "$LANGUAGE" --device "$DEVICE"