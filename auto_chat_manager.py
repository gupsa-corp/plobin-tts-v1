#!/usr/bin/env python3
"""
자동 대화 관리 시스템
자동 대화 세션 관리, 스케줄링, 메시지 생성을 담당
"""

import asyncio
import uuid
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import json

from conversation_patterns import conversation_patterns

class AutoChatSession:
    """개별 자동 대화 세션을 관리하는 클래스"""

    def __init__(self, websocket, theme: str = "casual", interval: int = 30):
        self.session_id = str(uuid.uuid4())
        self.websocket = websocket
        self.theme = theme
        self.interval = interval  # 초 단위
        self.is_active = False
        self.last_message_time = time.time()
        self.message_count = 0
        self.user_responses = []  # 사용자 응답 기록
        self.created_at = datetime.now()

    def should_send_message(self) -> bool:
        """메시지를 보낼 시간인지 확인"""
        return (time.time() - self.last_message_time) >= self.interval

    def update_last_message_time(self):
        """마지막 메시지 시간 업데이트"""
        self.last_message_time = time.time()
        self.message_count += 1

    def add_user_response(self, response: str):
        """사용자 응답 기록"""
        self.user_responses.append({
            "text": response,
            "timestamp": datetime.now().isoformat()
        })
        # 최근 10개만 유지
        if len(self.user_responses) > 10:
            self.user_responses = self.user_responses[-10:]

class AutoChatManager:
    """자동 대화 시스템 전체를 관리하는 클래스"""

    def __init__(self):
        self.active_sessions: Dict[str, AutoChatSession] = {}
        self.background_task = None
        self.is_running = False

    async def start_auto_chat(self, websocket, theme: str = "casual", interval: int = 30) -> str:
        """새로운 자동 대화 세션 시작"""
        # 기존 세션이 있다면 중지
        await self.stop_auto_chat_for_websocket(websocket)

        # 새 세션 생성
        session = AutoChatSession(websocket, theme, interval)
        session.is_active = True
        self.active_sessions[session.session_id] = session

        # 백그라운드 태스크 시작 (아직 없다면)
        if not self.is_running:
            await self.start_background_task()

        # 시작 메시지 즉시 전송
        await self.send_auto_message(session)

        return session.session_id

    async def stop_auto_chat(self, session_id: str) -> bool:
        """특정 세션의 자동 대화 중지"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            session.is_active = False

            # WebSocket으로 중지 알림 전송
            await self.send_websocket_message(session.websocket, {
                "type": "auto_chat_stop",
                "session_id": session_id,
                "message": "자동 대화가 중지되었습니다."
            })

            del self.active_sessions[session_id]
            return True
        return False

    async def stop_auto_chat_for_websocket(self, websocket) -> bool:
        """특정 WebSocket의 모든 자동 대화 세션 중지"""
        sessions_to_remove = []
        for session_id, session in self.active_sessions.items():
            if session.websocket == websocket:
                sessions_to_remove.append(session_id)

        for session_id in sessions_to_remove:
            await self.stop_auto_chat(session_id)

        return len(sessions_to_remove) > 0

    async def pause_auto_chat(self, session_id: str, duration: int = 60):
        """자동 대화 일시 중지 (사용자가 말할 때)"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            # 마지막 메시지 시간을 현재 + duration으로 설정
            session.last_message_time = time.time() + duration

    async def handle_user_input(self, websocket, user_text: str):
        """사용자 입력 처리 및 자동 대화 조정"""
        # 해당 WebSocket의 활성 세션 찾기
        for session in self.active_sessions.values():
            if session.websocket == websocket and session.is_active:
                # 사용자 응답 기록
                session.add_user_response(user_text)

                # 잠시 자동 대화 중지 (사용자가 말하고 있으므로)
                await self.pause_auto_chat(session.session_id, 90)  # 90초 대기

                # 사용자 입력에 대한 적절한 응답 생성 및 전송
                await self.send_contextual_response(session, user_text)
                break

    async def send_contextual_response(self, session: AutoChatSession, user_input: str):
        """사용자 입력에 대한 맥락적 응답 전송"""
        response_text = conversation_patterns.get_response_to_input(user_input)

        # 추가 질문이나 대화 연결
        if session.message_count > 0:  # 첫 메시지가 아니라면
            follow_up = conversation_patterns.get_themed_message(session.theme)
            response_text += f" {follow_up}"

        await self.send_auto_message_with_text(session, response_text)

    async def send_auto_message(self, session: AutoChatSession):
        """자동 메시지 생성 및 전송"""
        # 상황에 맞는 메시지 생성
        if session.message_count == 0:  # 첫 메시지
            message_text = conversation_patterns.get_themed_message("greeting")
        else:
            message_text = conversation_patterns.get_contextual_message(
                theme=session.theme,
                include_time=True
            )

        await self.send_auto_message_with_text(session, message_text)

    async def send_auto_message_with_text(self, session: AutoChatSession, message_text: str):
        """지정된 텍스트로 자동 메시지 전송"""
        try:
            # TTS 변환을 위한 메시지 전송
            message_data = {
                "type": "auto_chat_message",
                "session_id": session.session_id,
                "text": message_text,
                "timestamp": datetime.now().isoformat(),
                "theme": session.theme,
                "message_count": session.message_count + 1
            }

            await self.send_websocket_message(session.websocket, message_data)
            session.update_last_message_time()

        except Exception as e:
            print(f"자동 메시지 전송 오류: {e}")
            # 연결이 끊어진 세션 제거
            if session.session_id in self.active_sessions:
                del self.active_sessions[session.session_id]

    async def send_websocket_message(self, websocket, data: Dict[str, Any]):
        """WebSocket 메시지 전송"""
        try:
            await websocket.send_text(json.dumps(data, ensure_ascii=False))
        except Exception as e:
            print(f"WebSocket 메시지 전송 실패: {e}")
            raise

    async def start_background_task(self):
        """백그라운드 자동 대화 태스크 시작"""
        if not self.is_running:
            self.is_running = True
            self.background_task = asyncio.create_task(self.auto_chat_loop())

    async def stop_background_task(self):
        """백그라운드 태스크 중지"""
        self.is_running = False
        if self.background_task:
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                pass

    async def auto_chat_loop(self):
        """자동 대화 백그라운드 루프"""
        while self.is_running:
            try:
                # 모든 활성 세션 확인
                sessions_to_process = list(self.active_sessions.values())

                for session in sessions_to_process:
                    if session.is_active and session.should_send_message():
                        await self.send_auto_message(session)

                # 5초마다 확인
                await asyncio.sleep(5)

            except Exception as e:
                print(f"자동 대화 루프 오류: {e}")
                await asyncio.sleep(5)

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 정보 조회"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            return {
                "session_id": session.session_id,
                "theme": session.theme,
                "interval": session.interval,
                "is_active": session.is_active,
                "message_count": session.message_count,
                "created_at": session.created_at.isoformat(),
                "last_message_time": session.last_message_time,
                "user_responses_count": len(session.user_responses)
            }
        return None

    def get_all_sessions_info(self) -> Dict[str, Any]:
        """모든 세션 정보 조회"""
        return {
            "total_sessions": len(self.active_sessions),
            "sessions": [self.get_session_info(sid) for sid in self.active_sessions.keys()],
            "available_themes": conversation_patterns.get_all_themes()
        }

    async def update_session_settings(self, session_id: str, theme: Optional[str] = None,
                                    interval: Optional[int] = None) -> bool:
        """세션 설정 업데이트"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]

            if theme is not None:
                session.theme = theme
            if interval is not None:
                session.interval = max(10, min(300, interval))  # 10초~5분 제한

            # 설정 변경 알림
            await self.send_websocket_message(session.websocket, {
                "type": "auto_chat_settings_updated",
                "session_id": session_id,
                "theme": session.theme,
                "interval": session.interval
            })

            return True
        return False

# 전역 인스턴스
auto_chat_manager = AutoChatManager()