#!/bin/bash
# 종합 테스트 실행 스크립트

set -e  # 오류 발생 시 스크립트 중단

echo "🧪 음성 대화 시스템 테스트 실행"
echo "=================================="

# 가상환경 활성화 확인
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  가상환경이 활성화되지 않았습니다. korean_tts_env 활성화 중..."
    source korean_tts_env/bin/activate
fi

# 테스트 의존성 설치
echo "📦 테스트 의존성 설치 중..."
pip install -r requirements_test.txt

# 서버 실행 상태 확인
echo "🔍 서버 상태 확인 중..."
if curl -s http://localhost:40003/api/models/status > /dev/null 2>&1; then
    echo "✅ 서버가 실행 중입니다."
    SERVER_RUNNING=true
else
    echo "⚠️  서버가 실행되지 않았습니다. 일부 통합 테스트가 건너뛸 수 있습니다."
    SERVER_RUNNING=false
fi

# 테스트 카테고리별 실행
echo ""
echo "🏃 테스트 실행 중..."

# 1. 단위 테스트 (빠른 테스트)
echo "1️⃣  단위 테스트 실행..."
pytest tests/test_model_manager.py tests/test_audio_processing.py -v -m "not slow"

# 2. API 테스트
echo "2️⃣  API 테스트 실행..."
if [ "$SERVER_RUNNING" = true ]; then
    pytest tests/test_api.py -v --tb=short
else
    echo "⏭️  서버가 실행되지 않아 API 테스트를 건너뜁니다."
fi

# 3. WebSocket 테스트
echo "3️⃣  WebSocket 테스트 실행..."
if [ "$SERVER_RUNNING" = true ]; then
    pytest tests/test_websocket.py -v --tb=short -k "not slow"
else
    echo "⏭️  서버가 실행되지 않아 WebSocket 테스트를 건너뜁니다."
fi

# 4. 통합 테스트
echo "4️⃣  통합 테스트 실행..."
if [ "$SERVER_RUNNING" = true ]; then
    pytest tests/test_integration.py -v --tb=short -m "not slow"
else
    echo "⏭️  서버가 실행되지 않아 통합 테스트를 건너뜁니다."
fi

# 5. E2E 브라우저 테스트 (선택적)
echo "5️⃣  E2E 브라우저 테스트..."
if command -v google-chrome &> /dev/null || command -v chromium-browser &> /dev/null; then
    if [ "$SERVER_RUNNING" = true ]; then
        echo "🌐 브라우저 테스트 실행 중... (Chrome/Chromium 필요)"
        pytest tests/test_e2e_browser.py -v --tb=short -k "not slow" || echo "⚠️  브라우저 테스트 실패 (일부 테스트는 GUI 환경에서만 작동)"
    else
        echo "⏭️  서버가 실행되지 않아 E2E 테스트를 건너뜁니다."
    fi
else
    echo "⏭️  Chrome/Chromium이 설치되지 않아 E2E 테스트를 건너뜁니다."
fi

echo ""
echo "📊 테스트 커버리지 생성 중..."
pytest --cov=. --cov-report=html --cov-report=term-missing tests/ -v -m "not slow and not browser" || true

echo ""
echo "✅ 테스트 완료!"
echo ""
echo "📁 결과 파일:"
echo "   - 커버리지 리포트: htmlcov/index.html"
echo "   - 테스트 로그: 터미널 출력 참조"
echo ""

if [ "$SERVER_RUNNING" = false ]; then
    echo "💡 모든 테스트를 실행하려면:"
    echo "   1. ./run_web.sh 실행 (별도 터미널)"
    echo "   2. ./run_tests.sh 재실행"
fi

echo ""
echo "🧪 추가 테스트 옵션:"
echo "   - 느린 테스트 포함: pytest -m slow"
echo "   - 병렬 실행: pytest -n auto"
echo "   - 특정 테스트: pytest tests/test_api.py::TestAPIEndpoints::test_tts_endpoint_success"