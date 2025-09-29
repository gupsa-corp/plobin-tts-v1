#!/usr/bin/env python3
"""
웹 기반 음성 대화 시스템
Speech-to-Text + Text-to-Speech 실시간 대화
"""

import os
import sys
import asyncio
import tempfile
import warnings
import json
import uuid
from pathlib import Path
from typing import Optional, List
import base64

warnings.filterwarnings("ignore")

# Add MeloTTS to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'MeloTTS'))

from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# TTS 관련 임포트
try:
    import torch
    from melo.api import TTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

# STT 관련 임포트 (Whisper)
try:
    import whisper
    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False

# 자동 대화 관련 임포트
from auto_chat_manager import auto_chat_manager
from conversation_patterns import conversation_patterns

# FastAPI 앱 생성
app = FastAPI(
    title="음성 대화 시스템 API",
    description="Speech-to-Text + Text-to-Speech 실시간 대화 시스템",
    version="2.0.0",
    docs_url="/docs",  # Swagger UI 경로
    redoc_url="/redoc"  # ReDoc 경로
)

# 정적 파일 서빙
app.mount("/static", StaticFiles(directory="static"), name="static")

# 전역 변수
tts_model = None
stt_model = None
connected_clients = []

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
    error: Optional[str] = None

class ChatMessage(BaseModel):
    type: str  # "user", "system"
    text: str
    timestamp: str
    audio_url: Optional[str] = None

# 자동 대화 관련 모델
class AutoChatStartRequest(BaseModel):
    theme: str = "casual"
    interval: int = 30  # 초 단위

class AutoChatResponse(BaseModel):
    success: bool
    session_id: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None

class AutoChatUpdateRequest(BaseModel):
    theme: Optional[str] = None
    interval: Optional[int] = None

# 모델 초기화
async def initialize_models():
    """TTS와 STT 모델 초기화"""
    global tts_model, stt_model

    if TTS_AVAILABLE:
        try:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            tts_model = TTS(language="KR", device=device)
            print(f"✅ TTS 모델 로드 완료 (device: {device})")
        except Exception as e:
            print(f"❌ TTS 모델 로드 실패: {e}")

    if STT_AVAILABLE:
        try:
            stt_model = whisper.load_model("base")
            print("✅ STT 모델 로드 완료")
        except Exception as e:
            print(f"❌ STT 모델 로드 실패: {e}")

@app.on_event("startup")
async def startup_event():
    """서버 시작시 모델 초기화"""
    await initialize_models()

    # static 디렉토리 생성
    os.makedirs("static/audio", exist_ok=True)
    os.makedirs("templates", exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """메인 페이지"""
    html_file = "templates/index.html"
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    else:
        # 기본 HTML 반환
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>음성 대화 시스템</title>
            <meta charset="utf-8">
        </head>
        <body>
            <h1>음성 대화 시스템</h1>
            <p>웹 UI가 아직 구현되지 않았습니다.</p>
            <p><a href="/docs">API 문서 보기 (Swagger)</a></p>
        </body>
        </html>
        """)

@app.post("/api/tts", response_model=TTSResponse,
          summary="텍스트를 음성으로 변환",
          description="입력된 텍스트를 음성 파일로 변환합니다.")
async def text_to_speech(request: TTSRequest):
    """텍스트를 음성으로 변환"""
    global tts_model

    if not TTS_AVAILABLE or not tts_model:
        raise HTTPException(status_code=503, detail="TTS 서비스를 사용할 수 없습니다")

    try:
        # 디바이스 설정
        if request.device == 'auto':
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            device = request.device

        # 필요시 모델 재로드
        if hasattr(tts_model, 'device') and str(tts_model.device) != device:
            tts_model = TTS(language=request.language, device=device)

        # 임시 파일 생성
        audio_filename = f"audio_{uuid.uuid4().hex}.wav"
        audio_path = f"static/audio/{audio_filename}"

        # TTS 변환
        tts_model.tts_to_file(
            text=request.text,
            speaker_id=0,
            output_path=audio_path,
            speed=request.speed,
            quiet=True
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

@app.post("/api/stt", response_model=STTResponse,
          summary="음성을 텍스트로 변환",
          description="업로드된 음성 파일을 텍스트로 변환합니다.")
async def speech_to_text(audio_file: UploadFile = File(...)):
    """음성을 텍스트로 변환"""
    if not STT_AVAILABLE or not stt_model:
        raise HTTPException(status_code=503, detail="STT 서비스를 사용할 수 없습니다")

    try:
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            content = await audio_file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        # STT 변환
        result = stt_model.transcribe(temp_path)

        # 임시 파일 삭제
        os.unlink(temp_path)

        return STTResponse(
            success=True,
            text=result["text"].strip()
        )

    except Exception as e:
        return STTResponse(
            success=False,
            error=str(e)
        )

@app.get("/api/models/status",
         summary="모델 상태 확인",
         description="TTS와 STT 모델의 로드 상태를 확인합니다.")
async def get_models_status():
    """모델 상태 확인"""
    return {
        "tts_available": TTS_AVAILABLE and tts_model is not None,
        "stt_available": STT_AVAILABLE and stt_model is not None,
        "tts_device": str(getattr(tts_model, 'device', 'unknown')) if tts_model else None,
        "cuda_available": torch.cuda.is_available() if TTS_AVAILABLE else False
    }

@app.get("/api/languages",
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

@app.get("/api/websocket/info",
         summary="WebSocket 엔드포인트 정보",
         description="사용 가능한 WebSocket 엔드포인트들과 사용법을 반환합니다.")
async def get_websocket_info():
    """WebSocket 엔드포인트 정보"""
    return {
        "endpoints": [
            {
                "path": "/ws/stt",
                "name": "실시간 STT",
                "description": "음성을 실시간으로 텍스트로 변환",
                "message_format": {
                    "send": {
                        "type": "audio",
                        "data": "<base64_encoded_audio>",
                        "timestamp": "optional_timestamp"
                    },
                    "receive": {
                        "type": "stt_result",
                        "text": "변환된 텍스트",
                        "confidence": 0.95,
                        "timestamp": "timestamp"
                    }
                },
                "supported_audio_formats": ["WAV", "MP3", "M4A"],
                "example_js_code": """
// WebSocket 연결
const ws = new WebSocket('ws://localhost:8001/ws/stt');

// 음성 데이터 전송 (Base64 인코딩된 오디오)
ws.send(JSON.stringify({
    type: 'audio',
    data: audioBase64,
    timestamp: new Date().toISOString()
}));

// 결과 수신
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'stt_result') {
        console.log('변환된 텍스트:', data.text);
        console.log('신뢰도:', data.confidence);
    }
};
                """
            },
            {
                "path": "/ws/chat",
                "name": "실시간 음성 대화",
                "description": "STT + TTS + 대화 시스템 통합",
                "message_format": {
                    "send": {
                        "type": "audio | auto_chat_start | auto_chat_stop | auto_chat_message",
                        "data": "message_data",
                        "theme": "optional_for_auto_chat",
                        "interval": "optional_for_auto_chat"
                    },
                    "receive": {
                        "type": "user_message | system_response | auto_message_response | error",
                        "text": "메시지 내용",
                        "audio_url": "음성 파일 URL (해당하는 경우)",
                        "timestamp": "timestamp"
                    }
                },
                "features": [
                    "실시간 음성 인식 (STT)",
                    "음성 합성 (TTS)",
                    "자동 대화 시스템",
                    "다양한 대화 주제 지원"
                ]
            }
        ],
        "common_message_types": {
            "ping": "연결 상태 확인 (모든 WebSocket에서 지원)",
            "pong": "ping에 대한 응답"
        },
        "connection_example": "ws://localhost:8001/ws/stt 또는 ws://localhost:8001/ws/chat"
    }

# 자동 대화 API 엔드포인트들
@app.get("/api/auto-chat/themes",
         summary="자동 대화 주제 목록",
         description="사용 가능한 자동 대화 주제들을 반환합니다.")
async def get_auto_chat_themes():
    """자동 대화 주제 목록"""
    themes = conversation_patterns.get_all_themes()
    theme_info = {
        "casual": "일상 대화",
        "weather": "날씨 이야기",
        "educational": "학습 도우미",
        "entertainment": "재미있는 대화",
        "motivational": "동기부여",
        "questions": "질문과 답변",
        "greeting": "인사말"
    }

    return {
        "themes": [
            {"code": theme, "name": theme_info.get(theme, theme)}
            for theme in themes
        ]
    }

@app.get("/api/auto-chat/sessions",
         summary="자동 대화 세션 정보",
         description="현재 활성화된 자동 대화 세션들의 정보를 반환합니다.")
async def get_auto_chat_sessions():
    """자동 대화 세션 정보 조회"""
    return auto_chat_manager.get_all_sessions_info()

@app.get("/api/auto-chat/sessions/{session_id}",
         summary="특정 자동 대화 세션 정보",
         description="특정 자동 대화 세션의 상세 정보를 반환합니다.")
async def get_auto_chat_session(session_id: str):
    """특정 자동 대화 세션 정보 조회"""
    session_info = auto_chat_manager.get_session_info(session_id)
    if session_info:
        return session_info
    else:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# WebSocket STT 전용 응답 모델 (Swagger용)
class WebSocketSTTMessage(BaseModel):
    """WebSocket STT 메시지 모델"""
    type: str  # "audio", "text"
    data: Optional[str] = None  # Base64 인코딩된 오디오 데이터 또는 텍스트
    timestamp: Optional[str] = None

class WebSocketSTTResponse(BaseModel):
    """WebSocket STT 응답 모델"""
    type: str  # "stt_result", "error"
    text: Optional[str] = None  # 변환된 텍스트
    confidence: Optional[float] = None  # 신뢰도 (0-1)
    error: Optional[str] = None
    timestamp: Optional[str] = None

@app.websocket("/ws/stt")
async def websocket_stt(websocket: WebSocket):
    """실시간 STT 전용 WebSocket

    음성 데이터를 실시간으로 받아서 텍스트로 변환합니다.

    **메시지 형식:**
    - 송신: `{"type": "audio", "data": "<base64_audio>", "timestamp": "..."}`
    - 수신: `{"type": "stt_result", "text": "변환된 텍스트", "confidence": 0.95, "timestamp": "..."}`

    **지원 오디오 형식:** WAV, MP3, M4A
    """
    await manager.connect(websocket)
    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_text()
            message_data = json.loads(data)

            if message_data["type"] == "audio":
                # 음성 데이터를 텍스트로 변환
                try:
                    if not STT_AVAILABLE or not stt_model:
                        await manager.send_personal_message(json.dumps({
                            "type": "error",
                            "error": "STT 서비스를 사용할 수 없습니다",
                            "timestamp": message_data.get("timestamp", "")
                        }), websocket)
                        continue

                    # Base64 오디오 디코딩
                    audio_data = base64.b64decode(message_data["data"])

                    # STT 처리
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                        temp_file.write(audio_data)
                        temp_path = temp_file.name

                    result = stt_model.transcribe(temp_path)
                    transcribed_text = result["text"].strip()

                    # 신뢰도 계산 (Whisper는 세그먼트별 확률 제공)
                    confidence = 0.0
                    if "segments" in result and result["segments"]:
                        confidence = sum(seg.get("avg_logprob", 0) for seg in result["segments"]) / len(result["segments"])
                        confidence = max(0, min(1, (confidence + 1) / 2))  # -1~0 범위를 0~1로 변환

                    # 임시 파일 삭제
                    os.unlink(temp_path)

                    # STT 결과 전송
                    await manager.send_personal_message(json.dumps({
                        "type": "stt_result",
                        "text": transcribed_text,
                        "confidence": round(confidence, 3),
                        "timestamp": message_data.get("timestamp", "")
                    }), websocket)

                except Exception as e:
                    await manager.send_personal_message(json.dumps({
                        "type": "error",
                        "error": f"STT 처리 오류: {str(e)}",
                        "timestamp": message_data.get("timestamp", "")
                    }), websocket)

            elif message_data["type"] == "ping":
                # 연결 상태 확인
                await manager.send_personal_message(json.dumps({
                    "type": "pong",
                    "timestamp": message_data.get("timestamp", "")
                }), websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """실시간 음성 대화 WebSocket"""
    await manager.connect(websocket)
    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_text()
            message_data = json.loads(data)

            if message_data["type"] == "audio":
                # 음성 데이터 처리 (Base64 디코딩 -> STT -> 응답 생성 -> TTS)
                try:
                    # Base64 오디오 디코딩
                    audio_data = base64.b64decode(message_data["data"])

                    # STT 처리
                    if STT_AVAILABLE and stt_model:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                            temp_file.write(audio_data)
                            temp_path = temp_file.name

                        result = stt_model.transcribe(temp_path)
                        user_text = result["text"].strip()
                        os.unlink(temp_path)

                        # 사용자 메시지 전송
                        await manager.send_personal_message(json.dumps({
                            "type": "user_message",
                            "text": user_text,
                            "timestamp": message_data.get("timestamp", "")
                        }), websocket)

                        # 자동 대화 매니저에 사용자 입력 알림
                        await auto_chat_manager.handle_user_input(websocket, user_text)

                        # 간단한 응답 생성 (실제로는 AI 모델 연동 가능)
                        response_text = generate_response(user_text)

                        # TTS 변환
                        if TTS_AVAILABLE and tts_model:
                            audio_filename = f"audio_{uuid.uuid4().hex}.wav"
                            audio_path = f"static/audio/{audio_filename}"

                            tts_model.tts_to_file(
                                text=response_text,
                                speaker_id=0,
                                output_path=audio_path,
                                speed=1.0,
                                quiet=True
                            )

                            # 시스템 응답 전송
                            await manager.send_personal_message(json.dumps({
                                "type": "system_response",
                                "text": response_text,
                                "audio_url": f"/static/audio/{audio_filename}",
                                "timestamp": message_data.get("timestamp", "")
                            }), websocket)

                except Exception as e:
                    await manager.send_personal_message(json.dumps({
                        "type": "error",
                        "message": f"처리 오류: {str(e)}"
                    }), websocket)

            elif message_data["type"] == "auto_chat_start":
                # 자동 대화 시작 요청
                try:
                    theme = message_data.get("theme", "casual")
                    interval = message_data.get("interval", 30)

                    session_id = await auto_chat_manager.start_auto_chat(websocket, theme, interval)

                    await manager.send_personal_message(json.dumps({
                        "type": "auto_chat_started",
                        "session_id": session_id,
                        "theme": theme,
                        "interval": interval,
                        "message": "자동 대화가 시작되었습니다."
                    }), websocket)

                except Exception as e:
                    await manager.send_personal_message(json.dumps({
                        "type": "error",
                        "message": f"자동 대화 시작 오류: {str(e)}"
                    }), websocket)

            elif message_data["type"] == "auto_chat_stop":
                # 자동 대화 중지 요청
                try:
                    stopped = await auto_chat_manager.stop_auto_chat_for_websocket(websocket)

                    await manager.send_personal_message(json.dumps({
                        "type": "auto_chat_stopped",
                        "message": "자동 대화가 중지되었습니다." if stopped else "활성 자동 대화가 없습니다."
                    }), websocket)

                except Exception as e:
                    await manager.send_personal_message(json.dumps({
                        "type": "error",
                        "message": f"자동 대화 중지 오류: {str(e)}"
                    }), websocket)

            elif message_data["type"] == "auto_chat_message":
                # 자동 대화 메시지를 TTS로 변환
                try:
                    text = message_data.get("text", "")
                    if text and TTS_AVAILABLE and tts_model:
                        audio_filename = f"audio_{uuid.uuid4().hex}.wav"
                        audio_path = f"static/audio/{audio_filename}"

                        tts_model.tts_to_file(
                            text=text,
                            speaker_id=0,
                            output_path=audio_path,
                            speed=1.0,
                            quiet=True
                        )

                        # 자동 대화 메시지로 전송
                        await manager.send_personal_message(json.dumps({
                            "type": "auto_message_response",
                            "text": text,
                            "audio_url": f"/static/audio/{audio_filename}",
                            "timestamp": message_data.get("timestamp", ""),
                            "session_id": message_data.get("session_id", ""),
                            "theme": message_data.get("theme", "casual")
                        }), websocket)

                except Exception as e:
                    await manager.send_personal_message(json.dumps({
                        "type": "error",
                        "message": f"자동 대화 TTS 오류: {str(e)}"
                    }), websocket)

    except WebSocketDisconnect:
        # 연결이 끊어질 때 자동 대화도 정리
        await auto_chat_manager.stop_auto_chat_for_websocket(websocket)
        manager.disconnect(websocket)

def generate_response(user_text: str) -> str:
    """간단한 응답 생성 (추후 AI 모델로 확장 가능)"""
    user_text = user_text.lower()

    if "안녕" in user_text or "hello" in user_text:
        return "안녕하세요! 음성 대화 시스템입니다."
    elif "날씨" in user_text or "weather" in user_text:
        return "오늘 날씨는 좋네요!"
    elif "이름" in user_text or "name" in user_text:
        return "저는 음성 대화 시스템입니다."
    elif "시간" in user_text or "time" in user_text:
        import datetime
        now = datetime.datetime.now()
        return f"현재 시간은 {now.strftime('%H시 %M분')}입니다."
    else:
        return "네, 잘 들었습니다. 다른 질문이 있으시면 말씀해 주세요."

# 개발 서버 실행
if __name__ == "__main__":
    print("🚀 음성 대화 시스템 웹 서버 시작...")
    print(f"TTS 지원: {'Yes' if TTS_AVAILABLE else 'No'}")
    print(f"STT 지원: {'Yes' if STT_AVAILABLE else 'No'}")
    print("📖 API 문서: http://localhost:8001/docs")
    print("🌐 웹 앱: http://localhost:8001")

    uvicorn.run(app, host="0.0.0.0", port=8001)