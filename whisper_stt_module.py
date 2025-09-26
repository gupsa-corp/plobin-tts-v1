"""
Whisper STT Module for Real-time Speech-to-Text
OpenAI Whisper 모델을 사용한 실시간 음성 인식 모듈
"""

import os
import sys
import tempfile
import warnings
import numpy as np
import io
import wave
import threading
import queue
import time
from typing import Optional, Generator, Dict, Any

warnings.filterwarnings("ignore")

try:
    import whisper
    import torch
except ImportError as e:
    print(f"Whisper dependencies not found: {e}")
    raise ImportError("whisper and torch are required for STT functionality")


class WhisperSTT:
    """
    Whisper 기반 실시간 음성-텍스트 변환 클래스
    """

    def __init__(self, model_name: str = "base", device: str = "auto", language: str = "auto"):
        """
        WhisperSTT 초기화

        Args:
            model_name (str): Whisper 모델 크기 ("tiny", "base", "small", "medium", "large")
            device (str): 사용할 디바이스 ("cpu", "cuda", "auto")
            language (str): 언어 코드 ("ko", "en", "auto" 등)
        """
        self.model_name = model_name
        self.device = self._setup_device(device)
        self.language = language if language != "auto" else None

        # 모델 로딩
        self.model = None
        self.load_model()

        # 오디오 설정
        self.sample_rate = 16000  # Whisper 기본 샘플레이트
        self.chunk_duration = 1.0  # 초 단위
        self.min_audio_length = 1.0  # 최소 오디오 길이 (초)

        # 버퍼 및 상태 관리
        self.audio_buffer = []
        self.is_recording = False
        self.processing_thread = None
        self.result_queue = queue.Queue()

    def _setup_device(self, device: str) -> str:
        """
        사용할 디바이스 설정

        Args:
            device (str): 디바이스 설정

        Returns:
            str: 실제 사용할 디바이스
        """
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            else:
                return "cpu"
        return device

    def load_model(self):
        """
        Whisper 모델 로딩
        """
        try:
            print(f"Loading Whisper model '{self.model_name}' on {self.device}...")
            self.model = whisper.load_model(self.model_name, device=self.device)
            print(f"✓ Whisper model loaded successfully!")
        except Exception as e:
            print(f"✗ Failed to load Whisper model: {e}")
            raise e

    def transcribe_audio(self, audio_data: np.ndarray, language: Optional[str] = None) -> Dict[str, Any]:
        """
        오디오 데이터를 텍스트로 변환

        Args:
            audio_data (np.ndarray): 오디오 데이터 (16kHz, float32)
            language (str, optional): 언어 코드

        Returns:
            Dict[str, Any]: 변환 결과
        """
        if self.model is None:
            raise RuntimeError("Whisper model not loaded")

        try:
            # 언어 설정
            transcribe_language = language or self.language

            # Whisper 변환 옵션
            options = {
                "language": transcribe_language,
                "task": "transcribe",
                "fp16": self.device == "cuda",  # GPU에서는 fp16 사용
            }

            # 변환 실행
            result = self.model.transcribe(audio_data, **options)

            return {
                "text": result["text"].strip(),
                "language": result.get("language", "unknown"),
                "segments": result.get("segments", []),
                "confidence": self._calculate_confidence(result.get("segments", []))
            }

        except Exception as e:
            print(f"Transcription error: {e}")
            return {
                "text": "",
                "language": "unknown",
                "segments": [],
                "confidence": 0.0,
                "error": str(e)
            }

    def _calculate_confidence(self, segments: list) -> float:
        """
        세그먼트들의 평균 신뢰도 계산

        Args:
            segments (list): Whisper 결과 세그먼트들

        Returns:
            float: 평균 신뢰도 (0.0-1.0)
        """
        if not segments:
            return 0.0

        total_confidence = 0.0
        segment_count = 0

        for segment in segments:
            if "confidence" in segment:
                total_confidence += segment["confidence"]
                segment_count += 1
            elif "avg_logprob" in segment:
                # avg_logprob을 confidence로 변환 (근사치)
                confidence = max(0.0, min(1.0, (segment["avg_logprob"] + 1.0) / 2.0))
                total_confidence += confidence
                segment_count += 1

        return total_confidence / segment_count if segment_count > 0 else 0.0

    def transcribe_file(self, file_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        오디오 파일을 텍스트로 변환

        Args:
            file_path (str): 오디오 파일 경로
            language (str, optional): 언어 코드

        Returns:
            Dict[str, Any]: 변환 결과
        """
        try:
            # 오디오 파일 로드
            audio_data = whisper.load_audio(file_path)
            return self.transcribe_audio(audio_data, language)

        except Exception as e:
            print(f"File transcription error: {e}")
            return {
                "text": "",
                "language": "unknown",
                "segments": [],
                "confidence": 0.0,
                "error": str(e)
            }

    def transcribe_wav_bytes(self, wav_bytes: bytes, language: Optional[str] = None) -> Dict[str, Any]:
        """
        WAV 바이트 데이터를 텍스트로 변환

        Args:
            wav_bytes (bytes): WAV 형식의 오디오 바이트
            language (str, optional): 언어 코드

        Returns:
            Dict[str, Any]: 변환 결과
        """
        try:
            # 임시 파일에 저장
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(wav_bytes)
                temp_path = temp_file.name

            # 변환 실행
            result = self.transcribe_file(temp_path, language)

            # 임시 파일 삭제
            os.unlink(temp_path)

            return result

        except Exception as e:
            print(f"WAV bytes transcription error: {e}")
            return {
                "text": "",
                "language": "unknown",
                "segments": [],
                "confidence": 0.0,
                "error": str(e)
            }

    def start_streaming_transcription(self) -> Generator[Dict[str, Any], None, None]:
        """
        스트리밍 음성 인식 시작

        Yields:
            Dict[str, Any]: 실시간 변환 결과
        """
        self.is_recording = True
        self.audio_buffer = []

        try:
            while self.is_recording:
                # 결과 큐에서 변환 결과 확인
                try:
                    result = self.result_queue.get(timeout=0.1)
                    yield result
                except queue.Empty:
                    continue

        except Exception as e:
            print(f"Streaming transcription error: {e}")
            yield {
                "text": "",
                "language": "unknown",
                "segments": [],
                "confidence": 0.0,
                "error": str(e)
            }
        finally:
            self.stop_streaming_transcription()

    def add_audio_chunk(self, audio_chunk: bytes):
        """
        실시간 스트리밍을 위한 오디오 청크 추가

        Args:
            audio_chunk (bytes): 오디오 청크 (16-bit PCM)
        """
        if not self.is_recording:
            return

        # 오디오 청크를 버퍼에 추가
        audio_array = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
        self.audio_buffer.extend(audio_array)

        # 충분한 오디오가 모이면 처리
        min_samples = int(self.min_audio_length * self.sample_rate)
        if len(self.audio_buffer) >= min_samples:
            self._process_audio_buffer()

    def _process_audio_buffer(self):
        """
        오디오 버퍼 처리 (백그라운드에서 실행)
        """
        if len(self.audio_buffer) == 0:
            return

        # 버퍼 복사 및 초기화
        audio_data = np.array(self.audio_buffer, dtype=np.float32)
        self.audio_buffer = []

        # 백그라운드에서 변환 실행
        def transcribe_worker():
            try:
                result = self.transcribe_audio(audio_data)
                if result["text"]:  # 텍스트가 있는 경우만 결과 전송
                    self.result_queue.put(result)
            except Exception as e:
                self.result_queue.put({
                    "text": "",
                    "language": "unknown",
                    "segments": [],
                    "confidence": 0.0,
                    "error": str(e)
                })

        thread = threading.Thread(target=transcribe_worker)
        thread.daemon = True
        thread.start()

    def stop_streaming_transcription(self):
        """
        스트리밍 음성 인식 중지
        """
        self.is_recording = False

        # 남은 오디오 버퍼 처리
        if self.audio_buffer:
            self._process_audio_buffer()

        # 결과 큐 비우기
        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except queue.Empty:
                break

    def get_supported_languages(self) -> list:
        """
        지원하는 언어 목록 반환

        Returns:
            list: 지원 언어 코드 목록
        """
        return [
            "ko",  # 한국어
            "en",  # 영어
            "ja",  # 일본어
            "zh",  # 중국어
            "fr",  # 프랑스어
            "es",  # 스페인어
            "de",  # 독일어
            "it",  # 이탈리아어
            "pt",  # 포르투갈어
            "ru",  # 러시아어
            "ar",  # 아랍어
            "hi",  # 힌디어
            "auto"  # 자동 감지
        ]

    def get_model_info(self) -> Dict[str, Any]:
        """
        모델 정보 반환

        Returns:
            Dict[str, Any]: 모델 정보
        """
        return {
            "model_name": self.model_name,
            "device": self.device,
            "language": self.language or "auto",
            "sample_rate": self.sample_rate,
            "supported_languages": self.get_supported_languages(),
            "model_loaded": self.model is not None
        }


class AudioProcessor:
    """
    오디오 전처리 유틸리티 클래스
    """

    @staticmethod
    def wav_bytes_to_array(wav_bytes: bytes, target_sr: int = 16000) -> np.ndarray:
        """
        WAV 바이트를 numpy 배열로 변환

        Args:
            wav_bytes (bytes): WAV 파일 바이트
            target_sr (int): 목표 샘플레이트

        Returns:
            np.ndarray: 오디오 배열
        """
        try:
            with io.BytesIO(wav_bytes) as wav_io:
                with wave.open(wav_io, 'rb') as wav_file:
                    # WAV 파일 정보
                    sample_rate = wav_file.getframerate()
                    n_channels = wav_file.getnchannels()
                    sample_width = wav_file.getsampwidth()

                    # 오디오 데이터 읽기
                    frames = wav_file.readframes(-1)

                    # numpy 배열로 변환
                    if sample_width == 2:  # 16-bit
                        audio_data = np.frombuffer(frames, dtype=np.int16)
                    elif sample_width == 4:  # 32-bit
                        audio_data = np.frombuffer(frames, dtype=np.int32)
                    else:
                        raise ValueError(f"Unsupported sample width: {sample_width}")

                    # float32로 정규화
                    if sample_width == 2:
                        audio_data = audio_data.astype(np.float32) / 32768.0
                    elif sample_width == 4:
                        audio_data = audio_data.astype(np.float32) / 2147483648.0

                    # 스테레오를 모노로 변환
                    if n_channels == 2:
                        audio_data = audio_data.reshape(-1, 2).mean(axis=1)

                    # 리샘플링 (필요한 경우)
                    if sample_rate != target_sr:
                        # 간단한 리샘플링 (librosa가 없는 경우)
                        audio_data = AudioProcessor._resample_simple(audio_data, sample_rate, target_sr)

                    return audio_data

        except Exception as e:
            print(f"WAV conversion error: {e}")
            return np.array([], dtype=np.float32)

    @staticmethod
    def _resample_simple(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """
        간단한 리샘플링 (librosa 없이)

        Args:
            audio (np.ndarray): 원본 오디오
            orig_sr (int): 원본 샘플레이트
            target_sr (int): 목표 샘플레이트

        Returns:
            np.ndarray: 리샘플링된 오디오
        """
        if orig_sr == target_sr:
            return audio

        # 간단한 선형 보간을 사용한 리샘플링
        duration = len(audio) / orig_sr
        target_length = int(duration * target_sr)

        indices = np.linspace(0, len(audio) - 1, target_length)
        return np.interp(indices, np.arange(len(audio)), audio)


# 편의성을 위한 함수들
def create_whisper_stt(model_name: str = "base", device: str = "auto", language: str = "auto") -> WhisperSTT:
    """
    WhisperSTT 인스턴스 생성

    Args:
        model_name (str): 모델 크기
        device (str): 디바이스
        language (str): 언어

    Returns:
        WhisperSTT: STT 인스턴스
    """
    return WhisperSTT(model_name=model_name, device=device, language=language)


def transcribe_audio_file(file_path: str, model_name: str = "base", language: str = "auto") -> str:
    """
    오디오 파일을 텍스트로 변환하는 편의 함수

    Args:
        file_path (str): 오디오 파일 경로
        model_name (str): Whisper 모델 크기
        language (str): 언어 코드

    Returns:
        str: 변환된 텍스트
    """
    stt = create_whisper_stt(model_name, "auto", language)
    result = stt.transcribe_file(file_path, language)
    return result.get("text", "")