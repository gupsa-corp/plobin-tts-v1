#!/usr/bin/env python3
"""
플로빈 TTS 서버 - 안정성 극대화 버전
Broken pipe 오류 완전 해결
"""

import os
import sys
import tempfile
import traceback
import uuid
import time
import threading
import signal
import gc
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

# Add MeloTTS to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'MeloTTS'))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# TTS 관련 임포트
TTS_AVAILABLE = False
try:
    import torch
    from melo.api import TTS
    TTS_AVAILABLE = True
    print("✅ TTS 모듈 임포트 성공")
except ImportError as e:
    print(f"❌ TTS 모듈 임포트 실패: {e}")

# FastAPI 앱 생성
app = FastAPI(
    title="플로빈 TTS API",
    description="안정성이 극대화된 Text-to-Speech 서버",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 정적 파일 서빙
app.mount("/static", StaticFiles(directory="static"), name="static")

# 글로벌 변수
tts_model = None
model_lock = threading.Lock()
model_load_count = 0

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
    model_loads: int = 0

@contextmanager
def safe_cuda_context():
    """CUDA 컨텍스트 안전 관리"""
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        yield
    finally:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()

def force_cleanup_model():
    """강제 모델 정리"""
    global tts_model
    try:
        if tts_model is not None:
            del tts_model
            tts_model = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception as e:
        print(f"모델 정리 중 오류: {e}")

def load_tts_model_safe():
    """안전한 TTS 모델 로드"""
    global tts_model, model_load_count

    with model_lock:
        try:
            # 기존 모델 정리
            force_cleanup_model()

            print("🔄 TTS 모델 안전 로드 시작...")
            with safe_cuda_context():
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
                tts_model = TTS(language="KR", device=device)
                model_load_count += 1
                print(f"✅ TTS 모델 로드 완료 (device: {device}, 로드 횟수: {model_load_count})")
                return True
        except Exception as e:
            print(f"❌ TTS 모델 로드 실패: {e}")
            traceback.print_exc()
            force_cleanup_model()
            return False

async def initialize_tts():
    """TTS 모델 초기화"""
    if TTS_AVAILABLE:
        return load_tts_model_safe()
    else:
        print("❌ TTS 모듈을 사용할 수 없습니다")
        return False

@app.on_event("startup")
async def startup_event():
    """서버 시작시 모델 초기화"""
    success = await initialize_tts()
    if success:
        print("🎉 플로빈 TTS 서버가 성공적으로 시작되었습니다!")
    else:
        print("⚠️ TTS 모델 로드에 실패했지만 서버는 시작됩니다.")

def safe_tts_generation(text: str, speaker_id: int, output_path: str, speed: float = 2.0):
    """안전한 TTS 생성 함수"""
    global tts_model

    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            print(f"TTS 생성 시도 {attempt + 1}/{max_attempts}")

            with safe_cuda_context():
                # 모델 유효성 검사
                if tts_model is None:
                    raise Exception("TTS 모델이 로드되지 않음")

                # 임시 파일을 통한 안전한 생성 (.wav 확장자 유지)
                temp_path = output_path.replace(".wav", "_tmp.wav")

                # TTS 생성
                tts_model.tts_to_file(
                    text,
                    speaker_id,
                    temp_path,
                    speed=speed,
                    quiet=True  # 진행 표시 비활성화
                )

                # 파일 검증
                if not os.path.exists(temp_path):
                    raise Exception("임시 파일이 생성되지 않음")

                file_size = os.path.getsize(temp_path)
                if file_size == 0:
                    raise Exception("생성된 파일이 비어있음")

                # 최종 위치로 이동
                import shutil
                shutil.move(temp_path, output_path)

                print(f"✅ TTS 생성 성공 (크기: {file_size} bytes)")
                return True

        except Exception as e:
            error_msg = str(e)
            print(f"❌ TTS 생성 실패 (시도 {attempt + 1}): {error_msg}")

            # 임시 파일 정리
            try:
                temp_path = output_path.replace(".wav", "_tmp.wav")
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            except:
                pass

            # broken pipe 또는 CUDA 오류인 경우 모델 재로드
            if any(keyword in error_msg.lower() for keyword in ['broken pipe', 'errno 32', 'cuda', 'out of memory']):
                print(f"🔄 심각한 오류 감지, 모델 재로드 중... ({error_msg})")
                if load_tts_model_safe():
                    continue  # 재시도
                else:
                    break  # 모델 로드 실패시 중단

            # 마지막 시도가 아니면 잠시 대기 후 재시도
            if attempt < max_attempts - 1:
                time.sleep(1)
                continue

    return False

@app.get("/", response_class=HTMLResponse)
async def read_index():
    """메인 페이지"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>플로빈 TTS 서비스</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
            .container { max-width: 800px; margin: 0 auto; padding: 20px; }
            .form-group { margin: 20px 0; }
            input[type="text"], textarea, select, button { padding: 10px; margin: 5px; border: 1px solid #ddd; border-radius: 5px; }
            textarea { width: 90%; height: 100px; resize: vertical; }
            button { background: #007bff; color: white; border: none; cursor: pointer; }
            button:hover { background: #0056b3; }
            .success { color: green; margin: 10px 0; }
            .error { color: red; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎵 플로빈 TTS 서비스</h1>
            <p>안정성이 극대화된 Text-to-Speech 서비스입니다.</p>

            <div class="form-group">
                <label for="text">변환할 텍스트:</label>
                <textarea id="text" placeholder="여기에 텍스트를 입력하세요...">안녕하세요! 플로빈 TTS 서비스입니다.</textarea>
            </div>

            <div class="form-group">
                <label for="language">언어:</label>
                <select id="language">
                    <option value="KR">한국어</option>
                </select>
            </div>

            <div class="form-group">
                <label for="speed">속도:</label>
                <input type="range" id="speed" min="0.5" max="3.0" step="0.1" value="2.0">
                <span id="speed-value">2.0</span>
            </div>

            <div class="form-group">
                <button onclick="convertTextToSpeech()">🎵 음성 생성</button>
            </div>

            <div id="status"></div>
            <div id="audio-player"></div>

            <div style="margin-top: 40px;">
                <h3>📚 API 정보</h3>
                <p><a href="/docs" target="_blank">Swagger UI</a> | <a href="/redoc" target="_blank">ReDoc</a> | <a href="/api/models/status" target="_blank">모델 상태</a></p>
            </div>
        </div>

        <script>
            const speedSlider = document.getElementById('speed');
            const speedValue = document.getElementById('speed-value');
            speedSlider.addEventListener('input', function() {
                speedValue.textContent = this.value;
            });

            async function convertTextToSpeech() {
                const text = document.getElementById('text').value;
                const language = document.getElementById('language').value;
                const speed = parseFloat(document.getElementById('speed').value);
                const statusDiv = document.getElementById('status');
                const audioDiv = document.getElementById('audio-player');

                if (!text.trim()) {
                    statusDiv.innerHTML = '<div class="error">텍스트를 입력해주세요.</div>';
                    return;
                }

                statusDiv.innerHTML = '<div>🔄 음성을 생성하고 있습니다... (안정성 강화 모드)</div>';
                audioDiv.innerHTML = '';

                try {
                    const response = await fetch('/api/tts', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text: text, language: language, speed: speed })
                    });

                    const result = await response.json();

                    if (result.success) {
                        statusDiv.innerHTML = '<div class="success">✅ 음성 생성 완료!</div>';
                        audioDiv.innerHTML = `
                            <audio controls autoplay>
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

            // 엔터키 지원
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
    """플로빈 텍스트 음성 변환"""
    global tts_model

    if not TTS_AVAILABLE:
        return TTSResponse(
            success=False,
            error="TTS 모듈이 사용 가능하지 않습니다"
        )

    if tts_model is None:
        print("모델이 없음, 로드 시도...")
        if not load_tts_model_safe():
            return TTSResponse(
                success=False,
                error="TTS 모델을 로드할 수 없습니다"
            )

    try:
        # 오디오 저장 디렉토리 확인
        audio_dir = Path("static/audio")
        audio_dir.mkdir(parents=True, exist_ok=True)

        # 고유한 파일명 생성
        audio_filename = f"robust_audio_{uuid.uuid4().hex}.wav"
        audio_path = audio_dir / audio_filename

        print(f"🔄 TTS 요청 처리: '{request.text}' -> {audio_path}")

        # 화자 ID 가져오기
        speaker_ids = tts_model.hps.data.spk2id
        speaker_key = list(speaker_ids.keys())[0]
        speaker_id = speaker_ids[speaker_key]

        # 안전한 TTS 생성
        success = safe_tts_generation(
            request.text,
            speaker_id,
            str(audio_path),
            request.speed
        )

        if success:
            audio_url = f"/static/audio/{audio_filename}"
            return TTSResponse(success=True, audio_url=audio_url)
        else:
            return TTSResponse(
                success=False,
                error="음성 생성에 실패했습니다. 모든 재시도가 실패했습니다."
            )

    except Exception as e:
        error_msg = f"예상치 못한 오류: {str(e)}"
        print(f"❌ {error_msg}")
        traceback.print_exc()
        return TTSResponse(success=False, error=error_msg)

@app.get("/api/models/status", response_model=ModelStatusResponse)
async def get_models_status():
    """모델 상태 확인"""
    global tts_model, model_load_count

    return ModelStatusResponse(
        tts_available=TTS_AVAILABLE and tts_model is not None,
        tts_device=getattr(tts_model, 'device', None) if tts_model else None,
        cuda_available=torch.cuda.is_available() if TTS_AVAILABLE else False,
        model_loads=model_load_count
    )

@app.post("/api/reload-model")
async def reload_model():
    """모델 강제 재로드"""
    success = load_tts_model_safe()
    return {"success": success, "loads": model_load_count}

# 정상 종료 처리
def signal_handler(signum, frame):
    print("🛑 서비스 종료 신호 수신, 정리 중...")
    force_cleanup_model()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    print("🚀 플로빈 TTS 서버 시작...")
    print("📖 API 문서: http://localhost:40003/docs")
    print("🌐 웹 앱: http://localhost:40003")
    print("")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=40003,
        log_level="info"
    )