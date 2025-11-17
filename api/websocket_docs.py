#!/usr/bin/env python3
"""
WebSocket 문서화 API 엔드포인트 모듈
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any

# WebSocket 관련 문서화 모델들
class WebSocketEndpoint(BaseModel):
    path: str
    name: str
    description: str
    connection_url: str
    message_formats: Dict[str, Any]
    examples: Dict[str, Any]

class WebSocketMessage(BaseModel):
    type: str
    description: str
    example: Dict[str, Any]

class WebSocketDocumentation(BaseModel):
    overview: str
    endpoints: List[WebSocketEndpoint]
    common_patterns: Dict[str, str]
    error_handling: Dict[str, str]
    connection_guide: List[str]

# API 라우터 생성
router = APIRouter(prefix="/api/websocket", tags=["🔌 WebSocket 문서"])

@router.get("/docs", response_model=WebSocketDocumentation,
            summary="📡 WebSocket 완전 문서",
            description="""
## 🔌 WebSocket 엔드포인트 완전 가이드

FastAPI Swagger는 WebSocket을 기본 지원하지 않으므로,
이 엔드포인트에서 모든 WebSocket 관련 정보를 제공합니다.

### 📋 포함 내용:
- 사용 가능한 모든 WebSocket 엔드포인트
- 메시지 형식 및 예제 코드
- 연결 방법 및 오류 처리
- JavaScript 클라이언트 예제

### 🚀 빠른 시작:
1. 이 문서에서 원하는 WebSocket 엔드포인트 확인
2. JavaScript 예제 코드 복사
3. 브라우저 콘솔이나 테스트 페이지에서 실행
            """)
async def get_websocket_documentation():
    """WebSocket 엔드포인트 완전 문서"""
    return WebSocketDocumentation(
        overview="""
🔌 실시간 음성 처리를 위한 WebSocket API

이 시스템은 실시간 STT(음성→텍스트), TTS(텍스트→음성),
그리고 통합 음성 대화를 위한 3개의 WebSocket 엔드포인트를 제공합니다.

모든 WebSocket은 JSON 메시지 형식을 사용하며,
오디오 데이터는 Base64로 인코딩하여 전송합니다.
        """,
        endpoints=[
            WebSocketEndpoint(
                path="/ws/stt",
                name="실시간 STT (음성 → 텍스트)",
                description="음성을 실시간으로 텍스트로 변환합니다. 한국어 최적화 및 노이즈 제거 기능 포함.",
                connection_url="ws://localhost:40003/ws/stt",
                message_formats={
                    "send": {
                        "audio": {
                            "type": "audio",
                            "data": "<base64_encoded_audio>",
                            "timestamp": "2025-01-01T00:00:00Z"
                        },
                        "ping": {
                            "type": "ping",
                            "timestamp": "2025-01-01T00:00:00Z"
                        }
                    },
                    "receive": {
                        "stt_result": {
                            "type": "stt_result",
                            "text": "변환된 텍스트",
                            "confidence": 0.95,
                            "timestamp": "2025-01-01T00:00:00Z"
                        },
                        "pong": {
                            "type": "pong",
                            "timestamp": "2025-01-01T00:00:00Z"
                        },
                        "error": {
                            "type": "error",
                            "error": "오류 메시지",
                            "timestamp": "2025-01-01T00:00:00Z"
                        }
                    }
                },
                examples={
                    "javascript": """
// WebSocket 연결
const ws = new WebSocket('ws://localhost:40003/ws/stt');

// 연결 성공
ws.onopen = () => {
    console.log('STT WebSocket 연결됨');

    // 핑 테스트
    ws.send(JSON.stringify({
        type: 'ping',
        timestamp: new Date().toISOString()
    }));
};

// 메시지 수신
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'stt_result') {
        console.log('인식된 텍스트:', data.text);
        console.log('신뢰도:', data.confidence);
    } else if (data.type === 'pong') {
        console.log('연결 정상');
    } else if (data.type === 'error') {
        console.error('STT 오류:', data.error);
    }
};

// 오디오 녹음 및 전송 (MediaRecorder API 사용)
navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
        const mediaRecorder = new MediaRecorder(stream);
        const audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            const reader = new FileReader();

            reader.onload = () => {
                const base64Audio = reader.result.split(',')[1];

                // STT 요청 전송
                ws.send(JSON.stringify({
                    type: 'audio',
                    data: base64Audio,
                    timestamp: new Date().toISOString()
                }));
            };

            reader.readAsDataURL(audioBlob);
        };

        // 3초간 녹음
        mediaRecorder.start();
        setTimeout(() => mediaRecorder.stop(), 3000);
    });
                    """
                }
            ),

            WebSocketEndpoint(
                path="/ws/chat",
                name="실시간 음성 대화 (STT + TTS)",
                description="음성 입력을 받아 텍스트로 변환하고, 자동 응답을 음성으로 출력하는 완전 자동화된 대화 시스템입니다.",
                connection_url="ws://localhost:40003/ws/chat",
                message_formats={
                    "send": {
                        "audio": {
                            "type": "audio",
                            "data": "<base64_encoded_audio>",
                            "timestamp": "2025-01-01T00:00:00Z"
                        },
                        "auto_chat_start": {
                            "type": "auto_chat_start",
                            "theme": "casual",
                            "interval": 30
                        },
                        "auto_chat_stop": {
                            "type": "auto_chat_stop"
                        }
                    },
                    "receive": {
                        "user_message": {
                            "type": "user_message",
                            "text": "사용자가 말한 내용",
                            "timestamp": "2025-01-01T00:00:00Z"
                        },
                        "system_response": {
                            "type": "system_response",
                            "text": "시스템 응답",
                            "audio_url": "/static/audio/response.wav",
                            "timestamp": "2025-01-01T00:00:00Z"
                        },
                        "auto_chat_started": {
                            "type": "auto_chat_started",
                            "session_id": "uuid",
                            "theme": "casual",
                            "interval": 30,
                            "message": "자동 대화가 시작되었습니다."
                        }
                    }
                },
                examples={
                    "javascript": """
// WebSocket 연결
const ws = new WebSocket('ws://localhost:40003/ws/chat');

// 연결 성공
ws.onopen = () => {
    console.log('음성 대화 WebSocket 연결됨');
};

// 메시지 수신
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'user_message') {
        console.log('사용자:', data.text);

    } else if (data.type === 'system_response') {
        console.log('시스템:', data.text);

        // 음성 응답 재생
        if (data.audio_url) {
            const audio = new Audio(data.audio_url);
            audio.play();
        }

    } else if (data.type === 'auto_chat_started') {
        console.log('자동 대화 시작:', data.session_id);

    } else if (data.type === 'error') {
        console.error('대화 오류:', data.message);
    }
};

// 자동 대화 시작
function startAutoChat() {
    ws.send(JSON.stringify({
        type: 'auto_chat_start',
        theme: 'casual',
        interval: 30
    }));
}

// 음성 녹음 및 대화 (위의 STT 예제와 동일한 방식)
// ...
                    """
                }
            )
        ],
        common_patterns={
            "connection": "모든 WebSocket은 ws://localhost:40003/ws/<endpoint> 형식으로 연결",
            "message_format": "JSON 형식 메시지, 'type' 필드로 메시지 구분",
            "audio_encoding": "오디오 데이터는 Base64로 인코딩하여 'data' 필드에 전송",
            "error_handling": "모든 오류는 {type: 'error', error: '메시지'} 형식으로 응답",
            "timestamps": "선택적 timestamp 필드로 메시지 시간 추적 가능"
        },
        error_handling={
            "connection_failed": "네트워크 오류 또는 서버 다운 - 재연결 시도",
            "model_not_loaded": "STT/TTS 모델 로딩 실패 - /api/health로 상태 확인",
            "invalid_audio": "오디오 형식 오류 - WAV/MP3 형식 사용 권장",
            "json_parse_error": "메시지 형식 오류 - JSON 문법 확인"
        },
        connection_guide=[
            "1. /api/health 엔드포인트로 서버 상태 확인",
            "2. WebSocket 연결: new WebSocket('ws://localhost:40003/ws/<endpoint>')",
            "3. onopen 이벤트에서 연결 확인",
            "4. JSON 형식으로 메시지 송수신",
            "5. 오류 처리를 위한 onerror 및 onclose 이벤트 핸들러 구현"
        ]
    )

@router.get("/endpoints",
            summary="🔗 WebSocket 엔드포인트 목록",
            description="사용 가능한 모든 WebSocket 엔드포인트의 간단한 목록입니다.")
async def get_websocket_endpoints():
    """WebSocket 엔드포인트 목록"""
    return {
        "websocket_endpoints": [
            {
                "path": "/ws/stt",
                "name": "실시간 STT",
                "url": "ws://localhost:40003/ws/stt",
                "description": "음성을 실시간으로 텍스트로 변환"
            },
            {
                "path": "/ws/chat",
                "name": "실시간 음성 대화",
                "url": "ws://localhost:40003/ws/chat",
                "description": "STT + TTS 통합 음성 대화 시스템"
            }
        ],
        "documentation": "/api/websocket/docs",
        "test_page": "/test",
        "note": "FastAPI Swagger는 WebSocket을 지원하지 않으므로 이 엔드포인트들에서 상세 정보를 확인하세요."
    }

@router.get("/examples/{endpoint}",
            summary="💡 WebSocket 예제 코드",
            description="특정 WebSocket 엔드포인트의 사용 예제를 반환합니다.")
async def get_websocket_examples(endpoint: str):
    """WebSocket 사용 예제"""

    examples = {
        "stt": {
            "description": "실시간 STT WebSocket 사용 예제",
            "javascript": """
// 실시간 STT 연결
const sttSocket = new WebSocket('ws://localhost:40003/ws/stt');

sttSocket.onopen = () => console.log('STT 연결됨');

sttSocket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'stt_result') {
        document.getElementById('transcript').textContent = data.text;
    }
};

// 마이크 녹음 및 전송
navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
        const mediaRecorder = new MediaRecorder(stream);
        const audioChunks = [];

        mediaRecorder.ondataavailable = event => audioChunks.push(event.data);
        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            const reader = new FileReader();
            reader.onload = () => {
                const base64Audio = reader.result.split(',')[1];
                sttSocket.send(JSON.stringify({
                    type: 'audio',
                    data: base64Audio,
                    timestamp: new Date().toISOString()
                }));
            };
            reader.readAsDataURL(audioBlob);
        };

        mediaRecorder.start();
        setTimeout(() => mediaRecorder.stop(), 3000); // 3초 녹음
    });
            """,
            "html": """
<!DOCTYPE html>
<html>
<head>
    <title>실시간 STT 테스트</title>
</head>
<body>
    <h1>실시간 STT 테스트</h1>
    <button onclick="startRecording()">🎤 녹음 시작</button>
    <div id="transcript">인식된 텍스트가 여기에 표시됩니다...</div>

    <script>
        // 위의 JavaScript 코드 삽입
    </script>
</body>
</html>
            """
        },

        "chat": {
            "description": "실시간 음성 대화 WebSocket 사용 예제",
            "javascript": """
// 실시간 음성 대화 연결
const chatSocket = new WebSocket('ws://localhost:40003/ws/chat');

chatSocket.onopen = () => console.log('음성 대화 연결됨');

chatSocket.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'user_message') {
        addMessage('사용자', data.text);

    } else if (data.type === 'system_response') {
        addMessage('시스템', data.text);

        // 음성 응답 자동 재생
        if (data.audio_url) {
            const audio = new Audio(data.audio_url);
            audio.play();
        }
    }
};

function addMessage(speaker, text) {
    const chatDiv = document.getElementById('chat');
    const messageDiv = document.createElement('div');
    messageDiv.innerHTML = `<strong>${speaker}:</strong> ${text}`;
    chatDiv.appendChild(messageDiv);
}

// 자동 대화 시작
function startAutoChat() {
    chatSocket.send(JSON.stringify({
        type: 'auto_chat_start',
        theme: 'casual',
        interval: 30
    }));
}
            """,
            "html": """
<!DOCTYPE html>
<html>
<head>
    <title>실시간 음성 대화</title>
</head>
<body>
    <h1>실시간 음성 대화</h1>
    <button onclick="startRecording()">🎤 말하기</button>
    <button onclick="startAutoChat()">🤖 자동 대화 시작</button>
    <div id="chat" style="border: 1px solid #ccc; height: 300px; padding: 10px; overflow-y: scroll;">
        대화 내용이 여기에 표시됩니다...
    </div>

    <script>
        // 위의 JavaScript 코드 삽입
    </script>
</body>
</html>
            """
        }
    }

    if endpoint in examples:
        return examples[endpoint]
    else:
        return {
            "error": f"엔드포인트 '{endpoint}'에 대한 예제를 찾을 수 없습니다.",
            "available_endpoints": list(examples.keys())
        }