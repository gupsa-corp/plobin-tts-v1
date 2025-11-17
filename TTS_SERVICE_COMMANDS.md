# TTS 서비스 관리 명령어

## 기본 서비스 제어

### 서비스 시작
```bash
sudo systemctl start tts-server
```

### 서비스 중지
```bash
sudo systemctl stop tts-server
```

### 서비스 재시작
```bash
sudo systemctl restart tts-server
```

### 서비스 상태 확인
```bash
sudo systemctl status tts-server
```

## 로그 관리

### 실시간 로그 보기
```bash
journalctl -u tts-server -f
```

### 최근 로그 확인
```bash
journalctl -u tts-server --no-pager
```

### 특정 시간 이후 로그 확인
```bash
journalctl -u tts-server --since "1 hour ago"
```

## 부팅 관리

### 부팅 시 자동 시작 활성화 (이미 설정됨)
```bash
sudo systemctl enable tts-server
```

### 부팅 시 자동 시작 비활성화
```bash
sudo systemctl disable tts-server
```

## 서비스 파일 위치
- 서비스 파일: `/etc/systemd/system/tts-server.service`
- 작업 디렉토리: `/home/gupsa/문서/Host/40003/plobin-api-tts`

## API 테스트
```bash
# 서버 상태 확인
curl http://localhost:40003/api/models/status

# TTS 생성 테스트
curl -X POST "http://localhost:40003/api/tts" \
     -H "Content-Type: application/json" \
     -d '{"text":"안녕하세요"}' \
     --output test.wav
```

## 주의사항
- 서비스는 자동으로 재시작되도록 설정되어 있음
- 시스템 부팅 시 자동으로 시작됨
- CUDA 환경이 설정되어 있음