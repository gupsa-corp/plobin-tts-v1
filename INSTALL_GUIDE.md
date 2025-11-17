# 🎵 TTS 서비스 설치 가이드

## 🚀 최초 설치 (권장)

### 1. 자동 설치 스크립트 실행
```bash
# 스크립트 권한 부여 (이미 되어 있음)
chmod +x install_tts.sh

# 설치 실행
./install_tts.sh
```

이 스크립트는 다음 작업을 자동으로 수행합니다:
- ✅ 시스템 요구사항 확인
- ✅ 필요한 시스템 패키지 설치
- ✅ Python 가상환경 생성
- ✅ MeloTTS 및 관련 패키지 설치
- ✅ 한국어 모델 다운로드
- ✅ 설치 테스트
- ✅ 서비스 관리 스크립트 생성

### 2. 서비스 시작
```bash
./start_tts.sh
```

### 3. 서비스 확인
- 🌐 웹 인터페이스: http://localhost:40003
- 📖 API 문서: http://localhost:40003/docs

---

## 🐳 Docker로 설치 (대안)

### 1. Docker Compose 실행
```bash
docker compose up -d
```

### 2. 로그 확인
```bash
docker compose logs -f
```

### 3. 중지
```bash
docker compose down
```

---

## 📋 서비스 관리 명령어

### 서비스 시작
```bash
./start_tts.sh
```

### 서비스 중지
```bash
./stop_tts.sh
```

### 서비스 상태 확인
```bash
./status_tts.sh
```

### 포트 확인
```bash
lsof -i :40003
```

---

## 🔧 문제 해결

### 1. 설치 실패 시
```bash
# 정리 후 재설치
rm -rf korean_tts_env
./install_tts.sh
```

### 2. 모델 로드 오류 시
```bash
# 가상환경 활성화
source korean_tts_env/bin/activate

# 모델 재다운로드
python download_korean_model.py
```

### 3. CUDA 오류 시
```bash
# CUDA 상태 확인
nvidia-smi

# CPU 모드로 강제 실행
CUDA_VISIBLE_DEVICES="" ./start_tts.sh
```

### 4. 포트 충돌 시
```bash
# 포트 사용 중인 프로세스 확인
lsof -i :40003

# 프로세스 종료
sudo kill -9 <PID>
```

---

## 📊 시스템 요구사항

### 최소 요구사항
- **OS**: Ubuntu 20.04+ (또는 호환 Linux)
- **Python**: 3.9+
- **RAM**: 8GB+
- **디스크**: 15GB+ 여유공간
- **CPU**: 4코어+

### 권장 사양
- **OS**: Ubuntu 22.04+
- **Python**: 3.10+
- **RAM**: 16GB+
- **디스크**: 50GB+ SSD
- **GPU**: NVIDIA GPU (CUDA 지원)

---

## 🧪 테스트

### API 테스트
```bash
curl -X POST "http://localhost:40003/api/tts" \
  -H "Content-Type: application/json" \
  -d '{"text": "안녕하세요, TTS 테스트입니다", "language": "KR"}'
```

### 웹 인터페이스 테스트
브라우저에서 http://localhost:40003 접속하여 텍스트 입력 후 음성 생성 테스트

---

## 📝 로그 확인

### 서비스 로그
```bash
# 실시간 로그 확인 (서비스 실행 중)
tail -f /var/log/tts_service.log  # 로그 파일이 있는 경우

# 또는 직접 실행하여 로그 확인
source korean_tts_env/bin/activate
python tts_only_server.py
```

### 문제 발생 시 스크린샷 위치
- `trouble/` 디렉토리에 타임스탬프별로 저장됩니다.

---

## 🔄 업데이트

### 코드 업데이트
```bash
git pull origin main
./stop_tts.sh
./start_tts.sh
```

### 패키지 업데이트
```bash
source korean_tts_env/bin/activate
pip install --upgrade -r requirements.txt
```

---

## 💡 팁

1. **초기 실행 시 시간이 오래 걸립니다** - 모델 다운로드 때문입니다.
2. **CUDA 메모리 부족 시** - `CUDA_VISIBLE_DEVICES=""` 로 CPU 모드 실행하세요.
3. **안정성을 위해** - 정기적으로 서비스를 재시작하는 것을 권장합니다.
4. **백업** - `models/` 디렉토리를 백업해두면 재설치 시 빠릅니다.