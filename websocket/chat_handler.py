#!/usr/bin/env python3
"""
음성 대화 WebSocket 핸들러
"""

import json
import base64
import tempfile
import os
from fastapi import WebSocket, WebSocketDisconnect

from models.model_manager import model_manager
from websocket.connection_manager import manager
from utils.audio_processing import cleanup_temp_audio, generate_audio_filename
from config.settings import AUDIO_DIR

# 자동 대화 관련 임포트
from auto_chat_manager import auto_chat_manager

async def handle_chat_websocket(websocket: WebSocket):
    """실시간 음성 대화 WebSocket 핸들러"""
    await manager.connect(websocket)

    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_text()
            message_data = json.loads(data)

            message_type = message_data["type"]

            if message_type == "ping":
                await _handle_ping(websocket, message_data)
            elif message_type == "audio":
                await _process_audio_message(websocket, message_data)
            elif message_type == "auto_chat_start":
                await _handle_auto_chat_start(websocket, message_data)
            elif message_type == "auto_chat_stop":
                await _handle_auto_chat_stop(websocket, message_data)
            elif message_type == "auto_chat_message":
                await _handle_auto_chat_message(websocket, message_data)

    except WebSocketDisconnect:
        # 연결이 끊어질 때 자동 대화도 정리
        await auto_chat_manager.stop_auto_chat_for_websocket(websocket)
        manager.disconnect(websocket)

async def _handle_ping(websocket: WebSocket, message_data: dict):
    """핑 메시지 처리 - pong 응답"""
    try:
        await manager.send_personal_message(json.dumps({
            "type": "pong",
            "timestamp": message_data.get("timestamp", ""),
            "server_time": json.dumps({"current_time": str(__import__('datetime').datetime.now())})
        }), websocket)
    except Exception as e:
        await manager.send_personal_message(json.dumps({
            "type": "error",
            "message": f"핑 처리 오류: {str(e)}"
        }), websocket)

async def _process_audio_message(websocket: WebSocket, message_data: dict):
    """오디오 메시지 처리 (STT -> 응답 생성 -> TTS)"""
    try:
        # Base64 오디오 디코딩
        audio_data = base64.b64decode(message_data["data"])

        # STT 처리
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name

        result = model_manager.transcribe_audio(temp_path)
        user_text = result["text"].strip()
        cleanup_temp_audio(temp_path)

        # 사용자 메시지 전송
        await manager.send_personal_message(json.dumps({
            "type": "user_message",
            "text": user_text,
            "timestamp": message_data.get("timestamp", "")
        }), websocket)

        # 자동 대화 매니저에 사용자 입력 알림
        await auto_chat_manager.handle_user_input(websocket, user_text)

        # 간단한 응답 생성 (실제로는 AI 모델 연동 가능)
        response_text = _generate_response(user_text)

        # TTS 변환
        audio_filename = generate_audio_filename()
        audio_path = os.path.join(AUDIO_DIR, audio_filename)

        model_manager.synthesize_speech(
            text=response_text,
            output_path=audio_path,
            speed=2.0
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

async def _handle_auto_chat_start(websocket: WebSocket, message_data: dict):
    """자동 대화 시작 요청 처리"""
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

async def _handle_auto_chat_stop(websocket: WebSocket, message_data: dict):
    """자동 대화 중지 요청 처리"""
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

async def _handle_auto_chat_message(websocket: WebSocket, message_data: dict):
    """자동 대화 메시지를 TTS로 변환"""
    try:
        text = message_data.get("text", "")
        if text:
            audio_filename = generate_audio_filename()
            audio_path = os.path.join(AUDIO_DIR, audio_filename)

            model_manager.synthesize_speech(
                text=text,
                output_path=audio_path,
                speed=2.0
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

def _generate_response(user_text: str) -> str:
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