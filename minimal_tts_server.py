#!/usr/bin/env python3
"""
최소 TTS 서버 - 디버깅용
"""

import os
import sys
import tempfile
import traceback
import uuid
from pathlib import Path

# Add MeloTTS to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'MeloTTS'))

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="최소 TTS 디버그 서버")

# 글로벌 변수
tts_model = None

class TTSRequest(BaseModel):
    text: str
    language: str = "KR"
    speed: float = 2.0

class TTSResponse(BaseModel):
    success: bool
    audio_url: str = None
    error: str = None

@app.on_event("startup")
async def startup_event():
    global tts_model
    try:
        import torch
        from melo.api import TTS

        print("🔄 TTS 모델 로드 시작...")
        tts_model = TTS(language='KR', device='cuda' if torch.cuda.is_available() else 'cpu')
        print(f"✅ TTS 모델 로드 완료 (device: {tts_model.device})")
    except Exception as e:
        print(f"❌ TTS 모델 로드 실패: {e}")
        traceback.print_exc()

@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    global tts_model

    if tts_model is None:
        return TTSResponse(success=False, error="TTS 모델이 로드되지 않았습니다")

    try:
        print(f"🔄 TTS 요청: '{request.text}' (언어: {request.language}, 속도: {request.speed})")

        # 오디오 저장 디렉토리
        audio_dir = Path("static/audio")
        audio_dir.mkdir(parents=True, exist_ok=True)

        # 파일명 생성
        audio_filename = f"audio_{uuid.uuid4().hex}.wav"
        audio_path = audio_dir / audio_filename

        print(f"📁 출력 파일: {audio_path}")

        # 화자 ID
        speaker_ids = tts_model.hps.data.spk2id
        speaker_key = list(speaker_ids.keys())[0]
        speaker_id = speaker_ids[speaker_key]

        print(f"🎭 화자 ID: {speaker_id} ({speaker_key})")

        # 1단계: 임시 파일로 생성
        print("1️⃣ 임시 파일로 TTS 생성...")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name
            print(f"📁 임시 파일: {temp_path}")

            tts_model.tts_to_file(
                request.text,
                speaker_id,
                temp_path,
                speed=request.speed
            )

            temp_size = os.path.getsize(temp_path)
            print(f"✅ 임시 파일 생성 완료 (크기: {temp_size} bytes)")

            # 2단계: 최종 위치로 이동
            print("2️⃣ 파일 이동 중...")
            import shutil
            shutil.move(temp_path, audio_path)

            final_size = os.path.getsize(audio_path)
            print(f"✅ 파일 이동 완료 (최종 크기: {final_size} bytes)")

        audio_url = f"/static/audio/{audio_filename}"
        print(f"🎵 음성 생성 완료: {audio_url}")

        return TTSResponse(success=True, audio_url=audio_url)

    except Exception as e:
        error_msg = f"TTS 생성 오류: {str(e)}"
        print(f"❌ {error_msg}")
        traceback.print_exc()
        return TTSResponse(success=False, error=error_msg)

@app.get("/health")
async def health_check():
    return {"status": "ok", "tts_loaded": tts_model is not None}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=40004, log_level="info")