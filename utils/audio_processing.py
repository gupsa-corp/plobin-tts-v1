#!/usr/bin/env python3
"""
오디오 전처리 유틸리티 모듈
"""

import os
import numpy as np
from config.settings import (
    AUDIO_SAMPLE_RATE,
    AUDIO_TRIM_TOP_DB,
    AUDIO_NOISE_GATE_THRESHOLD,
    AUDIO_VOLUME_NORMALIZE
)

try:
    import librosa
    import soundfile as sf
    AUDIO_PROCESSING_AVAILABLE = True
except ImportError:
    AUDIO_PROCESSING_AVAILABLE = False

def preprocess_audio(audio_path: str) -> str:
    """오디오 전처리: 노이즈 제거 및 정규화"""
    try:
        if not AUDIO_PROCESSING_AVAILABLE:
            return audio_path

        # librosa로 오디오 로드 (자동 샘플링 레이트 변환)
        y, sr = librosa.load(audio_path, sr=AUDIO_SAMPLE_RATE, mono=True)

        # 음성이 너무 짧으면 패딩
        if len(y) < sr * 0.1:  # 0.1초 미만
            return audio_path

        # 무음 구간 제거 (앞뒤)
        y_trimmed, _ = librosa.effects.trim(y, top_db=AUDIO_TRIM_TOP_DB)

        # 음성이 없는 경우 원본 반환
        if len(y_trimmed) == 0:
            return audio_path

        # 볼륨 정규화
        if np.max(np.abs(y_trimmed)) > 0:
            y_normalized = y_trimmed / np.max(np.abs(y_trimmed)) * AUDIO_VOLUME_NORMALIZE
        else:
            y_normalized = y_trimmed

        # 간단한 노이즈 게이트 (매우 작은 소리 제거)
        threshold = np.max(np.abs(y_normalized)) * AUDIO_NOISE_GATE_THRESHOLD
        y_cleaned = np.where(np.abs(y_normalized) < threshold, 0, y_normalized)

        # 전처리된 오디오를 임시 파일로 저장
        processed_path = audio_path.replace('.wav', '_processed.wav')
        sf.write(processed_path, y_cleaned, sr)

        return processed_path

    except Exception as e:
        print(f"오디오 전처리 오류: {e}")
        return audio_path  # 전처리 실패시 원본 반환


def cleanup_temp_audio(audio_path: str):
    """임시 오디오 파일 정리"""
    try:
        if os.path.exists(audio_path):
            os.unlink(audio_path)

        # 전처리된 파일도 정리
        processed_path = audio_path.replace('.wav', '_processed.wav')
        if os.path.exists(processed_path):
            os.unlink(processed_path)
    except Exception as e:
        print(f"임시 파일 정리 오류: {e}")


def generate_audio_filename() -> str:
    """고유한 오디오 파일명 생성"""
    import uuid
    return f"audio_{uuid.uuid4().hex}.wav"