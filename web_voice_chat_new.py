#!/usr/bin/env python3
"""
웹 기반 음성 대화 시스템 (모듈화 버전)
Speech-to-Text + Text-to-Speech 실시간 대화
"""

import os
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# 모듈 임포트
from config.settings import (
    SERVER_HOST,
    SERVER_PORT,
    ensure_directories
)
from models.model_manager import model_manager
from api.endpoints import router as api_router
from api.auto_chat_api import router as auto_chat_router
from api.websocket_docs import router as websocket_docs_router
from websocket.stt_handler import handle_stt_websocket
from websocket.chat_handler import handle_chat_websocket

# FastAPI 앱 생성
app = FastAPI(
    title="통합 음성 대화 시스템 API (v2.2.0)",
    description="통합 음성 대화 시스템: STT + TTS + 실시간 대화 + 배치 처리",
    version="2.2.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 정적 파일 서빙
app.mount("/static", StaticFiles(directory="static"), name="static")

# API 라우터 등록
app.include_router(api_router)
app.include_router(auto_chat_router)
app.include_router(websocket_docs_router)

# 메시지 모델
class ChatMessage(BaseModel):
    type: str  # "user", "system"
    text: str
    timestamp: str
    audio_url: str = None

@app.on_event("startup")
async def startup_event():
    """서버 시작시 초기화"""
    # 디렉토리 생성
    ensure_directories()

    # 모델 초기화
    await model_manager.initialize_models()

    print("✅ 웹 음성 대화 시스템 초기화 완료")

@app.get("/test", response_class=HTMLResponse)
async def get_test_page():
    """브라우저 테스트 페이지"""
    test_file = "test_browser.html"
    if os.path.exists(test_file):
        with open(test_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="<h1>테스트 페이지를 찾을 수 없습니다</h1>", status_code=404)

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
            <title>음성 대화 시스템 (모듈화)</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 800px; margin: 0 auto; }
                .status { background: #f0f8ff; padding: 20px; border-radius: 5px; margin: 20px 0; }
                .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .endpoint h3 { margin-top: 0; color: #333; }
                .code { background: #e8e8e8; padding: 10px; border-radius: 3px; font-family: monospace; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎤 음성 대화 시스템 (모듈화 버전)</h1>

                <div class="status">
                    <h2>📊 시스템 상태</h2>
                    <p>✅ 모듈화된 아키텍처로 업그레이드되었습니다!</p>
                    <p>🔧 설정 관리, 모델 관리, API, WebSocket이 분리되어 유지보수가 용이합니다.</p>
                </div>

                <div class="endpoint">
                    <h3>🌐 사용 가능한 엔드포인트</h3>
                    <ul>
                        <li><strong>API 문서:</strong> <a href="/docs">Swagger UI</a> | <a href="/redoc">ReDoc</a></li>
                        <li><strong>TTS API:</strong> <code>/api/tts</code></li>
                        <li><strong>STT API:</strong> <code>/api/stt</code></li>
                        <li><strong>모델 상태:</strong> <code>/api/models/status</code></li>
                        <li><strong>지원 언어:</strong> <code>/api/languages</code></li>
                        <li><strong>자동 대화 주제:</strong> <code>/api/auto-chat/themes</code></li>
                    </ul>
                </div>

                <div class="endpoint">
                    <h3>🔌 WebSocket 엔드포인트</h3>
                    <ul>
                        <li><strong>실시간 STT:</strong> <code>ws://localhost:40003/ws/stt</code></li>
                        <li><strong>음성 대화:</strong> <code>ws://localhost:40003/ws/chat</code></li>
                    </ul>
                </div>

                <div class="endpoint">
                    <h3>🏗️ 모듈 구조</h3>
                    <div class="code">
├── config/          # 설정 관리<br>
├── models/          # TTS/STT 모델 관리<br>
├── api/             # REST API 엔드포인트<br>
├── websocket/       # WebSocket 핸들러<br>
├── utils/           # 유틸리티 (오디오 전처리 등)<br>
└── web_voice_chat_new.py  # 메인 앱
                    </div>
                </div>

                <p><a href="/docs">📖 전체 API 문서 보기</a></p>
            </div>
        </body>
        </html>
        """)

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
                "handler": "websocket.stt_handler.handle_stt_websocket"
            },
            {
                "path": "/ws/chat",
                "name": "실시간 음성 대화",
                "description": "STT + TTS + 대화 시스템 통합",
                "handler": "websocket.chat_handler.handle_chat_websocket"
            }
        ],
        "features": [
            "모듈화된 아키텍처",
            "한국어 최적화 STT",
            "노이즈 제거 오디오 전처리",
            "자동 대화 시스템",
            "실시간 양방향 통신"
        ]
    }

# WebSocket 엔드포인트
@app.websocket("/ws/stt")
async def websocket_stt(websocket: WebSocket):
    """실시간 STT 전용 WebSocket"""
    await handle_stt_websocket(websocket)

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """실시간 음성 대화 WebSocket"""
    await handle_chat_websocket(websocket)

# 개발 서버 실행
if __name__ == "__main__":
    print("🚀 음성 대화 시스템 웹 서버 시작 (모듈화 버전)...")
    print(f"📖 API 문서: http://{SERVER_HOST}:{SERVER_PORT}/docs")
    print(f"🌐 웹 앱: http://{SERVER_HOST}:{SERVER_PORT}")
    print("🏗️  모듈화된 아키텍처로 업그레이드 완료!")

    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)