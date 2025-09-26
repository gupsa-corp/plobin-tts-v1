#!/usr/bin/env python3
"""
Korean TTS API Server using FastAPI
간단한 웹 API 서버로 한국어 TTS 기능 제공
"""

import os
import sys
import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# Add MeloTTS to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'MeloTTS'))

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse
    from pydantic import BaseModel
    from melo.api import TTS
except ImportError as e:
    print(f"필요한 패키지가 설치되지 않았습니다: {e}")
    print("다음 명령어로 설치하세요:")
    print("pip install fastapi uvicorn")
    sys.exit(1)

# FastAPI 앱 생성
app = FastAPI(title="Korean TTS API", version="1.0.0")

# 전역 TTS 모델
tts_model = None

class TTSRequest(BaseModel):
    text: str
    speaker_id: int = 0
    speed: float = 1.0

@app.on_event("startup")
async def startup_event():
    """서버 시작시 TTS 모델 로드"""
    global tts_model
    try:
        print("한국어 TTS 모델 로딩 중...")
        tts_model = TTS(language='KR', device='cpu')
        print("✓ TTS 모델 로드 완료!")
    except Exception as e:
        print(f"✗ TTS 모델 로드 실패: {e}")
        raise e

@app.get("/")
async def root():
    """기본 엔드포인트"""
    return {"message": "Korean TTS API Server", "status": "running"}

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    """텍스트를 음성으로 변환"""
    if not tts_model:
        raise HTTPException(status_code=500, detail="TTS 모델이 로드되지 않았습니다")

    try:
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name

        # TTS 수행
        tts_model.tts_to_file(
            text=request.text,
            speaker_id=request.speaker_id,
            output_path=temp_path,
            speed=request.speed,
            quiet=True
        )

        return FileResponse(
            path=temp_path,
            media_type="audio/wav",
            filename=f"tts_output.wav"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS 처리 실패: {str(e)}")

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "model_loaded": tts_model is not None
    }

if __name__ == "__main__":
    import uvicorn
    print("Korean TTS API 서버 시작...")
    print("사용법:")
    print("  POST /tts - 텍스트를 음성으로 변환")
    print("  GET /health - 서버 상태 확인")
    print("  GET / - 기본 정보")
    print("\n서버 주소: http://localhost:6001")

    uvicorn.run(app, host="0.0.0.0", port=6001)