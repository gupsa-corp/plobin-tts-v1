#!/usr/bin/env python3
"""
TTS 전용 서버
Text-to-Speech만 지원하는 간소화된 서버
"""

import os
import sys
import tempfile
import warnings
import json
import uuid
import time
from pathlib import Path
from typing import Optional

warnings.filterwarnings("ignore")

# Add MeloTTS to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'MeloTTS'))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# TTS 관련 임포트
try:
    import torch
    from melo.api import TTS
    TTS_AVAILABLE = True
    print("✅ TTS 모듈 임포트 성공")
except ImportError as e:
    TTS_AVAILABLE = False
    print(f"❌ TTS 모듈 임포트 실패: {e}")

# FastAPI 앱 생성
app = FastAPI(
    title="TTS 전용 API",
    description="Text-to-Speech 전용 서버",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 정적 파일 서빙
app.mount("/static", StaticFiles(directory="static"), name="static")

# 전역 변수
tts_model = None

# 요청/응답 모델
class TTSRequest(BaseModel):
    text: str
    language: str = "KR"
    speed: float = 2.0

class TTSResponse(BaseModel):
    success: bool
    audio_url: Optional[str] = None
    error: Optional[str] = None

class ModelStatusResponse(BaseModel):
    tts_available: bool
    tts_device: Optional[str] = None
    cuda_available: bool

async def initialize_tts():
    """TTS 모델 초기화"""
    global tts_model

    if TTS_AVAILABLE:
        try:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            print(f"🔄 TTS 모델 로드 시작 (device: {device})")
            tts_model = TTS(language="KR", device=device)
            print(f"✅ TTS 모델 로드 완료 (device: {device})")
            return True
        except Exception as e:
            print(f"❌ TTS 모델 로드 실패: {e}")
            return False
    else:
        print("❌ TTS 모듈을 사용할 수 없습니다")
        return False

@app.on_event("startup")
async def startup_event():
    """서버 시작시 모델 초기화"""
    success = await initialize_tts()
    if success:
        print("🎉 TTS 서버가 성공적으로 시작되었습니다!")
    else:
        print("⚠️ TTS 모델 로드에 실패했지만 서버는 시작됩니다.")

@app.get("/", response_class=HTMLResponse)
async def read_index():
    """메인 페이지"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TTS 전용 서버</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .container { text-align: center; }
            h1 { color: #2c3e50; }
            .form-group { margin: 20px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, textarea, select, button { padding: 10px; margin: 5px; border: 1px solid #ddd; border-radius: 5px; }
            textarea { width: 100%; min-height: 100px; resize: vertical; }
            button { background-color: #3498db; color: white; cursor: pointer; font-size: 16px; }
            button:hover { background-color: #2980b9; }
            .status { margin: 20px 0; padding: 10px; border-radius: 5px; }
            .success { background-color: #d4edda; color: #155724; }
            .error { background-color: #f8d7da; color: #721c24; }
            audio { width: 100%; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎤 TTS 전용 서버</h1>
            <p>텍스트를 음성으로 변환하는 서비스입니다.</p>

            <div class="form-group">
                <label for="text">변환할 텍스트:</label>
                <textarea id="text" placeholder="여기에 텍스트를 입력하세요...">안녕하세요! TTS 테스트입니다.</textarea>
            </div>

            <div class="form-group">
                <label for="language">언어:</label>
                <select id="language">
                    <option value="KR">한국어</option>
                    <option value="EN">영어</option>
                </select>
            </div>

            <div class="form-group">
                <button onclick="convertTextToSpeech()">🎵 음성 생성</button>
            </div>

            <div id="status"></div>
            <div id="audio-player"></div>

            <div style="margin-top: 40px;">
                <h3>📚 API 문서</h3>
                <p><a href="/docs" target="_blank">Swagger UI</a> | <a href="/redoc" target="_blank">ReDoc</a></p>
            </div>
        </div>

        <script>
            async function convertTextToSpeech() {
                const text = document.getElementById('text').value;
                const language = document.getElementById('language').value;
                const statusDiv = document.getElementById('status');
                const audioDiv = document.getElementById('audio-player');

                if (!text.trim()) {
                    statusDiv.innerHTML = '<div class="error">텍스트를 입력해주세요.</div>';
                    return;
                }

                statusDiv.innerHTML = '<div>🔄 음성을 생성하고 있습니다...</div>';
                audioDiv.innerHTML = '';

                try {
                    const response = await fetch('/api/tts', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            text: text,
                            language: language
                        })
                    });

                    const result = await response.json();

                    if (result.success) {
                        statusDiv.innerHTML = '<div class="success">✅ 음성 생성 완료!</div>';
                        audioDiv.innerHTML = `
                            <audio controls>
                                <source src="${result.audio_url}" type="audio/wav">
                                브라우저가 오디오를 지원하지 않습니다.
                            </audio>
                            <br>
                            <a href="${result.audio_url}" download="tts_output.wav">🔽 다운로드</a>
                        `;
                    } else {
                        statusDiv.innerHTML = `<div class="error">❌ 오류: ${result.error}</div>`;
                    }
                } catch (error) {
                    statusDiv.innerHTML = `<div class="error">❌ 네트워크 오류: ${error.message}</div>`;
                }
            }

            // 엔터키로 변환 실행
            document.getElementById('text').addEventListener('keydown', function(event) {
                if (event.ctrlKey && event.key === 'Enter') {
                    convertTextToSpeech();
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/api/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    """텍스트를 음성으로 변환"""
    global tts_model

    if not TTS_AVAILABLE or tts_model is None:
        return TTSResponse(
            success=False,
            error="TTS 모델이 사용 가능하지 않습니다"
        )

    # Broken pipe 오류 시 재시도 로직
    max_retries = 2
    for attempt in range(max_retries):
        try:
            # 오디오 저장 디렉토리 확인
            audio_dir = Path("static/audio")
            audio_dir.mkdir(parents=True, exist_ok=True)

            # 고유한 파일명 생성
            audio_filename = f"audio_{uuid.uuid4().hex}.wav"
            audio_path = audio_dir / audio_filename

            # TTS 생성
            speaker_ids = tts_model.hps.data.spk2id
            speaker_key = list(speaker_ids.keys())[0]  # 첫 번째 화자 사용

            # 음성 생성
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                tts_model.tts_to_file(
                    request.text,
                    speaker_ids[speaker_key],
                    temp_file.name,
                    speed=request.speed
                )

                # 임시 파일을 최종 위치로 복사
                import shutil
                shutil.move(temp_file.name, audio_path)

            audio_url = f"/static/audio/{audio_filename}"

            return TTSResponse(
                success=True,
                audio_url=audio_url
            )

        except Exception as e:
            error_msg = str(e)
            print(f"TTS 생성 오류 (시도 {attempt + 1}/{max_retries}): {error_msg}")

            # Broken pipe 오류이고 재시도 가능한 경우
            if "Errno 32" in error_msg or "Broken pipe" in error_msg:
                if attempt < max_retries - 1:  # 마지막 시도가 아닌 경우
                    print("🔄 TTS 모델 재로드 시도...")
                    try:
                        # 모델 재로드
                        device = 'cuda' if torch.cuda.is_available() else 'cpu'
                        tts_model = TTS(language="KR", device=device)
                        print("✅ TTS 모델 재로드 완료")
                        continue  # 재시도
                    except Exception as reload_error:
                        print(f"❌ TTS 모델 재로드 실패: {reload_error}")
                        return TTSResponse(
                            success=False,
                            error=f"모델 재로드 실패: {str(reload_error)}"
                        )

            # 재시도 불가능하거나 마지막 시도인 경우
            return TTSResponse(
                success=False,
                error=f"음성 생성 중 오류가 발생했습니다: {error_msg}"
            )

@app.get("/api/models/status", response_model=ModelStatusResponse)
async def get_models_status():
    """모델 상태 확인"""
    global tts_model

    return ModelStatusResponse(
        tts_available=TTS_AVAILABLE and tts_model is not None,
        tts_device=getattr(tts_model, 'device', None) if tts_model else None,
        cuda_available=torch.cuda.is_available() if TTS_AVAILABLE else False
    )

@app.get("/api/languages")
async def get_supported_languages():
    """지원 언어 목록"""
    return {
        "languages": [
            {"code": "KR", "name": "한국어"},
            {"code": "EN", "name": "영어"},
            {"code": "ZH", "name": "중국어"},
            {"code": "JP", "name": "일본어"},
            {"code": "FR", "name": "프랑스어"},
            {"code": "ES", "name": "스페인어"}
        ]
    }

if __name__ == "__main__":
    print("🚀 TTS 전용 서버 시작...")
    print("📖 API 문서: http://localhost:40003/docs")
    print("🌐 웹 앱: http://localhost:40003")
    print("")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=40003,
        log_level="info"
    )