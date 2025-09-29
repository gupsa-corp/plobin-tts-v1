"""
pytest 설정 및 공통 픽스처
"""

import pytest
import asyncio
import tempfile
import os
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from fastapi import FastAPI

# 테스트용 임포트
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.settings import *
from models.model_manager import ModelManager
from websocket.connection_manager import ConnectionManager

@pytest.fixture(scope="session")
def event_loop():
    """세션 범위 이벤트 루프"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def temp_dir():
    """임시 디렉토리 생성"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_audio_file(temp_dir):
    """테스트용 샘플 오디오 파일"""
    # 간단한 WAV 파일 헤더 (무음)
    wav_header = (
        b'RIFF' + (44 + 16000).to_bytes(4, 'little') +  # 파일 크기
        b'WAVE' + b'fmt ' + (16).to_bytes(4, 'little') +  # fmt 청크
        (1).to_bytes(2, 'little') +  # PCM 포맷
        (1).to_bytes(2, 'little') +  # 모노
        (16000).to_bytes(4, 'little') +  # 샘플레이트
        (32000).to_bytes(4, 'little') +  # 바이트레이트
        (2).to_bytes(2, 'little') +  # 블록 얼라인
        (16).to_bytes(2, 'little') +  # 비트 뎁스
        b'data' + (16000).to_bytes(4, 'little')  # 데이터 청크
    )

    # 1초 무음 데이터 (16000 샘플 * 2바이트)
    silence_data = b'\x00\x00' * 8000

    audio_path = os.path.join(temp_dir, "test_audio.wav")
    with open(audio_path, "wb") as f:
        f.write(wav_header + silence_data)

    return audio_path

@pytest.fixture
def mock_model_manager():
    """목 모델 매니저"""
    class MockModelManager:
        def __init__(self):
            self.tts_available = True
            self.stt_available = True
            self.device = "cpu"

        def get_status(self):
            return {
                "tts_available": self.tts_available,
                "stt_available": self.stt_available,
                "tts_device": self.device,
                "cuda_available": False,
                "stt_model_size": "base"
            }

        def transcribe_audio(self, audio_path):
            return {
                "text": "테스트 음성 인식 결과",
                "language": "ko",
                "confidence": 0.95
            }

        def synthesize_speech(self, text, output_path, speed=1.0, language="KR"):
            # 빈 오디오 파일 생성
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(b"fake_audio_data")
            return output_path

    return MockModelManager()

@pytest.fixture
def connection_manager():
    """WebSocket 연결 매니저"""
    return ConnectionManager()

@pytest.fixture
def test_app():
    """테스트용 FastAPI 앱"""
    from web_voice_chat_new import app
    return app

@pytest.fixture
def client(test_app):
    """테스트 클라이언트"""
    return TestClient(test_app)

@pytest.fixture
def test_config():
    """테스트용 설정"""
    return {
        "SERVER_HOST": "127.0.0.1",
        "SERVER_PORT": 6001,
        "STT_LANGUAGE": "ko",
        "TTS_LANGUAGE": "KR",
        "AUDIO_SAMPLE_RATE": 16000,
        "AUDIO_CHANNELS": 1
    }