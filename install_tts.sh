#!/bin/bash

# TTS 서비스 최초 설치 스크립트
# 작성일: 2024-11-17
# 목적: TTS 서비스 안정적 최초 설치

set -e  # 오류 발생 시 즉시 종료

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수들
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 오류 처리 함수
cleanup_on_error() {
    log_error "설치 중 오류가 발생했습니다. 정리 작업을 수행합니다..."

    # 실행 중인 TTS 프로세스 종료
    pkill -f "tts_only_server.py" 2>/dev/null || true

    # 포트 40003 사용 중인 프로세스 종료
    local pid=$(lsof -ti:40003 2>/dev/null || true)
    if [ ! -z "$pid" ]; then
        log_warning "포트 40003을 사용 중인 프로세스 $pid를 종료합니다"
        kill $pid 2>/dev/null || true
        sleep 2
        kill -9 $pid 2>/dev/null || true
    fi
}

# 오류 발생 시 cleanup 함수 실행
trap cleanup_on_error ERR

# 시스템 요구사항 검증
check_requirements() {
    log_info "시스템 요구사항을 확인합니다..."

    # Python 3.9+ 확인
    if ! command -v python3 &> /dev/null; then
        log_error "Python3가 설치되지 않았습니다. Python 3.9 이상을 설치해주세요."
        exit 1
    fi

    local python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    log_info "Python 버전: $python_version"

    # Git 확인
    if ! command -v git &> /dev/null; then
        log_error "Git이 설치되지 않았습니다."
        exit 1
    fi

    # CUDA 확인 (선택사항)
    if command -v nvidia-smi &> /dev/null; then
        log_success "NVIDIA GPU 감지됨 - CUDA 가속 사용 가능"
        nvidia-smi --query-gpu=name --format=csv,noheader | head -1 | xargs -I {} log_info "GPU: {}"
    else
        log_warning "NVIDIA GPU가 감지되지 않음 - CPU 모드로 실행됩니다"
    fi

    # 디스크 공간 확인 (최소 15GB 필요)
    local available_space=$(df . | tail -1 | awk '{print $4}')
    local required_space=$((15 * 1024 * 1024))  # 15GB in KB

    if [ $available_space -lt $required_space ]; then
        log_error "디스크 공간이 부족합니다. 최소 15GB가 필요합니다."
        exit 1
    fi

    log_success "시스템 요구사항 확인 완료"
}

# 기존 설치 확인 및 정리
check_existing_installation() {
    log_info "기존 설치를 확인합니다..."

    # 실행 중인 TTS 서비스 확인
    local pid=$(pgrep -f "tts_only_server.py" || true)
    if [ ! -z "$pid" ]; then
        log_warning "실행 중인 TTS 서비스를 종료합니다 (PID: $pid)"
        kill $pid 2>/dev/null || true
        sleep 3
        kill -9 $pid 2>/dev/null || true
    fi

    # 포트 40003 사용 중인 프로세스 확인
    local port_pid=$(lsof -ti:40003 2>/dev/null || true)
    if [ ! -z "$port_pid" ]; then
        log_warning "포트 40003을 사용 중인 프로세스를 종료합니다 (PID: $port_pid)"
        kill $port_pid 2>/dev/null || true
        sleep 2
    fi

    # 기존 가상환경 확인
    if [ -d "korean_tts_env" ]; then
        log_warning "기존 가상환경이 발견되었습니다. 삭제하고 새로 생성합니다."
        rm -rf korean_tts_env
    fi
}

# 시스템 의존성 설치
install_system_dependencies() {
    log_info "시스템 의존성을 설치합니다..."

    # Ubuntu/Debian 계열 확인
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y \
            python3-venv \
            python3-dev \
            build-essential \
            git \
            curl \
            wget \
            ffmpeg \
            libsndfile1 \
            libsndfile1-dev \
            libasound2-dev \
            libportaudio2 \
            libportaudiocpp0 \
            portaudio19-dev

        log_success "시스템 의존성 설치 완료"
    else
        log_warning "apt-get을 사용할 수 없습니다. 수동으로 의존성을 확인해주세요."
    fi
}

# MeloTTS 클론
clone_melotts() {
    log_info "MeloTTS를 클론합니다..."

    if [ ! -d "MeloTTS" ]; then
        git clone https://github.com/myshell-ai/MeloTTS.git
        log_success "MeloTTS 클론 완료"
    else
        log_info "MeloTTS가 이미 존재합니다. 스킵합니다."
    fi
}

# Python 가상환경 생성
create_virtual_environment() {
    log_info "Python 가상환경을 생성합니다..."

    python3 -m venv korean_tts_env
    source korean_tts_env/bin/activate

    # pip 업그레이드
    log_info "pip를 업그레이드합니다..."
    pip install --upgrade pip setuptools wheel

    log_success "가상환경 생성 완료"
}

# Python 패키지 설치
install_python_packages() {
    log_info "Python 패키지를 설치합니다. 시간이 오래 걸릴 수 있습니다..."

    source korean_tts_env/bin/activate

    # PyTorch 설치 (CUDA 버전)
    log_info "PyTorch를 설치합니다..."
    if command -v nvidia-smi &> /dev/null; then
        # CUDA 사용 가능한 경우
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    else
        # CPU 버전
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
    fi

    # 웹 서버 관련 패키지
    log_info "웹 서버 패키지를 설치합니다..."
    pip install fastapi>=0.104.0 uvicorn[standard]>=0.24.0

    # 오디오 처리 패키지
    log_info "오디오 처리 패키지를 설치합니다..."
    pip install soundfile pydub librosa

    # 한국어 처리 패키지
    log_info "한국어 처리 패키지를 설치합니다..."
    pip install g2pkk jamo python-mecab-ko

    # 기타 필요 패키지
    log_info "기타 필요한 패키지를 설치합니다..."
    pip install transformers huggingface_hub websockets pydantic protobuf

    # MeloTTS 설치
    log_info "MeloTTS 패키지를 설치합니다..."
    cd MeloTTS
    pip install -e .
    cd ..

    log_success "Python 패키지 설치 완료"
}

# 한국어 모델 다운로드
download_korean_models() {
    log_info "한국어 TTS 모델을 다운로드합니다..."

    source korean_tts_env/bin/activate

    # 모델 다운로드 스크립트 실행
    if [ -f "download_korean_model.py" ]; then
        python download_korean_model.py
        log_success "한국어 모델 다운로드 완료"
    else
        log_warning "download_korean_model.py가 없습니다. 수동으로 모델을 다운로드해주세요."
    fi
}

# 디렉토리 구조 생성
create_directories() {
    log_info "필요한 디렉토리를 생성합니다..."

    mkdir -p static/audio
    mkdir -p static/css
    mkdir -p static/js
    mkdir -p trouble

    # 권한 설정
    chmod 755 static
    chmod 755 static/audio
    chmod 755 trouble

    log_success "디렉토리 구조 생성 완료"
}

# 설치 테스트
test_installation() {
    log_info "설치를 테스트합니다..."

    source korean_tts_env/bin/activate

    # TTS 모델 로드 테스트
    python3 -c "
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'MeloTTS'))

try:
    import torch
    from melo.api import TTS

    print('🔄 TTS 모델 로드 테스트 시작...')
    tts_model = TTS(language='KR', device='cuda' if torch.cuda.is_available() else 'cpu')
    print(f'✅ TTS 모델 로드 성공 (device: {tts_model.device})')
    print('✅ 설치 테스트 통과!')

except Exception as e:
    print(f'❌ 설치 테스트 실패: {e}')
    sys.exit(1)
"

    if [ $? -eq 0 ]; then
        log_success "설치 테스트 통과!"
    else
        log_error "설치 테스트 실패!"
        exit 1
    fi
}

# 서비스 시작 스크립트 생성
create_service_scripts() {
    log_info "서비스 시작 스크립트를 생성합니다..."

    # 시작 스크립트
    cat > start_tts.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source korean_tts_env/bin/activate
python tts_only_server.py
EOF
    chmod +x start_tts.sh

    # 중지 스크립트
    cat > stop_tts.sh << 'EOF'
#!/bin/bash
echo "TTS 서비스를 중지합니다..."
pkill -f "tts_only_server.py" 2>/dev/null || true
echo "TTS 서비스가 중지되었습니다."
EOF
    chmod +x stop_tts.sh

    # 상태 확인 스크립트
    cat > status_tts.sh << 'EOF'
#!/bin/bash
if pgrep -f "tts_only_server.py" > /dev/null; then
    echo "✅ TTS 서비스가 실행 중입니다."
    echo "포트: 40003"
    echo "웹 인터페이스: http://localhost:40003"
    echo "API 문서: http://localhost:40003/docs"
else
    echo "❌ TTS 서비스가 실행되지 않고 있습니다."
fi
EOF
    chmod +x status_tts.sh

    log_success "서비스 스크립트 생성 완료"
}

# 메인 설치 함수
main() {
    echo "================================================"
    echo "🎵 TTS 서비스 자동 설치 스크립트"
    echo "================================================"
    echo ""

    local start_time=$(date +%s)

    check_requirements
    check_existing_installation
    install_system_dependencies
    clone_melotts
    create_virtual_environment
    install_python_packages
    download_korean_models
    create_directories
    test_installation
    create_service_scripts

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    echo ""
    echo "================================================"
    log_success "🎉 TTS 서비스 설치가 완료되었습니다!"
    echo "================================================"
    echo ""
    echo "⏱️  설치 소요 시간: ${duration}초"
    echo ""
    echo "🚀 서비스 시작: ./start_tts.sh"
    echo "⏹️  서비스 중지: ./stop_tts.sh"
    echo "📊 서비스 상태: ./status_tts.sh"
    echo ""
    echo "🌐 웹 인터페이스: http://localhost:40003"
    echo "📖 API 문서: http://localhost:40003/docs"
    echo ""
    echo "💡 서비스를 시작하려면 다음 명령을 실행하세요:"
    echo "   ./start_tts.sh"
    echo ""
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi