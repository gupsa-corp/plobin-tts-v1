#!/usr/bin/env python3
"""
간단한 시스템 테스트 스크립트
"""

import requests
import json
import sys
import os
import tempfile
import time

def test_server_health():
    """서버 헬스 체크"""
    print("🔍 서버 상태 확인 중...")
    try:
        response = requests.get("http://localhost:6001/api/models/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 서버 정상 작동")
            print(f"   - TTS 사용 가능: {data.get('tts_available')}")
            print(f"   - STT 사용 가능: {data.get('stt_available')}")
            print(f"   - 디바이스: {data.get('tts_device')}")
            return True
        else:
            print(f"❌ 서버 오류: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 서버 연결 실패: {e}")
        return False

def test_languages_api():
    """언어 목록 API 테스트"""
    print("\n🌍 언어 목록 API 테스트...")
    try:
        response = requests.get("http://localhost:6001/api/languages", timeout=10)
        if response.status_code == 200:
            data = response.json()
            languages = data.get('languages', [])
            print(f"✅ 지원 언어 {len(languages)}개:")
            for lang in languages[:5]:  # 처음 5개만 표시
                print(f"   - {lang.get('code')}: {lang.get('name')}")
            return True
        else:
            print(f"❌ 언어 API 오류: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 언어 API 실패: {e}")
        return False

def test_tts_api():
    """TTS API 테스트"""
    print("\n🔊 TTS API 테스트...")
    try:
        tts_data = {
            "text": "안녕하세요 테스트입니다",
            "language": "KR",
            "speed": 1.0
        }

        response = requests.post(
            "http://localhost:6001/api/tts",
            json=tts_data,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ TTS 성공: {data.get('filename')}")
                return True
            else:
                print(f"❌ TTS 실패: {data.get('error')}")
                return False
        else:
            print(f"❌ TTS API 오류: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   오류 상세: {error_data}")
            except:
                print(f"   응답: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ TTS API 실패: {e}")
        return False

def test_static_files():
    """정적 파일 서빙 테스트"""
    print("\n📁 정적 파일 테스트...")
    test_files = [
        "/static/css/style.css",
        "/static/js/voice-chat.js",
        "/static/quick_test.html"
    ]

    success_count = 0
    for file_path in test_files:
        try:
            response = requests.get(f"http://localhost:6001{file_path}", timeout=10)
            if response.status_code == 200:
                print(f"✅ {file_path}")
                success_count += 1
            else:
                print(f"❌ {file_path}: {response.status_code}")
        except Exception as e:
            print(f"❌ {file_path}: {e}")

    return success_count == len(test_files)

def test_websocket_connection():
    """WebSocket 연결 테스트 (라우트 등록 확인)"""
    print("\n🔌 WebSocket 엔드포인트 확인...")
    try:
        # WebSocket 정보 API로 등록 상태 확인
        response = requests.get("http://localhost:6001/api/websocket/info", timeout=10)
        if response.status_code == 200:
            data = response.json()
            endpoints = data.get('endpoints', [])

            # /ws/chat 엔드포인트 찾기
            chat_endpoint = None
            for endpoint in endpoints:
                if endpoint.get('path') == '/ws/chat':
                    chat_endpoint = endpoint
                    break

            if chat_endpoint:
                print("✅ WebSocket 엔드포인트 등록됨:")
                print(f"   - 경로: {chat_endpoint.get('path')}")
                print(f"   - 이름: {chat_endpoint.get('name')}")
                print(f"   - 설명: {chat_endpoint.get('description')}")
                return True
            else:
                print("❌ /ws/chat 엔드포인트 없음")
                return False
        else:
            print(f"❌ WebSocket 정보 API 오류: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ WebSocket 엔드포인트 확인 실패: {e}")
        return False

def test_main_page():
    """메인 페이지 로딩 테스트"""
    print("\n🏠 메인 페이지 테스트...")
    try:
        response = requests.get("http://localhost:6001/", timeout=10)
        if response.status_code == 200:
            content = response.text
            # 기본적인 HTML 요소 확인
            if "<html" in content and "<body" in content:
                print("✅ 메인 페이지 정상 로딩")

                # 주요 요소 확인
                checks = {
                    "음성": "음성" in content or "voice" in content.lower(),
                    "WebSocket": "websocket" in content.lower() or "ws:" in content,
                    "JavaScript": "<script" in content,
                    "CSS": "stylesheet" in content or "<style" in content
                }

                for check_name, result in checks.items():
                    print(f"   - {check_name}: {'✅' if result else '❌'}")

                return all(checks.values())
            else:
                print("❌ 잘못된 HTML 응답")
                return False
        else:
            print(f"❌ 메인 페이지 오류: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 메인 페이지 실패: {e}")
        return False

def test_api_docs():
    """API 문서 테스트"""
    print("\n📚 API 문서 테스트...")
    try:
        response = requests.get("http://localhost:6001/docs", timeout=10)
        if response.status_code == 200:
            print("✅ Swagger UI 접근 가능")
            return True
        else:
            print(f"❌ API 문서 오류: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API 문서 실패: {e}")
        return False

def main():
    """메인 테스트 실행"""
    print("🧪 음성 대화 시스템 간단 테스트")
    print("=" * 40)

    tests = [
        ("서버 헬스 체크", test_server_health),
        ("언어 목록 API", test_languages_api),
        ("메인 페이지", test_main_page),
        ("정적 파일", test_static_files),
        ("WebSocket 엔드포인트", test_websocket_connection),
        ("API 문서", test_api_docs),
        ("TTS API", test_tts_api),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except KeyboardInterrupt:
            print("\n\n⚠️  테스트 중단됨")
            break
        except Exception as e:
            print(f"\n❌ {test_name} 테스트 중 예외 발생: {e}")
            results.append((test_name, False))

    # 결과 요약
    print("\n" + "=" * 40)
    print("📊 테스트 결과 요약")
    print("=" * 40)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1

    print("-" * 40)
    print(f"총 {total}개 테스트 중 {passed}개 통과 ({passed/total*100:.1f}%)")

    if passed == total:
        print("\n🎉 모든 테스트 통과! 시스템이 정상 작동합니다.")
        return 0
    else:
        print(f"\n⚠️  {total-passed}개 테스트 실패. 시스템 점검이 필요합니다.")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  테스트 중단됨")
        sys.exit(1)