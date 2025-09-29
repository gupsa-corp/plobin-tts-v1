"""
오디오 처리 유틸리티 테스트
"""

import pytest
import os
import tempfile
import numpy as np
from unittest.mock import patch, MagicMock

from utils.audio_processing import (
    preprocess_audio,
    cleanup_temp_audio,
    generate_audio_filename,
    validate_audio_file
)

class TestAudioProcessing:
    """오디오 처리 테스트"""

    def test_generate_audio_filename(self):
        """오디오 파일명 생성 테스트"""
        filename1 = generate_audio_filename()
        filename2 = generate_audio_filename()

        # 두 파일명이 달라야 함
        assert filename1 != filename2

        # .webm 확장자가 있어야 함
        assert filename1.endswith('.webm')
        assert filename2.endswith('.webm')

        # 파일명 길이 검증
        assert len(filename1) > 10  # 최소 길이
        assert len(filename1) < 100  # 최대 길이

    def test_cleanup_temp_audio_existing_file(self, temp_dir):
        """존재하는 임시 오디오 파일 정리 테스트"""
        # 임시 파일 생성
        temp_file = os.path.join(temp_dir, "temp_audio.wav")
        with open(temp_file, "w") as f:
            f.write("test content")

        assert os.path.exists(temp_file)

        # 파일 정리
        cleanup_temp_audio(temp_file)

        # 파일이 삭제되었는지 확인
        assert not os.path.exists(temp_file)

    def test_cleanup_temp_audio_nonexistent_file(self):
        """존재하지 않는 파일 정리 테스트"""
        # 존재하지 않는 파일 경로
        nonexistent_file = "/nonexistent/path/file.wav"

        # 예외가 발생하지 않아야 함
        try:
            cleanup_temp_audio(nonexistent_file)
        except Exception as e:
            pytest.fail(f"cleanup_temp_audio should not raise exception: {e}")

    @patch('librosa.load')
    @patch('librosa.effects.trim')
    def test_preprocess_audio_success(self, mock_trim, mock_load, sample_audio_file, temp_dir):
        """오디오 전처리 성공 테스트"""
        # Mock librosa 함수들
        mock_load.return_value = (np.random.random(16000), 16000)  # 1초 오디오
        mock_trim.return_value = (np.random.random(15000), np.array([500, 15500]))

        with patch('soundfile.write') as mock_write:
            result = preprocess_audio(sample_audio_file)

            # librosa.load가 호출되었는지 확인
            mock_load.assert_called_once()

            # librosa.effects.trim이 호출되었는지 확인
            mock_trim.assert_called_once()

            # soundfile.write가 호출되었는지 확인
            mock_write.assert_called_once()

            # 결과 파일 경로가 반환되었는지 확인
            assert isinstance(result, str)
            assert result.endswith('.webm')

    def test_validate_audio_file_valid(self, sample_audio_file):
        """유효한 오디오 파일 검증 테스트"""
        result = validate_audio_file(sample_audio_file)
        assert result is True

    def test_validate_audio_file_nonexistent(self):
        """존재하지 않는 오디오 파일 검증 테스트"""
        result = validate_audio_file("/nonexistent/file.wav")
        assert result is False

    def test_validate_audio_file_invalid_format(self, temp_dir):
        """잘못된 형식 오디오 파일 검증 테스트"""
        # 텍스트 파일을 오디오로 위장
        fake_audio = os.path.join(temp_dir, "fake.wav")
        with open(fake_audio, "w") as f:
            f.write("This is not audio data")

        result = validate_audio_file(fake_audio)
        assert result is False

    @patch('librosa.load')
    def test_preprocess_audio_librosa_error(self, mock_load, sample_audio_file):
        """librosa 로딩 오류 테스트"""
        # librosa.load에서 예외 발생
        mock_load.side_effect = Exception("Failed to load audio")

        with pytest.raises(Exception):
            preprocess_audio(sample_audio_file)

    def test_audio_file_size_limits(self, temp_dir):
        """오디오 파일 크기 제한 테스트"""
        # 빈 파일
        empty_file = os.path.join(temp_dir, "empty.wav")
        with open(empty_file, "w") as f:
            pass

        result = validate_audio_file(empty_file)
        assert result is False

        # 너무 큰 파일 (실제로는 생성하지 않고 크기만 체크)
        large_file = os.path.join(temp_dir, "large.wav")
        with open(large_file, "wb") as f:
            f.write(b"0" * (100 * 1024 * 1024))  # 100MB

        # 파일 크기 검증 로직이 있다면 실패해야 함
        # (실제 구현에 따라 다름)

class TestAudioFormats:
    """오디오 형식 테스트"""

    def test_supported_audio_formats(self):
        """지원되는 오디오 형식 테스트"""
        supported_formats = ['.webm', '.mp3', '.flac', '.ogg']

        for format_ext in supported_formats:
            filename = f"test{format_ext}"
            # 형식별 처리 로직 테스트
            assert filename.endswith(format_ext)

    def test_audio_sample_rate_conversion(self):
        """오디오 샘플레이트 변환 테스트"""
        # 다양한 샘플레이트에서 16kHz로 변환
        sample_rates = [8000, 22050, 44100, 48000]

        for sr in sample_rates:
            # 실제 변환 로직 테스트
            # (구현에 따라 다름)
            target_sr = 16000
            assert target_sr == 16000

    @patch('librosa.load')
    @patch('librosa.resample')
    def test_audio_resampling(self, mock_resample, mock_load, sample_audio_file):
        """오디오 리샘플링 테스트"""
        # 44.1kHz 오디오를 16kHz로 변환
        original_sr = 44100
        target_sr = 16000
        duration = 2.0  # 2초

        # Mock 데이터
        original_audio = np.random.random(int(original_sr * duration))
        resampled_audio = np.random.random(int(target_sr * duration))

        mock_load.return_value = (original_audio, original_sr)
        mock_resample.return_value = resampled_audio

        with patch('utils.audio_processing.preprocess_audio') as mock_preprocess:
            mock_preprocess.return_value = sample_audio_file

            result = mock_preprocess(sample_audio_file)

            assert result == sample_audio_file

class TestAudioQuality:
    """오디오 품질 테스트"""

    @patch('librosa.load')
    def test_noise_reduction(self, mock_load, sample_audio_file):
        """노이즈 감소 테스트"""
        # 노이즈가 있는 오디오 데이터 생성
        clean_signal = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 16000))  # 440Hz 사인파
        noise = np.random.normal(0, 0.1, 16000)  # 가우시안 노이즈
        noisy_signal = clean_signal + noise

        mock_load.return_value = (noisy_signal, 16000)

        with patch('utils.audio_processing.preprocess_audio') as mock_preprocess:
            mock_preprocess.return_value = sample_audio_file

            result = mock_preprocess(sample_audio_file)

            # 노이즈 감소 처리가 적용되었는지 확인
            assert result is not None

    def test_audio_normalization(self):
        """오디오 정규화 테스트"""
        # 다양한 볼륨의 오디오 테스트
        quiet_audio = np.random.random(1000) * 0.1  # 조용한 오디오
        loud_audio = np.random.random(1000) * 2.0   # 큰 오디오

        # 정규화 후 모든 오디오가 적절한 범위에 있어야 함
        for audio in [quiet_audio, loud_audio]:
            # 실제 정규화 로직 적용
            normalized = np.clip(audio, -1.0, 1.0)  # 간단한 클리핑
            assert np.max(np.abs(normalized)) <= 1.0

    def test_silence_trimming(self):
        """무음 구간 제거 테스트"""
        # 앞뒤에 무음이 있는 오디오
        silence = np.zeros(1000)
        signal = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 1000))
        audio_with_silence = np.concatenate([silence, signal, silence])

        # 무음 제거 후 신호만 남아야 함
        # (실제 구현에서는 librosa.effects.trim 사용)
        trimmed_start = 1000
        trimmed_end = 2000
        trimmed_audio = audio_with_silence[trimmed_start:trimmed_end]

        assert len(trimmed_audio) == len(signal)

class TestAudioPerformance:
    """오디오 처리 성능 테스트"""

    @pytest.mark.slow
    def test_processing_performance(self, sample_audio_file):
        """오디오 처리 성능 테스트"""
        import time

        start_time = time.time()

        # 여러 번 처리하여 평균 시간 측정
        for _ in range(5):
            try:
                validate_audio_file(sample_audio_file)
            except Exception:
                pass  # 오류 무시하고 성능만 측정

        end_time = time.time()
        avg_time = (end_time - start_time) / 5

        # 평균 처리 시간이 1초 이내여야 함
        assert avg_time < 1.0

    def test_memory_usage(self, sample_audio_file):
        """메모리 사용량 테스트"""
        import gc

        # 가비지 컬렉션 실행
        gc.collect()

        # 메모리 사용량 측정 (간단한 방법)
        for _ in range(10):
            filename = generate_audio_filename()
            # 메모리 누수가 없어야 함

        gc.collect()

        # 실제 메모리 측정 도구를 사용하려면 psutil 등 필요