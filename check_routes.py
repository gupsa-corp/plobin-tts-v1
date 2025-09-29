#!/usr/bin/env python3
"""
FastAPI 앱의 등록된 라우트 확인
"""

import sys
import os
sys.path.append('.')

from web_voice_chat_new import app

def check_routes():
    print("📋 등록된 라우트 목록:")
    print("=" * 50)

    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = getattr(route, 'methods', ['UNKNOWN'])
            path = route.path
            name = getattr(route, 'name', 'unnamed')

            if 'WebSocket' in str(type(route)):
                print(f"🔌 WebSocket: {path} ({name})")
            elif 'HTTP' in str(type(route)) or hasattr(route, 'methods'):
                methods_str = ', '.join(methods) if methods else 'UNKNOWN'
                print(f"🌐 HTTP: {methods_str} {path} ({name})")
            else:
                print(f"❓ Other: {path} ({name}) - {type(route)}")

    print("\n" + "=" * 50)

    # WebSocket 라우트만 별도 확인
    websocket_routes = [r for r in app.routes if 'WebSocket' in str(type(r))]
    print(f"🔌 WebSocket 라우트 총 {len(websocket_routes)}개:")

    for route in websocket_routes:
        print(f"   - {route.path}")

if __name__ == "__main__":
    check_routes()