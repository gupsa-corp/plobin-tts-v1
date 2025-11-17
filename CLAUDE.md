# CLAUDE.md - 개발 환경 설정

## 필수 패키지 설치 명령어

```bash
# 가상환경 활성화
source korean_tts_env/bin/activate

# 필수 의존성 패키지
pip install torch torchaudio librosa transformers huggingface_hub
pip install g2pkk jamo python-mecab-ko
pip install protobuf

# GUI 및 오디오 관련 패키지
pip install customtkinter pygame

# 웹 서버 및 STT 패키지 (음성 대화 시스템용)
pip install -r requirements_web.txt

# 시스템 패키지 (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install mecab mecab-ipadic-utf8 libmecab-dev
```

## 실행 명령어

```bash
# 환경 테스트
source korean_tts_env/bin/activate
python3 test_korean_model.py

# 🌐 웹 음성 대화 시스템 (NEW!) - 추천
./run_web.sh
# 접속: http://localhost:40003
# API 문서: http://localhost:40003/docs

# GUI 실행 (데스크톱)
./run_gui.sh

# CLI 실행
./run_tts.sh "안녕하세요" "KR" "auto"
./run_tts.sh "Hello World" "EN" "auto"
./run_tts.sh "こんにちは" "JP" "auto"

# 직접 실행 (가상환경 필수)
source korean_tts_env/bin/activate
python3 web_voice_chat.py     # 웹 서버
python3 korean_tts_gui_final.py  # GUI
python3 korean_tts.py --text "안녕하세요" --language KR --device auto  # CLI
```

## GPU 지원

- **GPU 사용**: `device=cuda` (기본값, 권장)
- **자동 감지**: `device=auto`
- **CPU 강제**: `device=cpu`

**10GB VRAM 최적화 지원**: 자동 VRAM 정리 및 사용량 모니터링
GPU 사용 시 실시간 대화 수준의 빠른 음성 변환 가능

## 린트/타입체크 명령어

```bash
# 현재 프로젝트에는 별도 린트/타입체크 설정 없음
# 필요시 추가 설정
```

## 지원 언어

- **KR**: 한국어
- **EN**: 영어 (v1)
- **EN_V2**: 영어 (v2)
- **EN_NEWEST**: 영어 (v3, 최신)
- **ZH**: 중국어
- **JP**: 일본어
- **FR**: 프랑스어
- **ES**: 스페인어

## 프로젝트 구조

### 🌐 웹 음성 대화 시스템 (NEW!)
- `web_voice_chat.py`: FastAPI 웹 서버 (STT + TTS + WebSocket)
- `templates/index.html`: 웹 UI
- `static/css/style.css`: 웹 스타일
- `static/js/voice-chat.js`: 실시간 음성 대화 JavaScript
- `requirements_web.txt`: 웹 서버 의존성
- `run_web.sh`: 웹 서버 실행 스크립트

### 기존 시스템
- `korean_tts_gui_final.py`: 데스크톱 GUI (다국어, GPU 지원)
- `korean_tts.py`: CLI 도구 (다국어, GPU 지원)
- `test_korean_model.py`: 모델 테스트
- `MeloTTS/`: TTS 라이브러리
- `models/`: 다운로드된 모델 파일들

## 웹 시스템 주요 기능

### 🎤 실시간 음성 대화
- **STT**: Whisper 기반 음성 인식
- **TTS**: MeloTTS 기반 음성 합성
- **WebSocket**: 실시간 양방향 통신
- **Web Audio API**: 브라우저 마이크 접근

### 🛠️ API 엔드포인트
- `/api/tts`: 텍스트 → 음성 변환
- `/api/stt`: 음성 → 텍스트 변환
- `/api/models/status`: 모델 상태 확인
- `/api/languages`: 지원 언어 목록
- `/ws/chat`: WebSocket 실시간 대화
- `/docs`: Swagger API 문서 (자동 생성)
- `/redoc`: ReDoc API 문서

### 💡 사용법
1. `./run_web.sh` 실행
2. http://localhost:40003 접속
3. 마이크 권한 허용
4. 🎤 녹음 버튼 클릭하거나 스페이스바로 음성 입력
5. 실시간 음성 대화 즐기기!