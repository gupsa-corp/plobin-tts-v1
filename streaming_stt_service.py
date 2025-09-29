#!/usr/bin/env python3
"""
실시간 STT 서비스 - Faster Whisper + VAD 기반
스트리밍 음성 인식을 위한 고성능 서비스
"""

import asyncio
import time
import tempfile
import os
from typing import Optional, Dict, Any, AsyncGenerator
from dataclasses import dataclass
from faster_whisper import WhisperModel
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AudioChunk:
    """WebM 오디오 청크 데이터 클래스"""
    data: str  # WebM 파일 경로
    sample_rate: int
    timestamp: float
    is_final: bool = False

@dataclass
class TranscriptionResult:
    """전사 결과 클래스"""
    text: str
    confidence: float
    is_final: bool
    timestamp: float
    processing_time: float

# VAD 클래스 제거 - Faster Whisper 내장 VAD 사용

class StreamingSTTService:
    """실시간 STT 서비스 클래스"""

    def __init__(self,
                 model_size: str = "base",
                 device: str = "auto",
                 compute_type: str = "int8"):
        """
        STT 서비스 초기화

        Args:
            model_size: Whisper 모델 크기 ("tiny", "base", "small", "medium", "large-v3")
            device: 디바이스 ("cpu", "cuda", "auto")
            compute_type: 계산 타입 ("int8", "float16", "float32")
        """
        self.model_size = model_size
        self.device = self._get_device(device)
        self.compute_type = compute_type

        # Faster Whisper 모델 로드
        self.model: Optional[WhisperModel] = None

        # 스트리밍 관련 설정
        self.chunk_duration = 1.0  # 초
        self.overlap_duration = 0.3  # 초 (청크 간 겹침)
        self.sample_rate = 16000
        self.min_chunk_length = 0.5  # 최소 청크 길이 (초)

        # 상태 관리
        self.is_initialized = False
        self.transcription_history = []

        # 비동기 처리를 위한 큐
        self.audio_queue = asyncio.Queue()
        self.result_queue = asyncio.Queue()

        logger.info(f"StreamingSTT 초기화: {model_size} on {self.device}")

    def _get_device(self, device: str) -> str:
        """디바이스 자동 감지"""
        if device == "auto":
            try:
                import torch
                return "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                return "cpu"
        return device

    async def initialize(self):
        """모델 비동기 초기화"""
        if self.is_initialized:
            return

        try:
            logger.info(f"Faster Whisper 모델 로딩 중... ({self.model_size})")
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            self.is_initialized = True
            logger.info("✅ Faster Whisper 모델 로드 완료")

        except Exception as e:
            logger.error(f"❌ 모델 로드 실패: {e}")
            raise

    def add_audio_chunk(self, audio_data: bytes, timestamp: float = None) -> None:
        """
        WebM 오디오 청크 추가 (동기 메소드)

        Args:
            audio_data: WebM 오디오 바이트 데이터
            timestamp: 타임스탬프
        """
        if timestamp is None:
            timestamp = time.time()

        try:
            # WebM 데이터를 임시 파일로 저장하여 Faster Whisper에 직접 전달
            with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name

            chunk = AudioChunk(
                data=temp_file_path,  # 파일 경로를 저장
                sample_rate=self.sample_rate,
                timestamp=timestamp
            )

            # 비동기 큐에 추가 (논블로킹)
            try:
                self.audio_queue.put_nowait(chunk)
            except asyncio.QueueFull:
                logger.warning("오디오 큐가 가득참 - 청크 드롭")

        except Exception as e:
            logger.error(f"WebM 오디오 청크 처리 오류: {e}")

    async def transcribe_chunk(self, audio_chunk: AudioChunk) -> Optional[TranscriptionResult]:
        """
        단일 WebM 오디오 청크 전사

        Args:
            audio_chunk: WebM 오디오 청크 (파일 경로 포함)

        Returns:
            TranscriptionResult 또는 None
        """
        if not self.is_initialized or not self.model:
            await self.initialize()

        start_time = time.time()
        webm_file_path = audio_chunk.data

        try:
            # Faster Whisper로 WebM 파일 직접 전사
            segments, info = self.model.transcribe(
                webm_file_path,
                language="ko",
                beam_size=1,  # 빠른 처리를 위해 beam_size 감소
                word_timestamps=False,
                vad_filter=True,  # Faster Whisper 내장 VAD 사용
                condition_on_previous_text=False  # 독립적인 청크 처리
            )

            # 결과 합치기
            text_parts = []
            total_confidence = 0
            segment_count = 0

            for segment in segments:
                text_parts.append(segment.text)
                # avg_logprob를 confidence로 변환 (-1~0 범위를 0~1로)
                confidence = max(0, min(1, (segment.avg_logprob + 1)))
                total_confidence += confidence
                segment_count += 1

            text = "".join(text_parts).strip()
            avg_confidence = total_confidence / max(segment_count, 1)
            processing_time = time.time() - start_time

            # 임시 WebM 파일 삭제
            try:
                import os
                os.unlink(webm_file_path)
            except Exception as cleanup_error:
                logger.warning(f"임시 파일 삭제 실패: {cleanup_error}")

            if text:
                result = TranscriptionResult(
                    text=text,
                    confidence=avg_confidence,
                    is_final=audio_chunk.is_final,
                    timestamp=audio_chunk.timestamp,
                    processing_time=processing_time
                )

                logger.debug(f"WebM 전사 완료: '{text}' (신뢰도: {avg_confidence:.3f}, "
                           f"처리시간: {processing_time:.3f}초)")

                return result

        except Exception as e:
            logger.error(f"WebM 전사 오류: {e}")
            # 오류 발생시에도 임시 파일 정리
            try:
                import os
                os.unlink(webm_file_path)
            except:
                pass

        return None

    async def process_stream(self) -> AsyncGenerator[TranscriptionResult, None]:
        """
        오디오 스트림 처리 및 결과 생성

        Yields:
            TranscriptionResult: 전사 결과
        """
        if not self.is_initialized:
            await self.initialize()

        logger.info("🎤 스트리밍 STT 시작")

        try:
            while True:
                try:
                    # 오디오 청크 대기 (타임아웃 설정)
                    chunk = await asyncio.wait_for(
                        self.audio_queue.get(),
                        timeout=5.0
                    )

                    # 전사 처리
                    result = await self.transcribe_chunk(chunk)
                    if result:
                        yield result

                except asyncio.TimeoutError:
                    # 타임아웃은 정상 동작 (새 청크 대기)
                    continue
                except Exception as e:
                    logger.error(f"스트림 처리 오류: {e}")
                    continue

        except asyncio.CancelledError:
            logger.info("스트리밍 STT 중지됨")
        except Exception as e:
            logger.error(f"스트리밍 처리 치명적 오류: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """서비스 통계 반환"""
        return {
            "model_size": self.model_size,
            "device": self.device,
            "compute_type": self.compute_type,
            "is_initialized": self.is_initialized,
            "sample_rate": self.sample_rate,
            "chunk_duration": self.chunk_duration,
            "queue_size": self.audio_queue.qsize() if hasattr(self.audio_queue, 'qsize') else 0
        }

    async def cleanup(self):
        """리소스 정리"""
        logger.info("STT 서비스 정리 중...")
        if self.model:
            del self.model
        self.model = None
        self.is_initialized = False
        logger.info("✅ STT 서비스 정리 완료")

# 전역 STT 서비스 인스턴스
streaming_stt_service = StreamingSTTService(
    model_size="base",  # base 모델로 시작 (속도와 정확도 균형)
    device="auto",
    compute_type="int8"  # 메모리 사용량 최적화
)