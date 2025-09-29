"""
모델 매니저 단위 테스트
"""

import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock

from models.model_manager import ModelManager

class TestModelManager:
    """모델 매니저 테스트"""

    def test_model_manager_initialization(self):
        """모델 매니저 초기화 테스트"""
        manager = ModelManager()
        assert manager is not None
        assert hasattr(manager, 'tts_available')
        assert hasattr(manager, 'stt_available')

    def test_get_status(self, mock_model_manager):
        """상태 조회 테스트"""
        status = mock_model_manager.get_status()

        assert "tts_available" in status
        assert "stt_available" in status
        assert "tts_device" in status
        assert "cuda_available" in status
        assert "stt_model_size" in status

    def test_transcribe_audio_success(self, mock_model_manager, sample_audio_file):
        """오디오 전사 성공 테스트"""
        result = mock_model_manager.transcribe_audio(sample_audio_file)

        assert "text" in result
        assert "language" in result
        assert result["text"] == "테스트 음성 인식 결과"
        assert result["language"] == "ko"

    def test_transcribe_audio_file_not_found(self, mock_model_manager):
        """존재하지 않는 파일 전사 테스트"""
        with pytest.raises(Exception):
            mock_model_manager.transcribe_audio("/nonexistent/file.wav")

    def test_synthesize_speech_success(self, mock_model_manager, temp_dir):
        """음성 합성 성공 테스트"""
        output_path = os.path.join(temp_dir, "output.wav")
        result = mock_model_manager.synthesize_speech(
            text="안녕하세요",
            output_path=output_path,
            speed=1.0,
            language="KR"
        )

        assert result == output_path
        assert os.path.exists(output_path)

    def test_synthesize_speech_empty_text(self, mock_model_manager, temp_dir):
        """빈 텍스트 음성 합성 테스트"""
        output_path = os.path.join(temp_dir, "output.wav")
        result = mock_model_manager.synthesize_speech(
            text="",
            output_path=output_path
        )

        assert result == output_path

    @patch('torch.cuda.is_available')
    def test_cuda_detection(self, mock_cuda):
        """CUDA 감지 테스트"""
        mock_cuda.return_value = True
        manager = ModelManager()
        status = manager.get_status()

        # CUDA 사용 가능 여부는 실제 환경에 따라 다를 수 있음
        assert "cuda_available" in status

    def test_model_loading_performance(self, mock_model_manager):
        """모델 로딩 성능 테스트"""
        import time

        start_time = time.time()
        status = mock_model_manager.get_status()
        end_time = time.time()

        # 상태 조회는 1초 내에 완료되어야 함
        assert end_time - start_time < 1.0
        assert status["tts_available"] is True
        assert status["stt_available"] is True

    def test_multiple_transcription_calls(self, mock_model_manager, sample_audio_file):
        """다중 전사 호출 테스트"""
        results = []
        for i in range(3):
            result = mock_model_manager.transcribe_audio(sample_audio_file)
            results.append(result)

        # 모든 결과가 일관성 있어야 함
        for result in results:
            assert result["text"] == "테스트 음성 인식 결과"
            assert result["language"] == "ko"

    def test_different_languages(self, mock_model_manager, temp_dir):
        """다양한 언어 TTS 테스트"""
        languages = ["KR", "EN", "JP", "ZH"]

        for lang in languages:
            output_path = os.path.join(temp_dir, f"output_{lang}.wav")
            result = mock_model_manager.synthesize_speech(
                text="Hello",
                output_path=output_path,
                language=lang
            )
            assert os.path.exists(result)

class TestModelManagerIntegration:
    """모델 매니저 통합 테스트"""

    @pytest.mark.slow
    def test_real_model_loading(self):
        """실제 모델 로딩 테스트 (느림)"""
        # 실제 환경에서만 실행
        if not os.getenv("INTEGRATION_TESTS"):
            pytest.skip("Integration tests disabled")

        manager = ModelManager()
        status = manager.get_status()

        # 실제 모델이 로드되어야 함
        assert status["tts_available"] is True
        assert status["stt_available"] is True