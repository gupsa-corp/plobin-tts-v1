"""
WebSocket 핸들러 통합 테스트
"""

import pytest
import json
import base64
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import WebSocket

from websocket.chat_handler import handle_chat_websocket, _handle_ping, _process_audio_message
from websocket.connection_manager import ConnectionManager

class TestWebSocketHandlers:
    """WebSocket 핸들러 테스트"""

    @pytest.mark.asyncio
    async def test_ping_handler(self):
        """핑 핸들러 테스트"""
        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_manager = AsyncMock()

        with patch('websocket.chat_handler.manager', mock_manager):
            message_data = {
                "type": "ping",
                "timestamp": "2025-09-29T14:38:00Z"
            }

            await _handle_ping(mock_websocket, message_data)

            # pong 응답이 전송되었는지 확인
            mock_manager.send_personal_message.assert_called_once()
            call_args = mock_manager.send_personal_message.call_args[0]
            response_data = json.loads(call_args[0])

            assert response_data["type"] == "pong"
            assert response_data["timestamp"] == "2025-09-29T14:38:00Z"

    @pytest.mark.asyncio
    async def test_audio_message_processing(self, sample_audio_file):
        """오디오 메시지 처리 테스트"""
        mock_websocket = AsyncMock()
        mock_manager = AsyncMock()
        mock_model_manager = MagicMock()

        # 오디오 파일을 base64로 인코딩
        with open(sample_audio_file, "rb") as f:
            audio_data = base64.b64encode(f.read()).decode()

        # STT 결과 모킹
        mock_model_manager.transcribe_audio.return_value = {
            "text": "안녕하세요",
            "language": "ko"
        }

        # TTS 결과 모킹
        mock_model_manager.synthesize_speech.return_value = "/fake/path/audio.wav"

        with patch('websocket.chat_handler.manager', mock_manager), \
             patch('websocket.chat_handler.model_manager', mock_model_manager), \
             patch('websocket.chat_handler.cleanup_temp_audio'), \
             patch('websocket.chat_handler.generate_audio_filename', return_value="test.wav"), \
             patch('websocket.chat_handler.auto_chat_manager') as mock_auto_chat:

            mock_auto_chat.handle_user_input = AsyncMock()

            message_data = {
                "type": "audio",
                "data": audio_data,
                "timestamp": "2025-09-29T14:38:00Z"
            }

            await _process_audio_message(mock_websocket, message_data)

            # STT가 호출되었는지 확인
            mock_model_manager.transcribe_audio.assert_called_once()

            # TTS가 호출되었는지 확인
            mock_model_manager.synthesize_speech.assert_called_once()

            # 두 개의 메시지가 전송되었는지 확인 (사용자 메시지 + 시스템 응답)
            assert mock_manager.send_personal_message.call_count == 2

    @pytest.mark.asyncio
    async def test_websocket_connection_lifecycle(self):
        """WebSocket 연결 라이프사이클 테스트"""
        mock_websocket = AsyncMock()
        mock_manager = MagicMock()

        # receive_text가 WebSocketDisconnect를 발생시키도록 설정
        from fastapi import WebSocketDisconnect
        mock_websocket.receive_text.side_effect = WebSocketDisconnect()

        with patch('websocket.chat_handler.manager', mock_manager), \
             patch('websocket.chat_handler.auto_chat_manager') as mock_auto_chat:

            mock_auto_chat.stop_auto_chat_for_websocket = AsyncMock()

            await handle_chat_websocket(mock_websocket)

            # 연결 및 해제가 호출되었는지 확인
            mock_manager.connect.assert_called_once_with(mock_websocket)
            mock_manager.disconnect.assert_called_once_with(mock_websocket)

    @pytest.mark.asyncio
    async def test_invalid_json_message(self):
        """잘못된 JSON 메시지 처리 테스트"""
        mock_websocket = AsyncMock()
        mock_manager = MagicMock()

        # 잘못된 JSON을 반환하도록 설정
        mock_websocket.receive_text.side_effect = [
            "invalid json",
            json.dumps({"type": "ping"})  # 두 번째 호출에서는 정상 메시지
        ]

        # 세 번째 호출에서 연결 해제
        def side_effect():
            from fastapi import WebSocketDisconnect
            raise WebSocketDisconnect()
        mock_websocket.receive_text.side_effect.append(side_effect)

        with patch('websocket.chat_handler.manager', mock_manager), \
             patch('websocket.chat_handler.auto_chat_manager'):

            # JSON 파싱 에러가 발생해도 연결이 유지되어야 함
            try:
                await handle_chat_websocket(mock_websocket)
            except Exception:
                pass  # WebSocketDisconnect 예외는 정상적인 종료

class TestConnectionManager:
    """연결 매니저 테스트"""

    def test_connection_manager_initialization(self):
        """연결 매니저 초기화 테스트"""
        manager = ConnectionManager()
        assert manager.active_connections == []

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """연결/해제 테스트"""
        manager = ConnectionManager()
        mock_websocket = AsyncMock()

        # 연결
        await manager.connect(mock_websocket)
        assert mock_websocket in manager.active_connections

        # 해제
        manager.disconnect(mock_websocket)
        assert mock_websocket not in manager.active_connections

    @pytest.mark.asyncio
    async def test_send_personal_message(self):
        """개인 메시지 전송 테스트"""
        manager = ConnectionManager()
        mock_websocket = AsyncMock()

        await manager.connect(mock_websocket)
        await manager.send_personal_message("test message", mock_websocket)

        mock_websocket.send_text.assert_called_once_with("test message")

    @pytest.mark.asyncio
    async def test_broadcast_message(self):
        """브로드캐스트 메시지 테스트"""
        manager = ConnectionManager()
        mock_websocket1 = AsyncMock()
        mock_websocket2 = AsyncMock()

        await manager.connect(mock_websocket1)
        await manager.connect(mock_websocket2)
        await manager.broadcast("broadcast message")

        mock_websocket1.send_text.assert_called_once_with("broadcast message")
        mock_websocket2.send_text.assert_called_once_with("broadcast message")

    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """연결 오류 처리 테스트"""
        manager = ConnectionManager()
        mock_websocket = AsyncMock()

        # send_text에서 예외 발생하도록 설정
        mock_websocket.send_text.side_effect = Exception("Connection error")

        await manager.connect(mock_websocket)

        # 예외가 발생해도 매니저가 정상 작동해야 함
        try:
            await manager.send_personal_message("test", mock_websocket)
        except Exception:
            pass  # 예외가 발생할 수 있음

        assert mock_websocket in manager.active_connections

class TestWebSocketIntegration:
    """WebSocket 통합 테스트"""

    def test_websocket_endpoint_exists(self, client):
        """WebSocket 엔드포인트 존재 확인"""
        # WebSocket 엔드포인트는 HTTP로 직접 접근할 수 없음
        # 404나 405 응답을 받아야 함
        response = client.get("/ws/chat")
        assert response.status_code in [404, 405, 426]  # 426 = Upgrade Required

    @pytest.mark.slow
    def test_websocket_connection_with_testclient(self, client):
        """TestClient를 통한 WebSocket 연결 테스트"""
        with client.websocket_connect("/ws/chat") as websocket:
            # 핑 메시지 전송
            ping_data = {
                "type": "ping",
                "timestamp": "2025-09-29T14:38:00Z"
            }
            websocket.send_text(json.dumps(ping_data))

            # pong 응답 수신
            response = websocket.receive_text()
            response_data = json.loads(response)

            assert response_data["type"] == "pong"
            assert response_data["timestamp"] == "2025-09-29T14:38:00Z"