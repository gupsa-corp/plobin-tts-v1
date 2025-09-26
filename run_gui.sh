#!/bin/bash

# MeloTTS GUI 실행 스크립트

echo "=== MeloTTS GUI 시작 ==="
echo "다국어 지원, GPU 지원"
echo "========================"

# 가상환경 활성화 및 GUI 실행
source korean_tts_env/bin/activate
python3 korean_tts_gui_final.py