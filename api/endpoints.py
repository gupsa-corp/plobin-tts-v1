#!/usr/bin/env python3
"""
REST API 엔드포인트 모듈
"""

import os
import tempfile
import time
from typing import Optional
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from models.model_manager import model_manager
from utils.audio_processing import generate_audio_filename, cleanup_temp_audio
from config.settings import AUDIO_DIR

# 요청/응답 모델
class TTSRequest(BaseModel):
    text: str
    language: str = "KR"
    speed: float = 1.0
    device: str = "auto"

class TTSResponse(BaseModel):
    success: bool
    audio_url: Optional[str] = None
    error: Optional[str] = None

class STTResponse(BaseModel):
    success: bool
    text: Optional[str] = None
    language: Optional[str] = None
    confidence: Optional[float] = None
    processing_time: Optional[float] = None
    error: Optional[str] = None

class BatchTTSRequest(BaseModel):
    texts: list[str]
    language: str = "KR"
    speaker_id: int = 0
    speed: float = 1.0
    format: str = "zip"

    class Config:
        schema_extra = {
            "example": {
                "texts": [
                    "첫 번째 텍스트입니다.",
                    "두 번째 텍스트입니다.",
                    "세 번째 텍스트입니다."
                ],
                "language": "KR",
                "speaker_id": 0,
                "speed": 1.0,
                "format": "zip"
            }
        }

class HealthResponse(BaseModel):
    status: str
    tts_available: bool
    stt_available: bool
    model_info: dict
    server_info: dict

# API 라우터 생성
router = APIRouter(prefix="/api", tags=["음성 처리"])

@router.post("/tts", response_model=TTSResponse,
             summary="텍스트를 음성으로 변환",
             description="입력된 텍스트를 음성 파일로 변환합니다.")
async def text_to_speech(request: TTSRequest):
    """텍스트를 음성으로 변환"""
    try:
        # 오디오 파일 경로 생성
        audio_filename = generate_audio_filename()
        audio_path = os.path.join(AUDIO_DIR, audio_filename)

        # TTS 변환
        model_manager.synthesize_speech(
            text=request.text,
            output_path=audio_path,
            language=request.language,
            speed=request.speed
        )

        return TTSResponse(
            success=True,
            audio_url=f"/static/audio/{audio_filename}"
        )

    except Exception as e:
        return TTSResponse(
            success=False,
            error=str(e)
        )

@router.post("/stt", response_model=STTResponse,
             summary="음성을 텍스트로 변환",
             description="업로드된 음성 파일을 텍스트로 변환합니다.")
async def speech_to_text(audio_file: UploadFile = File(...)):
    """음성을 텍스트로 변환"""
    try:
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            content = await audio_file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        start_time = time.time()

        # STT 변환
        result = model_manager.transcribe_audio(temp_path)
        processing_time = time.time() - start_time

        # 신뢰도 계산
        confidence = 0.0
        if "segments" in result and result["segments"]:
            confidence = sum(seg.get("avg_logprob", 0) for seg in result["segments"]) / len(result["segments"])
            confidence = max(0, min(1, (confidence + 1) / 2))

        # 임시 파일 정리
        cleanup_temp_audio(temp_path)

        return STTResponse(
            success=True,
            text=result["text"].strip(),
            language=result.get("language", "unknown"),
            confidence=round(confidence, 3),
            processing_time=round(processing_time, 2)
        )

    except Exception as e:
        return STTResponse(
            success=False,
            error=str(e)
        )

@router.get("/models/status",
            summary="모델 상태 확인",
            description="TTS와 STT 모델의 로드 상태를 확인합니다.")
async def get_models_status():
    """모델 상태 확인"""
    return model_manager.get_status()

@router.get("/languages",
            summary="지원 언어 목록",
            description="TTS에서 지원하는 언어 목록을 반환합니다.")
async def get_supported_languages():
    """지원 언어 목록"""
    return {
        "languages": [
            {"code": "KR", "name": "한국어"},
            {"code": "EN", "name": "영어 (v1)"},
            {"code": "EN_V2", "name": "영어 (v2)"},
            {"code": "EN_NEWEST", "name": "영어 (v3)"},
            {"code": "ZH", "name": "중국어"},
            {"code": "JP", "name": "일본어"},
            {"code": "FR", "name": "프랑스어"},
            {"code": "ES", "name": "스페인어"}
        ]
    }

@router.post("/batch-tts",
             summary="여러 텍스트 일괄 음성 변환",
             description="대량의 텍스트를 효율적으로 음성 파일로 변환하고 ZIP으로 패키징합니다.")
async def batch_text_to_speech(request: BatchTTSRequest):
    """여러 텍스트를 일괄적으로 음성으로 변환"""
    if not request.texts:
        raise HTTPException(status_code=400, detail="변환할 텍스트가 제공되지 않았습니다")

    if len(request.texts) > 50:
        raise HTTPException(status_code=400, detail="한 번에 최대 50개의 텍스트만 처리 가능합니다")

    try:
        import tempfile
        import zipfile
        import os

        audio_files = []
        temp_dir = tempfile.mkdtemp()

        try:
            # 각 텍스트를 TTS 처리
            for i, text in enumerate(request.texts):
                if not text.strip():
                    continue

                # 파일명 생성
                filename = f"tts_output_{i:03d}.wav"
                file_path = os.path.join(temp_dir, filename)

                # TTS 변환
                model_manager.synthesize_speech(
                    text=text.strip(),
                    output_path=file_path,
                    language=request.language,
                    speed=request.speed
                )

                audio_files.append((filename, file_path))

            if not audio_files:
                raise HTTPException(status_code=400, detail="변환 가능한 텍스트가 없습니다")

            # ZIP 파일로 압축
            if request.format == "zip":
                zip_path = os.path.join(temp_dir, "batch_tts_output.zip")
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for filename, file_path in audio_files:
                        zipf.write(file_path, filename)

                return FileResponse(
                    path=zip_path,
                    media_type="application/zip",
                    filename="batch_tts_output.zip"
                )
            else:
                # 개별 파일 처리 (첫 번째 파일만 반환)
                if audio_files:
                    filename, file_path = audio_files[0]
                    return FileResponse(
                        path=file_path,
                        media_type="audio/wav",
                        filename=filename
                    )

        finally:
            # 백그라운드에서 임시 파일 정리
            import threading
            def cleanup_temp_files():
                try:
                    import shutil
                    import time
                    time.sleep(60)  # 1분 후 정리
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                except:
                    pass

            cleanup_thread = threading.Thread(target=cleanup_temp_files)
            cleanup_thread.daemon = True
            cleanup_thread.start()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"배치 TTS 처리 실패: {str(e)}")

@router.get("/health", response_model=HealthResponse,
            summary="서버 및 모델 상태 확인",
            description="실시간 시스템 상태와 STT/TTS 모델의 준비 상태를 확인합니다.")
async def health_check():
    """서버 상태 및 AI 모델 로딩 상태 종합 확인"""
    try:
        import psutil
        import os

        # 시스템 정보 수집
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_info = psutil.virtual_memory()

            server_info = {
                "cpu_usage": f"{cpu_percent}%",
                "memory_usage": f"{memory_info.percent}%",
                "memory_available": f"{memory_info.available // (1024**3)}GB",
                "process_id": os.getpid()
            }
        except:
            server_info = {
                "process_id": os.getpid(),
                "note": "시스템 정보 수집 제한"
            }

        # 모델 상태 확인
        model_status = model_manager.get_status()

        return HealthResponse(
            status="healthy" if (model_status["tts_available"] and model_status["stt_available"]) else "degraded",
            tts_available=model_status["tts_available"],
            stt_available=model_status["stt_available"],
            model_info={
                "tts_device": model_status["tts_device"],
                "stt_model_size": model_status["stt_model_size"],
                "cuda_available": model_status["cuda_available"]
            },
            server_info=server_info
        )

    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            tts_available=False,
            stt_available=False,
            model_info={"error": str(e)},
            server_info={"error": "상태 수집 실패"}
        )