#!/usr/bin/env python3
"""
WebSocket 기능 테스트
"""

import asyncio
import json
import aiohttp
import sys
import time

async def test_websocket_connection():
    """WebSocket 연결 및 기능 테스트"""
    print("🔌 WebSocket 기능 테스트")
    print("=" * 40)

    # WebSocket 엔드포인트 테스트
    endpoints = [
        ("ws://localhost:40003/ws/chat", "음성 대화"),
        ("ws://localhost:40003/ws/stt", "STT 전용")
    ]

    for ws_url, description in endpoints:
        print(f"\n📡 {description} ({ws_url})")
        await test_websocket_endpoint(ws_url, description)

async def test_websocket_endpoint(ws_url, description):
    """개별 WebSocket 엔드포인트 테스트"""
    try:
        session = aiohttp.ClientSession()

        # WebSocket 연결
        async with session.ws_connect(ws_url, timeout=aiohttp.ClientTimeout(total=10)) as ws:
            print(f"   ✅ 연결 성공")

            # 1. 핑 테스트
            ping_message = {
                "type": "ping",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }

            await ws.send_str(json.dumps(ping_message))
            print(f"   📤 핑 메시지 전송: {ping_message['type']}")

            # 응답 대기 (최대 5초)
            try:
                async with asyncio.timeout(5):
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            response = json.loads(msg.data)
                            print(f"   📨 응답 수신: {response.get('type', 'unknown')}")

                            if response.get('type') == 'pong':
                                print(f"   ✅ 핑/퐁 테스트 성공")
                                break
                            elif response.get('type') == 'error':
                                print(f"   ❌ 서버 오류: {response.get('message', '알 수 없는 오류')}")
                                break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            print(f"   ❌ WebSocket 오류: {ws.exception()}")
                            break

            except asyncio.TimeoutError:
                print(f"   ⏰ 응답 타임아웃 (5초)")

        await session.close()

    except aiohttp.ClientConnectionError as e:
        print(f"   ❌ 연결 실패: {e}")
    except Exception as e:
        print(f"   ❌ 오류: {e}")

async def test_chat_websocket_features():
    """채팅 WebSocket 고급 기능 테스트"""
    print(f"\n🎯 채팅 WebSocket 고급 기능 테스트")
    print("-" * 30)

    try:
        session = aiohttp.ClientSession()
        ws_url = "ws://localhost:40003/ws/chat"

        async with session.ws_connect(ws_url, timeout=aiohttp.ClientTimeout(total=10)) as ws:
            print(f"   ✅ 연결 성공")

            # 자동 대화 시작 테스트
            auto_chat_message = {
                "type": "auto_chat_start",
                "theme": "casual",
                "interval": 30
            }

            await ws.send_str(json.dumps(auto_chat_message))
            print(f"   📤 자동 대화 시작 요청")

            # 응답 확인
            try:
                async with asyncio.timeout(5):
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            response = json.loads(msg.data)
                            msg_type = response.get('type', 'unknown')
                            print(f"   📨 응답: {msg_type}")

                            if msg_type == 'auto_chat_started':
                                session_id = response.get('session_id', '')
                                print(f"   ✅ 자동 대화 시작됨 (세션: {session_id[:8]}...)")

                                # 자동 대화 중지
                                stop_message = {"type": "auto_chat_stop"}
                                await ws.send_str(json.dumps(stop_message))
                                print(f"   📤 자동 대화 중지 요청")

                            elif msg_type == 'auto_chat_stopped':
                                print(f"   ✅ 자동 대화 중지됨")
                                break
                            elif msg_type == 'error':
                                print(f"   ❌ 오류: {response.get('message', '알 수 없는 오류')}")
                                break

            except asyncio.TimeoutError:
                print(f"   ⏰ 응답 타임아웃")

        await session.close()

    except Exception as e:
        print(f"   ❌ 오류: {e}")

def main():
    """메인 함수"""
    print("🔍 WebSocket 종합 테스트 시작")

    # Python 3.7+ asyncio 실행
    try:
        asyncio.run(run_all_tests())
    except AttributeError:
        # Python 3.6 호환성
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_all_tests())

async def run_all_tests():
    """모든 테스트 실행"""
    await test_websocket_connection()
    await test_chat_websocket_features()

    print("\n" + "=" * 40)
    print("🎯 WebSocket 테스트 완료!")
    print("\n💡 테스트 결과:")
    print("   - WebSocket 연결이 정상적으로 작동하면 핑/퐁 응답을 받을 수 있습니다")
    print("   - 자동 대화 기능이 작동하면 세션 ID를 받을 수 있습니다")
    print("   - 실제 음성 테스트는 브라우저 데모 페이지에서 확인하세요")

if __name__ == "__main__":
    main()