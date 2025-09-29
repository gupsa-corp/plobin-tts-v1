"""
API 엔드포인트 테스트
"""

import pytest
import json
import base64
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

class TestAPIEndpoints:
    """API 엔드포인트 테스트"""

    def test_root_endpoint(self, client):
        """루트 엔드포인트 테스트"""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_models_status_endpoint(self, client):
        """모델 상태 API 테스트"""
        response = client.get("/api/models/status")
        assert response.status_code == 200

        data = response.json()
        required_fields = [
            "tts_available", "stt_available", "tts_device",
            "cuda_available", "stt_model_size"
        ]

        for field in required_fields:
            assert field in data

    def test_languages_endpoint(self, client):
        """지원 언어 목록 API 테스트"""
        response = client.get("/api/languages")
        assert response.status_code == 200

        data = response.json()
        assert "languages" in data
        assert isinstance(data["languages"], list)
        assert len(data["languages"]) > 0

        # 한국어가 포함되어 있는지 확인
        language_codes = [lang["code"] for lang in data["languages"]]
        assert "KR" in language_codes

    @patch('models.model_manager.model_manager')
    def test_tts_endpoint_success(self, mock_manager, client, temp_dir):
        """TTS API 성공 테스트"""
        # TTS 결과 모킹
        output_file = os.path.join(temp_dir, "test_output.wav")
        with open(output_file, "wb") as f:
            f.write(b"fake_audio_data")

        mock_manager.synthesize_speech.return_value = output_file

        tts_data = {
            "text": "안녕하세요",
            "language": "KR",
            "speed": 1.0
        }

        response = client.post("/api/tts", json=tts_data)
        assert response.status_code == 200

        data = response.json()
        assert "audio_url" in data
        assert "filename" in data
        assert data["success"] is True

    def test_tts_endpoint_empty_text(self, client):
        """TTS API 빈 텍스트 테스트"""
        tts_data = {
            "text": "",
            "language": "KR",
            "speed": 1.0
        }

        response = client.post("/api/tts", json=tts_data)
        assert response.status_code == 400

    def test_tts_endpoint_invalid_language(self, client):
        """TTS API 잘못된 언어 테스트"""
        tts_data = {
            "text": "Hello",
            "language": "INVALID",
            "speed": 1.0
        }

        response = client.post("/api/tts", json=tts_data)
        # 언어 검증에 따라 400 또는 500 응답
        assert response.status_code in [400, 500]

    @patch('models.model_manager.model_manager')
    def test_stt_endpoint_success(self, mock_manager, client, sample_audio_file):
        """STT API 성공 테스트"""
        # STT 결과 모킹
        mock_manager.transcribe_audio.return_value = {
            "text": "테스트 음성 인식 결과",
            "language": "ko",
            "confidence": 0.95
        }

        with open(sample_audio_file, "rb") as f:
            files = {"audio": ("test.webm", f, "audio/webm")}
            response = client.post("/api/stt", files=files)

        assert response.status_code == 200

        data = response.json()
        assert "text" in data
        assert "language" in data
        assert data["success"] is True
        assert data["text"] == "테스트 음성 인식 결과"

    def test_stt_endpoint_no_file(self, client):
        """STT API 파일 없음 테스트"""
        response = client.post("/api/stt")
        assert response.status_code == 422  # Unprocessable Entity

    def test_stt_endpoint_invalid_file(self, client):
        """STT API 잘못된 파일 테스트"""
        files = {"audio": ("test.txt", b"not audio data", "text/plain")}
        response = client.post("/api/stt", files=files)
        assert response.status_code in [400, 500]

    def test_health_check(self, client):
        """헬스 체크 테스트"""
        response = client.get("/health")
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] == "healthy"
        else:
            # 헬스 체크 엔드포인트가 없을 수 있음
            assert response.status_code == 404

    def test_static_files(self, client):
        """정적 파일 서빙 테스트"""
        # CSS 파일 테스트
        response = client.get("/static/css/style.css")
        assert response.status_code == 200
        assert "text/css" in response.headers.get("content-type", "")

        # JS 파일 테스트
        response = client.get("/static/js/voice-chat.js")
        assert response.status_code == 200
        assert "javascript" in response.headers.get("content-type", "")

    def test_docs_endpoint(self, client):
        """API 문서 엔드포인트 테스트"""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_endpoint(self, client):
        """ReDoc 엔드포인트 테스트"""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

class TestAPIValidation:
    """API 입력 검증 테스트"""

    def test_tts_parameter_validation(self, client):
        """TTS 매개변수 검증 테스트"""
        # 필수 필드 누락
        response = client.post("/api/tts", json={})
        assert response.status_code == 422

        # 잘못된 속도 값
        tts_data = {
            "text": "Hello",
            "language": "KR",
            "speed": -1.0  # 음수 속도
        }
        response = client.post("/api/tts", json=tts_data)
        assert response.status_code == 422

        # 너무 긴 텍스트
        tts_data = {
            "text": "A" * 10000,  # 매우 긴 텍스트
            "language": "KR",
            "speed": 1.0
        }
        response = client.post("/api/tts", json=tts_data)
        # 길이 제한에 따라 400 또는 422 응답
        assert response.status_code in [400, 422]

    def test_file_upload_limits(self, client):
        """파일 업로드 제한 테스트"""
        # 너무 큰 파일 (10MB)
        large_data = b"0" * (10 * 1024 * 1024)
        files = {"audio": ("large.webm", large_data, "audio/webm")}

        response = client.post("/api/stt", files=files)
        # 파일 크기 제한에 따라 413 또는 400 응답
        assert response.status_code in [413, 400, 422]

class TestAPIPerformance:
    """API 성능 테스트"""

    def test_concurrent_requests(self, client):
        """동시 요청 처리 테스트"""
        import threading
        import time

        results = []

        def make_request():
            start_time = time.time()
            response = client.get("/api/models/status")
            end_time = time.time()
            results.append({
                "status_code": response.status_code,
                "response_time": end_time - start_time
            })

        # 5개의 동시 요청
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)

        # 모든 스레드 시작
        for thread in threads:
            thread.start()

        # 모든 스레드 완료 대기
        for thread in threads:
            thread.join()

        # 결과 검증
        assert len(results) == 5
        for result in results:
            assert result["status_code"] == 200
            assert result["response_time"] < 5.0  # 5초 이내

    @pytest.mark.slow
    def test_api_response_time(self, client):
        """API 응답 시간 테스트"""
        import time

        endpoints = [
            "/api/models/status",
            "/api/languages",
            "/"
        ]

        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()

            assert response.status_code == 200
            assert end_time - start_time < 2.0  # 2초 이내

class TestAPIErrors:
    """API 오류 처리 테스트"""

    def test_404_handling(self, client):
        """404 오류 처리 테스트"""
        response = client.get("/nonexistent/endpoint")
        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """허용되지 않은 HTTP 메서드 테스트"""
        response = client.delete("/api/models/status")
        assert response.status_code == 405

    def test_invalid_json(self, client):
        """잘못된 JSON 요청 테스트"""
        response = client.post(
            "/api/tts",
            data="invalid json",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 422