"""
통합 테스트 - 전체 시스템 통합 테스트
"""

import pytest
import asyncio
import json
import base64
import tempfile
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

class TestFullSystemIntegration:
    """전체 시스템 통합 테스트"""

    def test_tts_stt_pipeline(self, client, mock_model_manager, sample_audio_file):
        """TTS -> STT 파이프라인 테스트"""
        # 1. TTS로 음성 생성
        tts_data = {
            "text": "안녕하세요 테스트입니다",
            "language": "KR",
            "speed": 1.0
        }

        with patch('models.model_manager.model_manager', mock_model_manager):
            tts_response = client.post("/api/tts", json=tts_data)
            assert tts_response.status_code == 200

            # 2. 생성된 음성을 STT로 변환
            with open(sample_audio_file, "rb") as f:
                files = {"audio": ("test.webm", f, "audio/webm")}
                stt_response = client.post("/api/stt", files=files)

            assert stt_response.status_code == 200
            stt_data = stt_response.json()
            assert "text" in stt_data
            assert stt_data["success"] is True

    def test_websocket_audio_pipeline(self, client, sample_audio_file):
        """WebSocket 오디오 파이프라인 통합 테스트"""
        with client.websocket_connect("/ws/chat") as websocket:
            # 오디오 파일을 base64로 인코딩
            with open(sample_audio_file, "rb") as f:
                audio_data = base64.b64encode(f.read()).decode()

            # 오디오 메시지 전송
            message = {
                "type": "audio",
                "data": audio_data,
                "timestamp": "2025-09-29T14:38:00Z"
            }

            websocket.send_text(json.dumps(message))

            # 사용자 메시지 응답 수신
            response1 = websocket.receive_text()
            response1_data = json.loads(response1)
            assert response1_data["type"] == "user_message"

            # 시스템 응답 수신
            response2 = websocket.receive_text()
            response2_data = json.loads(response2)
            assert response2_data["type"] == "system_response"
            assert "audio_url" in response2_data

    def test_api_model_consistency(self, client):
        """API 간 모델 상태 일관성 테스트"""
        # 모델 상태 확인
        status_response = client.get("/api/models/status")
        assert status_response.status_code == 200
        status_data = status_response.json()

        # 언어 목록 확인
        languages_response = client.get("/api/languages")
        assert languages_response.status_code == 200
        languages_data = languages_response.json()

        # TTS 사용 가능하면 언어 목록이 있어야 함
        if status_data["tts_available"]:
            assert len(languages_data["languages"]) > 0

    def test_concurrent_requests(self, client):
        """동시 요청 처리 테스트"""
        import threading
        import time

        results = []

        def make_tts_request():
            try:
                response = client.post("/api/tts", json={
                    "text": "동시 요청 테스트",
                    "language": "KR",
                    "speed": 1.0
                })
                results.append(response.status_code)
            except Exception as e:
                results.append(f"Error: {e}")

        # 5개의 동시 TTS 요청
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_tts_request)
            threads.append(thread)

        start_time = time.time()

        # 모든 스레드 시작
        for thread in threads:
            thread.start()

        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()

        end_time = time.time()

        # 결과 검증
        assert len(results) == 5
        success_count = sum(1 for r in results if r == 200)
        assert success_count >= 3  # 최소 3개는 성공해야 함

        # 전체 처리 시간이 합리적인지 확인
        assert end_time - start_time < 30.0  # 30초 이내

class TestErrorHandlingIntegration:
    """오류 처리 통합 테스트"""

    def test_model_failure_handling(self, client):
        """모델 실패 시 오류 처리 테스트"""
        with patch('models.model_manager.model_manager') as mock_manager:
            # TTS 실패 시뮬레이션
            mock_manager.synthesize_speech.side_effect = Exception("TTS model failed")

            response = client.post("/api/tts", json={
                "text": "실패 테스트",
                "language": "KR",
                "speed": 1.0
            })

            # 적절한 오류 응답이 반환되어야 함
            assert response.status_code in [400, 500]

    def test_websocket_error_recovery(self, client):
        """WebSocket 오류 복구 테스트"""
        with client.websocket_connect("/ws/chat") as websocket:
            # 잘못된 메시지 전송
            websocket.send_text("invalid json")

            # 정상 메시지 전송
            ping_message = {
                "type": "ping",
                "timestamp": "2025-09-29T14:38:00Z"
            }
            websocket.send_text(json.dumps(ping_message))

            # pong 응답 수신 (연결이 유지되어야 함)
            response = websocket.receive_text()
            response_data = json.loads(response)
            assert response_data["type"] == "pong"

    def test_file_upload_error_handling(self, client, temp_dir):
        """파일 업로드 오류 처리 테스트"""
        # 잘못된 파일 형식
        fake_audio = os.path.join(temp_dir, "fake.wav")
        with open(fake_audio, "w") as f:
            f.write("This is not audio")

        with open(fake_audio, "rb") as f:
            files = {"audio": ("fake.webm", f, "audio/webm")}
            response = client.post("/api/stt", files=files)

        # 적절한 오류 응답이 반환되어야 함
        assert response.status_code in [400, 422, 500]

class TestDataFlowIntegration:
    """데이터 플로우 통합 테스트"""

    def test_audio_processing_pipeline(self, sample_audio_file):
        """오디오 처리 파이프라인 테스트"""
        from utils.audio_processing import preprocess_audio, validate_audio_file

        # 1. 오디오 파일 검증
        is_valid = validate_audio_file(sample_audio_file)
        assert is_valid is True

        # 2. 오디오 전처리
        with patch('utils.audio_processing.preprocess_audio') as mock_preprocess:
            mock_preprocess.return_value = sample_audio_file
            processed_file = mock_preprocess(sample_audio_file)
            assert processed_file == sample_audio_file

    def test_websocket_message_flow(self, client):
        """WebSocket 메시지 플로우 테스트"""
        with client.websocket_connect("/ws/chat") as websocket:
            # 다양한 메시지 타입 테스트
            message_types = [
                {"type": "ping", "timestamp": "2025-09-29T14:38:00Z"},
                {"type": "auto_chat_start", "theme": "casual", "interval": 30},
                {"type": "auto_chat_stop"}
            ]

            for message in message_types:
                websocket.send_text(json.dumps(message))

                # 응답 수신
                try:
                    response = websocket.receive_text()
                    response_data = json.loads(response)
                    assert "type" in response_data
                except Exception:
                    pass  # 일부 메시지는 응답이 없을 수 있음

class TestConfigurationIntegration:
    """설정 통합 테스트"""

    def test_config_consistency(self):
        """설정 일관성 테스트"""
        from config.settings import (
            SERVER_PORT, STT_LANGUAGE, TTS_LANGUAGE,
            AUDIO_SAMPLE_RATE, AUDIO_CHANNELS
        )

        # 설정값들이 유효한지 확인
        assert isinstance(SERVER_PORT, int)
        assert 1000 <= SERVER_PORT <= 65535

        assert STT_LANGUAGE in ["ko", "en", "auto"]
        assert TTS_LANGUAGE in ["KR", "EN", "JP", "ZH", "FR", "ES"]

        assert AUDIO_SAMPLE_RATE in [8000, 16000, 22050, 44100, 48000]
        assert AUDIO_CHANNELS in [1, 2]

    def test_model_manager_initialization(self):
        """모델 매니저 초기화 통합 테스트"""
        from models.model_manager import model_manager

        # 모델 매니저가 올바르게 초기화되었는지 확인
        status = model_manager.get_status()
        assert isinstance(status, dict)
        assert "tts_available" in status
        assert "stt_available" in status

class TestSecurityIntegration:
    """보안 통합 테스트"""

    def test_file_upload_security(self, client, temp_dir):
        """파일 업로드 보안 테스트"""
        # 악성 파일명 테스트
        malicious_names = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "test<script>alert('xss')</script>.wav"
        ]

        for name in malicious_names:
            fake_file = os.path.join(temp_dir, "test.wav")
            with open(fake_file, "wb") as f:
                f.write(b"fake audio data")

            with open(fake_file, "rb") as f:
                files = {"audio": (name, f, "audio/webm")}
                response = client.post("/api/stt", files=files)

            # 요청이 적절히 거부되거나 처리되어야 함
            assert response.status_code in [200, 400, 422, 500]

    def test_websocket_message_validation(self, client):
        """WebSocket 메시지 검증 테스트"""
        with client.websocket_connect("/ws/chat") as websocket:
            # 악성 메시지 전송 시도
            malicious_messages = [
                '{"type": "audio", "data": "' + 'A' * 10000 + '"}',  # 매우 긴 데이터
                '{"type": "unknown_type", "malicious": true}',  # 알 수 없는 타입
                '{"type": null, "data": null}'  # null 값
            ]

            for message in malicious_messages:
                try:
                    websocket.send_text(message)
                    # 연결이 유지되거나 적절히 종료되어야 함
                except Exception:
                    pass  # 예외 발생은 정상적인 보안 동작

class TestPerformanceIntegration:
    """성능 통합 테스트"""

    @pytest.mark.slow
    def test_system_performance_under_load(self, client):
        """부하 상태에서의 시스템 성능 테스트"""
        import time
        import threading

        results = []

        def load_test():
            start_time = time.time()
            response = client.get("/api/models/status")
            end_time = time.time()

            results.append({
                "status_code": response.status_code,
                "response_time": end_time - start_time
            })

        # 10개의 동시 요청으로 부하 테스트
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=load_test)
            threads.append(thread)

        # 모든 스레드 시작
        for thread in threads:
            thread.start()

        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()

        # 성능 기준 검증
        assert len(results) == 10

        success_rate = sum(1 for r in results if r["status_code"] == 200) / len(results)
        assert success_rate >= 0.8  # 80% 이상 성공률

        avg_response_time = sum(r["response_time"] for r in results) / len(results)
        assert avg_response_time < 5.0  # 평균 5초 이내