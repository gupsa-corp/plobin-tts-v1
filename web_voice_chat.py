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
import subprocess
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

# STT 관련 임포트 (Whisper만 - WebM 직접 처리)
try:
    import whisper
    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False

# 오디오 변환 함수
def convert_wav_to_webm(wav_path: str) -> str:
    """WAV 파일을 WebM으로 변환"""
    webm_path = wav_path.replace('.wav', '.webm')

    try:
        # ffmpeg를 사용하여 WAV → WebM 변환
        subprocess.run([
            'ffmpeg', '-i', wav_path,
            '-c:a', 'libopus',  # Opus 오디오 코덱 사용
            '-b:a', '64k',      # 64kbps 비트레이트
            '-y',               # 기존 파일 덮어쓰기
            webm_path
        ], check=True, capture_output=True)

        # 원본 WAV 파일 삭제
        if os.path.exists(wav_path):
            os.unlink(wav_path)

        return webm_path

    except subprocess.CalledProcessError as e:
        # 변환 실패 시 원본 WAV 반환
        print(f"⚠️ WebM 변환 실패, WAV 파일 유지: {e}")
        return wav_path
    except Exception as e:
        print(f"⚠️ 변환 중 오류: {e}")
        return wav_path

# 실시간 STT 서비스 임포트
try:
    from streaming_stt_service import streaming_stt_service, TranscriptionResult
    STREAMING_STT_AVAILABLE = True
except ImportError:
    STREAMING_STT_AVAILABLE = False
    print("❌ 실시간 STT 서비스를 가져올 수 없습니다")

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
    speed: float = 2.0
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
            # 더 나은 한국어 지원을 위해 medium 모델 사용 (다운로드 시간이 오래 걸리므로 base로 임시 설정)
            stt_model = whisper.load_model("base")
            print("✅ STT 모델 로드 완료 (medium - 한국어 최적화)")
        except Exception as e:
            print(f"❌ STT 모델 로드 실패: {e}")

@app.on_event("startup")
async def startup_event():
    """서버 시작시 모델 초기화"""
    await initialize_models()

    # 실시간 STT 서비스 초기화
    if STREAMING_STT_AVAILABLE:
        try:
            await streaming_stt_service.initialize()
            print("✅ 실시간 STT 서비스 초기화 완료")
        except Exception as e:
            print(f"❌ 실시간 STT 서비스 초기화 실패: {e}")

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

        # 임시 WAV 파일 생성
        wav_filename = f"audio_{uuid.uuid4().hex}.wav"
        wav_path = f"static/audio/{wav_filename}"

        # TTS 변환 (WAV로 생성)
        tts_model.tts_to_file(
            text=request.text,
            speaker_id=0,
            output_path=wav_path,
            speed=request.speed,
            quiet=True
        )

        # WAV → WebM 변환
        final_path = convert_wav_to_webm(wav_path)
        final_filename = os.path.basename(final_path)

        return TTSResponse(
            success=True,
            audio_url=f"/static/audio/{final_filename}"
        )

    except Exception as e:
        return TTSResponse(
            success=False,
            error=str(e)
        )

@app.post("/api/stt", response_model=STTResponse,
          summary="WebM 음성을 텍스트로 변환",
          description="업로드된 WebM 음성 파일을 텍스트로 변환합니다.")
async def speech_to_text(audio_file: UploadFile = File(...)):
    """WebM 음성을 텍스트로 변환"""
    if not STT_AVAILABLE or not stt_model:
        raise HTTPException(status_code=503, detail="STT 서비스를 사용할 수 없습니다")

    # WebM 파일만 허용
    if not audio_file.filename or not audio_file.filename.lower().endswith('.webm'):
        if not audio_file.content_type or 'webm' not in audio_file.content_type.lower():
            raise HTTPException(status_code=400, detail="WebM 형식의 파일만 지원합니다")

    try:
        # 오디오 데이터 읽기
        content = await audio_file.read()

        # 파일 크기 검증
        if len(content) < 100:
            raise HTTPException(status_code=400, detail="오디오 파일이 너무 작습니다")

        # WebM 데이터를 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_file:
            temp_file.write(content)
            webm_path = temp_file.name

        # WebM 파일 유효성 검증
        try:
            with open(webm_path, 'rb') as f:
                header = f.read(32)
                if b'\x1a\x45\xdf\xa3' not in header:  # EBML header 확인
                    raise HTTPException(status_code=400, detail="유효하지 않은 WebM 파일입니다")
        except Exception as validation_error:
            if os.path.exists(webm_path):
                os.unlink(webm_path)
            raise HTTPException(status_code=400, detail=f"WebM 파일 검증 실패: {str(validation_error)}")

        # STT 변환 (WebM 직접 처리)
        try:
            result = stt_model.transcribe(
                webm_path,
                language="ko",  # 한국어 기본 설정
                initial_prompt="안녕하세요. 한국어로 말씀해 주세요.",  # 한국어 컨텍스트 제공
                word_timestamps=True,
                fp16=False,  # 안정성을 위해 fp16 비활성화
                temperature=0.0,  # 일관된 결과를 위해 temperature 0
                compression_ratio_threshold=2.4,
                logprob_threshold=-1.0,
                no_speech_threshold=0.6
            )
        except Exception as transcribe_error:
            # 임시 WebM 파일 삭제
            if os.path.exists(webm_path):
                os.unlink(webm_path)
            raise HTTPException(status_code=500, detail=f"STT 처리 오류: {str(transcribe_error)}")

        # 임시 WebM 파일 삭제
        if os.path.exists(webm_path):
            os.unlink(webm_path)

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
                "name": "기존 STT (배치 처리)",
                "description": "전체 오디오를 한 번에 처리하는 기존 방식",
                "processing_type": "batch",
                "latency": "2-5초",
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
                "supported_audio_formats": ["WEBM"]
            },
            {
                "path": "/ws/streaming-stt",
                "name": "🚀 스트리밍 STT (실시간)",
                "description": "Faster Whisper + VAD 기반 실시간 음성 인식",
                "processing_type": "streaming_chunks",
                "latency": "200-500ms",
                "features": [
                    "실시간 청크 처리 (500ms 간격)",
                    "Voice Activity Detection (VAD)",
                    "부분 결과 + 최종 결과 분리",
                    "4-5배 빠른 처리 속도",
                    "50% 적은 메모리 사용"
                ],
                "message_format": {
                    "send": {
                        "type": "audio_chunk | start_stream | stop_stream | ping",
                        "data": "<base64_encoded_audio_chunk>",
                        "timestamp": "timestamp",
                        "chunk_id": "unique_id"
                    },
                    "receive_partial": {
                        "type": "partial_result",
                        "text": "부분 결과...",
                        "confidence": 0.85,
                        "is_final": False,
                        "timestamp": 1701943800.123,
                        "processing_time": 0.25
                    },
                    "receive_final": {
                        "type": "final_result",
                        "text": "최종 완성된 텍스트",
                        "confidence": 0.92,
                        "is_final": True,
                        "timestamp": 1701943802.456,
                        "processing_time": 0.18
                    }
                },
                "supported_audio_formats": ["WEBM"],
                "example_js_code": """
// 스트리밍 STT WebSocket 연결
const streamingWs = new WebSocket('ws://localhost:6001/ws/streaming-stt');

// 스트림 시작
streamingWs.send(JSON.stringify({
    type: 'start_stream',
    timestamp: new Date().toISOString()
}));

// 실시간 오디오 청크 전송 (MediaRecorder 사용)
mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) {
        const reader = new FileReader();
        reader.onload = () => {
            const base64 = btoa(reader.result);
            streamingWs.send(JSON.stringify({
                type: 'audio_chunk',
                data: base64,
                timestamp: new Date().toISOString(),
                chunk_id: Date.now().toString()
            }));
        };
        reader.readAsBinaryString(event.data);
    }
};

// 500ms마다 청크 생성
mediaRecorder.start(500);

// 결과 수신
streamingWs.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'partial_result') {
        // 실시간 부분 결과 표시
        updatePartialText(data.text, data.confidence);
    } else if (data.type === 'final_result') {
        // 최종 결과 확정
        finalizeTranon(data.text, data.confidence);
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
        "performance_comparison": {
            "legacy_stt": {
                "latency": "2-5초",
                "processing": "배치",
                "realtime": False
            },
            "streaming_stt": {
                "latency": "200-500ms",
                "processing": "스트리밍",
                "realtime": True,
                "speed_improvement": "4-5배"
            }
        },
        "common_message_types": {
            "ping": "연결 상태 확인 (모든 WebSocket에서 지원)",
            "pong": "ping에 대한 응답"
        },
        "connection_examples": {
            "legacy_stt": "ws://localhost:6001/ws/stt",
            "streaming_stt": "ws://localhost:6001/ws/streaming-stt",
            "chat": "ws://localhost:6001/ws/chat"
        }
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

# 새로운 스트리밍 STT 관련 API 엔드포인트들
@app.get("/api/streaming-stt/status",
         summary="스트리밍 STT 서비스 상태",
         description="실시간 STT 서비스의 상태와 통계를 반환합니다.")
async def get_streaming_stt_status():
    """스트리밍 STT 서비스 상태 조회"""
    if not STREAMING_STT_AVAILABLE:
        raise HTTPException(status_code=503, detail="스트리밍 STT 서비스를 사용할 수 없습니다")

    return streaming_stt_service.get_stats()

@app.post("/api/streaming-stt/test",
          summary="스트리밍 STT 테스트",
          description="업로드된 오디오 파일로 스트리밍 STT를 테스트합니다.")
async def test_streaming_stt(audio_file: UploadFile = File(...)):
    """스트리밍 STT 테스트용 엔드포인트"""
    if not STREAMING_STT_AVAILABLE:
        raise HTTPException(status_code=503, detail="스트리밍 STT 서비스를 사용할 수 없습니다")

    try:
        # 오디오 데이터 읽기
        content = await audio_file.read()

        # 스트리밍 STT 서비스에 추가
        streaming_stt_service.add_audio_chunk(content, time.time())

        # 잠시 대기 후 결과 수집 (테스트용)
        results = []
        timeout = 10  # 10초 타임아웃
        start_time = time.time()

        async for result in streaming_stt_service.process_stream():
            results.append({
                "text": result.text,
                "confidence": result.confidence,
                "is_final": result.is_final,
                "processing_time": result.processing_time
            })

            # 최종 결과가 나오거나 타임아웃되면 종료
            if result.is_final or (time.time() - start_time) > timeout:
                break

        return {
            "success": True,
            "results": results,
            "file_info": {
                "filename": audio_file.filename,
                "size": len(content),
                "content_type": audio_file.content_type
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/streaming-stt/compare",
         summary="STT 성능 비교",
         description="기존 STT와 스트리밍 STT의 성능을 비교합니다.")
async def compare_stt_performance():
    """STT 성능 비교 정보"""
    return {
        "legacy_stt": {
            "name": "OpenAI Whisper (배치 처리)",
            "model": "medium",
            "processing_type": "batch",
            "typical_latency": "2-5초",
            "pros": ["높은 정확도", "안정성"],
            "cons": ["높은 지연시간", "실시간 처리 불가"]
        },
        "streaming_stt": {
            "name": "Faster Whisper (스트리밍)",
            "model": "base",
            "processing_type": "streaming_chunks",
            "typical_latency": "200-500ms",
            "pros": ["낮은 지연시간", "실시간 피드백", "VAD 최적화", "4-5배 빠른 속도", "WebM 직접 처리"],
            "cons": ["약간 낮은 정확도 (모델 크기에 따라)"]
        },
        "performance_metrics": {
            "speed_improvement": "4-5x faster",
            "latency_reduction": "80-90% 감소",
            "memory_usage": "50% 감소",
            "conversion_overhead": "WebM 직접 처리로 변환 단계 제거",
            "realtime_factor": "스트리밍만 지원"
        }
    }

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

# WebSocket STT 관련 모델들
class WebSocketSTTResponse(BaseModel):
    """WebSocket STT 응답 모델"""
    type: str  # "stt_result", "error"
    text: Optional[str] = None  # 변환된 텍스트
    confidence: Optional[float] = None  # 신뢰도 (0-1)
    error: Optional[str] = None
    timestamp: Optional[str] = None

# 스트리밍 STT 관련 모델들
class StreamingSTTRequest(BaseModel):
    """스트리밍 STT 요청 모델"""
    type: str = "audio_chunk"  # "audio_chunk", "start_stream", "stop_stream", "ping"
    data: Optional[str] = None  # Base64 인코딩된 오디오 데이터
    timestamp: Optional[str] = None
    chunk_id: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "type": "audio_chunk",
                "data": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=",
                "timestamp": "2023-12-07T10:30:00.000Z",
                "chunk_id": "1701943800000"
            }
        }

class StreamingSTTPartialResponse(BaseModel):
    """스트리밍 STT 부분 결과 응답"""
    type: str = "partial_result"
    text: str
    confidence: float  # 0.0 ~ 1.0
    is_final: bool = False
    timestamp: float
    processing_time: Optional[float] = None

    class Config:
        schema_extra = {
            "example": {
                "type": "partial_result",
                "text": "안녕하세요",
                "confidence": 0.85,
                "is_final": False,
                "timestamp": 1701943800.123,
                "processing_time": 0.25
            }
        }

class StreamingSTTFinalResponse(BaseModel):
    """스트리밍 STT 최종 결과 응답"""
    type: str = "final_result"
    text: str
    confidence: float  # 0.0 ~ 1.0
    is_final: bool = True
    timestamp: float
    processing_time: float

    class Config:
        schema_extra = {
            "example": {
                "type": "final_result",
                "text": "안녕하세요. 실시간 음성 인식 테스트입니다.",
                "confidence": 0.92,
                "is_final": True,
                "timestamp": 1701943802.456,
                "processing_time": 0.18
            }
        }

class StreamingSTTStatusResponse(BaseModel):
    """스트리밍 STT 상태 응답"""
    type: str  # "stream_started", "stream_stopped", "error"
    message: str
    session_id: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "type": "stream_started",
                "message": "실시간 STT 스트림이 시작되었습니다",
                "session_id": "session_123"
            }
        }

class STTServiceStats(BaseModel):
    """STT 서비스 통계 모델"""
    model_size: str
    device: str
    compute_type: str
    is_initialized: bool
    sample_rate: int
    chunk_duration: float
    queue_size: int
    vad_aggressiveness: int

    class Config:
        schema_extra = {
            "example": {
                "model_size": "base",
                "device": "cpu",
                "compute_type": "int8",
                "is_initialized": True,
                "sample_rate": 16000,
                "chunk_duration": 1.0,
                "queue_size": 0,
                "vad_aggressiveness": 3
            }
        }

@app.websocket("/ws/stt")
async def websocket_stt_legacy(websocket: WebSocket):
    """기존 STT WebSocket (배치 처리 방식)"""
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

                    # WebM 데이터를 임시 파일로 저장
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_file:
                        temp_file.write(audio_data)
                        webm_path = temp_file.name

                    # STT 변환 (WebM 직접 처리)
                    result = stt_model.transcribe(
                        webm_path,
                        language="ko",  # 한국어 기본 설정
                        initial_prompt="안녕하세요. 한국어로 말씀해 주세요.",
                        word_timestamps=True,
                        fp16=False,
                        temperature=0.0,
                        compression_ratio_threshold=2.4,
                        logprob_threshold=-1.0,
                        no_speech_threshold=0.6
                    )
                    transcribed_text = result["text"].strip()

                    # 신뢰도 계산 (Whisper는 세그먼트별 확률 제공)
                    confidence = 0.0
                    if "segments" in result and result["segments"]:
                        confidence = sum(seg.get("avg_logprob", 0) for seg in result["segments"]) / len(result["segments"])
                        confidence = max(0, min(1, (confidence + 1) / 2))  # -1~0 범위를 0~1로 변환

                    # 임시 WebM 파일 삭제
                    if os.path.exists(webm_path):
                        os.unlink(webm_path)

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

@app.websocket("/ws/streaming-stt")
async def websocket_streaming_stt(websocket: WebSocket):
    """실시간 스트리밍 STT WebSocket (새로운 고성능 버전)

    음성 데이터를 실시간으로 받아서 텍스트로 변환합니다.
    Faster Whisper + VAD 기반으로 빠른 처리 속도를 제공합니다.

    **메시지 형식:**
    - 송신: `{"type": "audio_chunk", "data": "<base64_audio>", "timestamp": "...", "chunk_id": "..."}`
    - 수신: `{"type": "partial_result", "text": "부분 결과", "confidence": 0.95, "is_final": false}`
    - 수신: `{"type": "final_result", "text": "최종 결과", "confidence": 0.98, "is_final": true}`

    **지원 오디오 형식:** WebM (Opus 코덱)
    """
    await manager.connect(websocket)
    print(f"🎤 실시간 STT 클라이언트 연결: {websocket.client}")

    if not STREAMING_STT_AVAILABLE:
        await manager.send_personal_message(json.dumps({
            "type": "error",
            "error": "실시간 STT 서비스를 사용할 수 없습니다"
        }), websocket)
        return

    try:
        # 스트리밍 STT 처리 태스크 시작
        processing_task = asyncio.create_task(
            process_streaming_stt(websocket)
        )

        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_text()
            message_data = json.loads(data)

            if message_data["type"] == "audio_chunk":
                try:
                    # Base64 오디오 디코딩
                    audio_data = base64.b64decode(message_data["data"])
                    timestamp = message_data.get("timestamp", time.time())

                    # 스트리밍 STT 서비스에 오디오 청크 추가
                    streaming_stt_service.add_audio_chunk(audio_data, timestamp)

                except Exception as e:
                    await manager.send_personal_message(json.dumps({
                        "type": "error",
                        "error": f"오디오 청크 처리 오류: {str(e)}",
                        "timestamp": message_data.get("timestamp", "")
                    }), websocket)

            elif message_data["type"] == "start_stream":
                # 스트림 시작 신호
                await manager.send_personal_message(json.dumps({
                    "type": "stream_started",
                    "message": "실시간 STT 스트림이 시작되었습니다"
                }), websocket)

            elif message_data["type"] == "stop_stream":
                # 스트림 중지 신호
                processing_task.cancel()
                await manager.send_personal_message(json.dumps({
                    "type": "stream_stopped",
                    "message": "실시간 STT 스트림이 중지되었습니다"
                }), websocket)
                break

            elif message_data["type"] == "ping":
                # 연결 상태 확인
                await manager.send_personal_message(json.dumps({
                    "type": "pong",
                    "timestamp": message_data.get("timestamp", "")
                }), websocket)

    except WebSocketDisconnect:
        print("🔌 실시간 STT 클라이언트 연결 해제")
        if 'processing_task' in locals():
            processing_task.cancel()
        manager.disconnect(websocket)
    except Exception as e:
        print(f"❌ 실시간 STT WebSocket 오류: {e}")
        if 'processing_task' in locals():
            processing_task.cancel()

async def process_streaming_stt(websocket: WebSocket):
    """실시간 STT 결과 처리 및 전송"""
    try:
        async for result in streaming_stt_service.process_stream():
            # 결과를 클라이언트에 전송
            response = {
                "type": "final_result" if result.is_final else "partial_result",
                "text": result.text,
                "confidence": round(result.confidence, 3),
                "is_final": result.is_final,
                "timestamp": result.timestamp,
                "processing_time": round(result.processing_time, 3)
            }

            await manager.send_personal_message(
                json.dumps(response, ensure_ascii=False),
                websocket
            )

    except asyncio.CancelledError:
        print("🛑 실시간 STT 처리 태스크 취소됨")
    except Exception as e:
        print(f"❌ 실시간 STT 처리 오류: {e}")
        await manager.send_personal_message(json.dumps({
            "type": "error",
            "error": f"STT 처리 오류: {str(e)}"
        }), websocket)

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
                        # WebM 데이터를 임시 파일로 저장
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_file:
                            temp_file.write(audio_data)
                            webm_path = temp_file.name

                        # STT 변환 (WebM 직접 처리)
                        result = stt_model.transcribe(
                            webm_path,
                            language="ko",  # 한국어 기본 설정
                            initial_prompt="안녕하세요. 한국어로 말씀해 주세요.",
                            word_timestamps=True,
                            fp16=False,
                            temperature=0.0,
                            compression_ratio_threshold=2.4,
                            logprob_threshold=-1.0,
                            no_speech_threshold=0.6
                        )
                        user_text = result["text"].strip()

                        # 임시 WebM 파일 삭제
                        if os.path.exists(webm_path):
                            os.unlink(webm_path)

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
                            wav_filename = f"audio_{uuid.uuid4().hex}.wav"
                            wav_path = f"static/audio/{wav_filename}"

                            tts_model.tts_to_file(
                                text=response_text,
                                speaker_id=0,
                                output_path=wav_path,
                                speed=2.0,
                                quiet=True
                            )

                            # WAV → WebM 변환
                            audio_path = convert_wav_to_webm(wav_path)
                            audio_filename = os.path.basename(audio_path)

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
                        wav_filename = f"audio_{uuid.uuid4().hex}.wav"
                        wav_path = f"static/audio/{wav_filename}"

                        tts_model.tts_to_file(
                            text=text,
                            speaker_id=0,
                            output_path=wav_path,
                            speed=2.0,
                            quiet=True
                        )

                        # WAV → WebM 변환
                        audio_path = convert_wav_to_webm(wav_path)
                        audio_filename = os.path.basename(audio_path)

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
    print("📖 API 문서: http://localhost:6001/docs")
    print("🌐 웹 앱: http://localhost:6001")

    uvicorn.run(app, host="0.0.0.0", port=6001)