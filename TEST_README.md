# 🧪 음성 대화 시스템 테스트 가이드

전체 시스템에 대한 종합적인 테스트 스위트입니다.

## 📁 테스트 구조

```
tests/
├── __init__.py              # 테스트 패키지
├── conftest.py              # pytest 설정 및 공통 픽스처
├── test_model_manager.py    # 모델 매니저 단위 테스트
├── test_websocket.py        # WebSocket 핸들러 통합 테스트
├── test_api.py              # API 엔드포인트 테스트
├── test_audio_processing.py # 오디오 처리 유틸리티 테스트
├── test_e2e_browser.py      # E2E 브라우저 자동화 테스트
└── test_integration.py      # 시스템 통합 테스트
```

## 🚀 빠른 시작

### 1. 테스트 의존성 설치

```bash
# 가상환경 활성화
source korean_tts_env/bin/activate

# 테스트 패키지 설치
pip install -r requirements_test.txt
```

### 2. 서버 실행 (통합 테스트용)

```bash
# 별도 터미널에서 실행
./run_web.sh
```

### 3. 테스트 실행

```bash
# 전체 테스트 실행 (권장)
./run_tests.sh

# 또는 pytest 직접 실행
pytest tests/ -v
```

## 📋 테스트 카테고리

### 🔧 단위 테스트 (Unit Tests)
- **모델 매니저**: TTS/STT 모델 로딩, 상태 관리
- **오디오 처리**: 파일 검증, 전처리, 노이즈 제거
- **유틸리티**: 파일명 생성, 정리 함수

```bash
pytest tests/test_model_manager.py tests/test_audio_processing.py -v
```

### 🔗 통합 테스트 (Integration Tests)
- **WebSocket 핸들러**: 실시간 대화, 연결 관리
- **API 엔드포인트**: TTS/STT API, 상태 확인
- **시스템 통합**: 전체 파이프라인, 데이터 플로우

```bash
pytest tests/test_websocket.py tests/test_api.py tests/test_integration.py -v
```

### 🌐 E2E 테스트 (End-to-End Tests)
- **브라우저 자동화**: Selenium 기반 UI 테스트
- **마이크 권한**: getUserMedia API 테스트
- **WebSocket 연결**: 실시간 통신 테스트

```bash
pytest tests/test_e2e_browser.py -v
```

## 🏷️ 테스트 마커

pytest 마커를 사용하여 특정 테스트 그룹 실행:

```bash
# 빠른 테스트만 (slow 제외)
pytest -m "not slow"

# 통합 테스트만
pytest -m integration

# 브라우저 테스트 제외
pytest -m "not browser"

# 성능 테스트만
pytest -m performance
```

## 📊 테스트 커버리지

```bash
# 커버리지 포함 테스트 실행
pytest --cov=. --cov-report=html --cov-report=term

# HTML 리포트 확인
open htmlcov/index.html
```

## 🔧 테스트 환경 설정

### 환경 변수

```bash
# 통합 테스트 활성화
export INTEGRATION_TESTS=1

# 테스트 서버 URL (기본값: http://localhost:6001)
export TEST_SERVER_URL=http://localhost:6001
```

### Chrome/Chromium 설치 (E2E 테스트용)

```bash
# Ubuntu/Debian
sudo apt-get install google-chrome-stable

# 또는 Chromium
sudo apt-get install chromium-browser
```

## 🐛 테스트 문제 해결

### 자주 발생하는 문제

1. **서버 연결 실패**
   ```bash
   # 서버 실행 확인
   curl http://localhost:6001/api/models/status

   # 서버 재시작
   ./run_web.sh
   ```

2. **브라우저 테스트 실패**
   ```bash
   # Chrome WebDriver 확인
   which google-chrome

   # 헤드리스 모드로 테스트
   pytest tests/test_e2e_browser.py --headless
   ```

3. **의존성 충돌**
   ```bash
   # 가상환경 재생성
   deactivate
   rm -rf korean_tts_env
   python3 -m venv korean_tts_env
   source korean_tts_env/bin/activate
   pip install -r requirements_web.txt
   pip install -r requirements_test.txt
   ```

### 로그 및 디버깅

```bash
# 상세 로그와 함께 실행
pytest tests/ -v --tb=long --capture=no

# 특정 테스트만 디버그
pytest tests/test_api.py::TestAPIEndpoints::test_tts_endpoint_success -v -s

# 실패한 테스트만 재실행
pytest --lf -v
```

## 📈 성능 테스트

```bash
# 성능 테스트 실행
pytest -m performance -v

# 부하 테스트
pytest tests/test_integration.py::TestPerformanceIntegration -v

# 메모리 프로파일링
pytest --profile -v
```

## 🔄 CI/CD 통합

### GitHub Actions 예시

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: |
          pip install -r requirements_web.txt
          pip install -r requirements_test.txt
      - name: Run tests
        run: pytest tests/ -v --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

## 📝 테스트 작성 가이드

### 새로운 테스트 추가

1. **적절한 테스트 파일 선택**
   - 단위 테스트: `test_<module_name>.py`
   - 통합 테스트: `test_integration.py`
   - E2E 테스트: `test_e2e_browser.py`

2. **테스트 클래스 구조**
   ```python
   class TestFeatureName:
       def test_success_case(self):
           # 성공 케이스

       def test_error_case(self):
           # 오류 케이스

       def test_edge_case(self):
           # 경계 케이스
   ```

3. **픽스처 활용**
   ```python
   def test_with_fixture(self, mock_model_manager, sample_audio_file):
       # conftest.py의 픽스처 사용
   ```

## 🎯 테스트 목표

- **코드 커버리지**: 80% 이상
- **API 응답 시간**: 2초 이내
- **E2E 테스트**: 주요 사용자 시나리오 커버
- **오류 처리**: 모든 예외 상황 테스트
- **성능**: 동시 요청 10개 처리 가능

## 📞 도움말

테스트 관련 문제가 있으면:

1. **로그 확인**: `pytest -v --tb=long`
2. **의존성 확인**: `pip list | grep pytest`
3. **서버 상태 확인**: `curl http://localhost:6001/api/models/status`
4. **브라우저 확인**: `google-chrome --version`

## 🔗 관련 문서

- [pytest 공식 문서](https://docs.pytest.org/)
- [FastAPI 테스트 가이드](https://fastapi.tiangolo.com/tutorial/testing/)
- [Selenium 문서](https://selenium-python.readthedocs.io/)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)