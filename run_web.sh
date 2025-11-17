#!/bin/bash

echo "🚀 음성 대화 시스템 웹 서버 시작..."

# 가상환경 활성화
if [ -d "korean_tts_env" ]; then
    echo "📦 가상환경 활성화..."
    source korean_tts_env/bin/activate
else
    echo "❌ 가상환경을 찾을 수 없습니다."
    echo "다음 명령어로 가상환경을 먼저 설정하세요:"
    echo "  python3 -m venv korean_tts_env"
    echo "  source korean_tts_env/bin/activate"
    echo "  pip install -r requirements_web.txt"
    exit 1
fi

# 웹 의존성 설치 확인
echo "📋 의존성 패키지 확인..."
pip install -r requirements_web.txt

# 웹 서버 실행
echo "🌐 웹 서버 시작 (http://localhost:40003)"
echo "📖 API 문서: http://localhost:40003/docs"
echo ""
echo "종료하려면 Ctrl+C를 누르세요"
echo ""

python3 web_voice_chat.py