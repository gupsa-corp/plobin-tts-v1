#!/usr/bin/env python3
"""
WebSocket 연결 관리 모듈
"""

from typing import List
from fastapi import WebSocket

class ConnectionManager:
    """WebSocket 연결 관리자"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """클라이언트 연결"""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """클라이언트 연결 해제"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """개별 클라이언트에게 메시지 전송"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"메시지 전송 오류: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        """모든 연결된 클라이언트에게 브로드캐스트"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"브로드캐스트 오류: {e}")
                disconnected.append(connection)

        # 연결이 끊어진 클라이언트 정리
        for connection in disconnected:
            self.disconnect(connection)

    def get_connection_count(self) -> int:
        """현재 연결된 클라이언트 수"""
        return len(self.active_connections)

# 전역 연결 매니저 인스턴스
manager = ConnectionManager()