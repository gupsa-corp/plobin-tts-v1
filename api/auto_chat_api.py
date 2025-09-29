#!/usr/bin/env python3
"""
자동 대화 API 엔드포인트 모듈
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

# 자동 대화 관련 임포트
from auto_chat_manager import auto_chat_manager
from conversation_patterns import conversation_patterns

# 요청/응답 모델
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

# API 라우터 생성
router = APIRouter(prefix="/api/auto-chat", tags=["자동 대화"])

@router.get("/themes",
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

@router.get("/sessions",
            summary="자동 대화 세션 정보",
            description="현재 활성화된 자동 대화 세션들의 정보를 반환합니다.")
async def get_auto_chat_sessions():
    """자동 대화 세션 정보 조회"""
    return auto_chat_manager.get_all_sessions_info()

@router.get("/sessions/{session_id}",
            summary="특정 자동 대화 세션 정보",
            description="특정 자동 대화 세션의 상세 정보를 반환합니다.")
async def get_auto_chat_session(session_id: str):
    """특정 자동 대화 세션 정보 조회"""
    session_info = auto_chat_manager.get_session_info(session_id)
    if session_info:
        return session_info
    else:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")