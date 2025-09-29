# Plobin TTS v1 - Korean Text-to-Speech System

한국어 텍스트를 음성으로 변환하는 고품질 TTS(Text-to-Speech) 시스템2 

## 🚀 주요 특징

- **한국어 전용 최적화**: MeloTTS 기반 고품질 한국어 음성 합성
- **실시간 처리**: CPU에서도 실시간 음성 변환 가능
- **모던 GUI**: CustomTkinter 기반 사용자 친화적 인터페이스
- **다양한 인터페이스**: CLI, GUI, API 서버 모두 지원
- **MIT 라이선스**: 상업적/비상업적 사용 모두 가능

## ⚠️ 사전 준비 사항 (중요!)

이 프로젝트는 대용량 모델 파일을 사용하므로, 사용하기 전에 **반드시** 다음 단계를 수행해야 합니다:

### 1️⃣ MeloTTS 리포지토리 클론 필요
```bash
git clone https://github.com/myshell-ai/MeloTTS.git
```

### 2️⃣ 한국어 모델 자동 다운로드
```bash
# 가상환경 생성 및 활성화
python3 -m venv korean_tts_env
source korean_tts_env/bin/activate

# 의존성 설치
pip install torch torchaudio huggingface_hub

# 한국어 모델 다운로드 (약 200MB)
python download_korean_model.py
```

### 3️⃣ 시스템 의존성 설치 (Linux/Ubuntu)
```bash
sudo apt-get update
sudo apt-get install mecab mecab-ipadic-utf8 libmecab-dev
```

## 📋 설치 가이드

### 1. 환경 설정
```bash
# 1. 이 저장소 클론
git clone https://github.com/gupsa-corp/plobin-tts-v1.git
cd plobin-tts-v1

# 2. MeloTTS 클론
git clone https://github.com/myshell-ai/MeloTTS.git

# 3. 가상환경 설정
python3 -m venv korean_tts_env
source korean_tts_env/bin/activate

# 4. 기본 의존성 설치
pip install torch torchaudio librosa transformers huggingface_hub

# 5. GUI 의존성 설치 (선택사항)
pip install customtkinter pygame

# 6. 한국어 관련 패키지 설치
pip install g2pkk jamo python-mecab-ko

# 7. 모델 다운로드
python download_korean_model.py
```

### 2. 모델 테스트
```bash
python test_korean_model.py
```

성공하면 `korean_test.wav` 파일이 생성됩니다.

## 🎯 사용법

### 🌐 웹 음성 대화 시스템 (NEW! 추천)
```bash
# 서버 시작
./run_web.sh

# 또는 직접 실행
source korean_tts_env/bin/activate
python web_voice_chat.py
```

**접속:**
- 웹 앱: http://localhost:8001
- API 문서: http://localhost:8001/docs

#### 🎤 WebSocket STT 사용법

**1. WebSocket 연결**
```javascript
const ws = new WebSocket('ws://localhost:8001/ws/stt');
```

**2. 음성 데이터 전송**
```javascript
ws.send(JSON.stringify({
    type: 'audio',
    data: audioBase64,  // Base64 인코딩된 WAV/MP3/M4A
    timestamp: new Date().toISOString()
}));
```

**3. 결과 수신**
```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'stt_result') {
        console.log('텍스트:', data.text);
        console.log('신뢰도:', data.confidence);
    }
};
```

**4. 연결 상태 확인**
```javascript
// Ping 전송
ws.send(JSON.stringify({ type: 'ping' }));

// Pong 수신 확인
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'pong') {
        console.log('연결 정상');
    }
};
```

**지원 엔드포인트:**
- `/ws/stt` - 실시간 STT 전용
- `/ws/chat` - STT + TTS + 대화 시스템

### GUI 애플리케이션
```bash
source korean_tts_env/bin/activate
python korean_tts_gui_final.py
```

**GUI 기능:**
- 텍스트 입력 및 실시간 음성 변환
- 음성 재생 및 파일 저장
- 속도 조절 (0.5x ~ 2.0x)
- 모던 다크 테마 인터페이스

### 명령행 도구
```bash
# 기본 사용법
python korean_tts.py --text "안녕하세요, 한국어 TTS 테스트입니다" --output hello.wav

# 속도 조절
python korean_tts.py --text "빠른 속도로 말하기" --speed 1.5 --output fast.wav
```

## 📁 주요 파일 설명

| 파일명 | 설명 |
|--------|------|
| `korean_tts_gui_final.py` | 🖥️ **메인 GUI 애플리케이션** |
| `korean_tts.py` | 📟 CLI 도구 |
| `korean_tts_api.py` | 🌐 FastAPI 서버 |
| `download_korean_model.py` | ⬇️ **모델 다운로드 스크립트** |
| `test_korean_model.py` | 🧪 모델 테스트 도구 |
| `start_gui.sh` | 🚀 GUI 실행 스크립트 |

## 🔧 기술 스택

- **MeloTTS**: 고품질 다국어 TTS 라이브러리
- **PyTorch**: 딥러닝 프레임워크
- **CustomTkinter**: 모던 GUI 라이브러리
- **Pygame**: 오디오 재생
- **FastAPI**: 웹 API 프레임워크
- **Hugging Face**: 모델 호스팅

## ⚡ 성능

- **모델 크기**: 198MB (한국어 모델)
- **변환 속도**: 실시간 (CPU)
- **메모리 사용**: 약 500MB
- **음질**: 고품질 자연스러운 한국어 발음

## 🛠️ 문제 해결

### MeCab 설치 오류
```bash
sudo apt-get install mecab mecab-ipadic-utf8 libmecab-dev
```

### 모델 다운로드 실패
- 인터넷 연결 확인
- 디스크 공간 확인 (최소 1GB 필요)
- Hugging Face 접근 확인

### GUI 실행 오류
```bash
pip install customtkinter pygame
```

## 📄 라이선스

MIT License - 자유로운 사용, 수정, 배포 가능

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📞 지원

- Issues: GitHub Issues 탭 활용
- 문서: 이 README 파일 참조
- 예제: `test_korean_model.py` 참조

---

**⭐ 이 프로젝트가 유용하다면 스타를 눌러주세요!**