#!/usr/bin/env python3
"""
데모 페이지 기능 테스트
"""

import requests
import json
import time

def test_demo_functionality():
    """데모 페이지 기능 테스트"""
    print("🎮 데모 페이지 기능 테스트")
    print("=" * 40)

    # 1. 데모 페이지 접근 테스트
    print("\n1️⃣  데모 페이지 접근...")
    try:
        response = requests.get("http://localhost:6001/static/demo.html", timeout=10)
        if response.status_code == 200:
            print("✅ 데모 페이지 접근 성공")
            content = response.text

            # 핵심 요소 확인
            checks = {
                "WebSocket 스크립트": "WebSocket" in content,
                "오디오 녹음": "mediaRecorder" in content or "MediaRecorder" in content,
                "TTS API 호출": "/api/tts" in content,
                "마이크 권한": "getUserMedia" in content,
                "오디오 시각화": "visualizer" in content.lower()
            }

            for feature, exists in checks.items():
                print(f"   - {feature}: {'✅' if exists else '❌'}")

        else:
            print(f"❌ 데모 페이지 접근 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 데모 페이지 테스트 실패: {e}")
        return False

    # 2. TTS API 기능 테스트
    print("\n2️⃣  TTS API 기능...")
    try:
        test_texts = [
            ("한국어", "KR", "안녕하세요! 데모 테스트입니다."),
            ("영어", "EN", "Hello! This is a demo test."),
            ("일본어", "JP", "こんにちは！デモテストです。")
        ]

        for lang_name, lang_code, text in test_texts:
            tts_data = {
                "text": text,
                "language": lang_code,
                "speed": 1.0
            }

            response = requests.post(
                "http://localhost:6001/api/tts",
                json=tts_data,
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print(f"   - {lang_name} TTS: ✅ ({data.get('audio_url', '').split('/')[-1]})")
                else:
                    print(f"   - {lang_name} TTS: ❌ {data.get('error')}")
            else:
                print(f"   - {lang_name} TTS: ❌ HTTP {response.status_code}")

    except Exception as e:
        print(f"❌ TTS API 테스트 실패: {e}")

    # 3. 언어 선택 API 테스트
    print("\n3️⃣  언어 선택 기능...")
    try:
        response = requests.get("http://localhost:6001/api/languages", timeout=10)
        if response.status_code == 200:
            data = response.json()
            languages = data.get('languages', [])
            print(f"✅ 지원 언어 {len(languages)}개 확인")

            # 주요 언어 확인
            lang_codes = [lang.get('code') for lang in languages]
            required_langs = ['KR', 'EN', 'JP', 'ZH']

            for req_lang in required_langs:
                if req_lang in lang_codes:
                    print(f"   - {req_lang}: ✅")
                else:
                    print(f"   - {req_lang}: ❌")
        else:
            print(f"❌ 언어 API 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ 언어 API 테스트 실패: {e}")

    # 4. WebSocket 정보 확인
    print("\n4️⃣  WebSocket 엔드포인트...")
    try:
        response = requests.get("http://localhost:6001/api/websocket/info", timeout=10)
        if response.status_code == 200:
            data = response.json()
            endpoints = data.get('endpoints', [])

            for endpoint in endpoints:
                path = endpoint.get('path')
                name = endpoint.get('name')
                print(f"✅ {path} - {name}")
        else:
            print(f"❌ WebSocket 정보 실패: {response.status_code}")
    except Exception as e:
        print(f"❌ WebSocket 정보 테스트 실패: {e}")

    # 5. 정적 파일 확인
    print("\n5️⃣  데모 리소스 파일...")
    static_files = [
        "/static/demo.html",
        "/static/css/style.css",
        "/static/js/voice-chat.js"
    ]

    for file_path in static_files:
        try:
            response = requests.get(f"http://localhost:6001{file_path}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {file_path}")
            else:
                print(f"❌ {file_path}: {response.status_code}")
        except Exception as e:
            print(f"❌ {file_path}: {e}")

    print("\n" + "=" * 40)
    print("🎯 데모 테스트 완료!")
    print("")
    print("🌐 데모 페이지 URL:")
    print("   http://localhost:6001/static/demo.html")
    print("")
    print("✨ 주요 기능:")
    print("   🎤 마이크 클릭 또는 스페이스바로 음성 입력")
    print("   💬 텍스트 입력 및 전송")
    print("   🔊 실시간 TTS 음성 출력")
    print("   🌍 다국어 지원 (한/영/일/중)")
    print("   📊 실시간 오디오 시각화")
    print("   🎛️ 속도/볼륨 조절")
    print("   🧪 개별 기능 테스트 버튼")

if __name__ == "__main__":
    test_demo_functionality()