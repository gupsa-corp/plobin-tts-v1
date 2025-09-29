#!/usr/bin/env python3
"""
STT 전용 WebSocket 핸들러
"""

import json
import base64
import tempfile
from fastapi import WebSocket, WebSocketDisconnect

from models.model_manager import model_manager
from websocket.connection_manager import manager
from utils.audio_processing import cleanup_temp_audio

async def handle_stt_websocket(websocket: WebSocket):
    """실시간 STT 전용 WebSocket 핸들러"""
    await manager.connect(websocket)

    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_text()
            message_data = json.loads(data)

            if message_data["type"] == "audio":
                await _process_audio_message(websocket, message_data)
            elif message_data["type"] == "ping":
                await _handle_ping(websocket, message_data)

    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def _process_audio_message(websocket: WebSocket, message_data: dict):
    """오디오 메시지 처리"""
    try:
        # Base64 오디오 디코딩
        audio_data = base64.b64decode(message_data["data"])

        # STT 처리
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name

        result = model_manager.transcribe_audio(temp_path)
        transcribed_text = result["text"].strip()

        # 신뢰도 계산 (Whisper는 세그먼트별 확률 제공)
        confidence = 0.0
        if "segments" in result and result["segments"]:
            confidence = sum(seg.get("avg_logprob", 0) for seg in result["segments"]) / len(result["segments"])
            confidence = max(0, min(1, (confidence + 1) / 2))  # -1~0 범위를 0~1로 변환

        # 임시 파일 정리
        cleanup_temp_audio(temp_path)

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

async def _handle_ping(websocket: WebSocket, message_data: dict):
    """연결 상태 확인 처리"""
    await manager.send_personal_message(json.dumps({
        "type": "pong",
        "timestamp": message_data.get("timestamp", "")
    }), websocket)