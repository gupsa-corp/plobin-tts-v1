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

# 시스템 패키지 (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install mecab mecab-ipadic-utf8 libmecab-dev
```

## 테스트 명령어

```bash
# 환경 테스트
source korean_tts_env/bin/activate
python3 test_korean_model.py

# GUI 실행 (간편)
./run_gui.sh

# CLI 실행 (간편)
./run_tts.sh "안녕하세요" "KR" "auto"
./run_tts.sh "Hello World" "EN" "auto"
./run_tts.sh "こんにちは" "JP" "auto"

# 직접 실행 (가상환경 필수)
source korean_tts_env/bin/activate
python3 korean_tts_gui_final.py
python3 korean_tts.py --text "안녕하세요" --language KR --device auto
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

- `korean_tts_gui_final.py`: 메인 GUI (다국어, GPU 지원)
- `korean_tts.py`: CLI 도구 (다국어, GPU 지원)
- `test_korean_model.py`: 모델 테스트
- `MeloTTS/`: TTS 라이브러리
- `models/`: 다운로드된 모델 파일들