#!/usr/bin/env python3
"""
최종 API 테스트 - 올바른 스키마 사용
"""

import requests
import json
import tempfile
import os

def test_all_apis():
    """모든 API 올바른 스키마로 테스트"""
    base_url = "http://localhost:6001"

    print("🎯 최종 API 테스트 (올바른 스키마)")
    print("=" * 50)

    results = {"success": 0, "total": 0}

    # 1. 기본 시스템 API 테스트
    system_apis = [
        ("GET", "/api/models/status", None, "모델 상태"),
        ("GET", "/api/languages", None, "언어 목록"),
        ("GET", "/api/health", None, "헬스 체크"),
        ("GET", "/docs", None, "Swagger UI"),
        ("GET", "/redoc", None, "ReDoc")
    ]

    print("\n📊 시스템 API")
    for method, endpoint, data, desc in system_apis:
        success = test_api(base_url, method, endpoint, data, desc)
        update_results(results, success)

    # 2. TTS API 테스트 (다국어)
    print("\n🔊 TTS API (다국어)")

    languages = [
        ("KR", "안녕하세요! 한국어 TTS 테스트입니다."),
        ("EN", "Hello! English TTS test."),
        ("JP", "こんにちは！日本語TTSテストです。"),
        ("ZH", "你好！中文TTS测试。")
    ]

    for lang_code, text in languages:
        tts_data = {
            "text": text,
            "language": lang_code,
            "speed": 1.0
        }
        success = test_api(base_url, "POST", "/api/tts", tts_data, f"TTS {lang_code}")
        update_results(results, success)

    # 3. 배치 TTS API (올바른 스키마)
    print("\n📦 배치 TTS API")
    batch_data = {
        "texts": [
            "첫 번째 배치 문장입니다.",
            "두 번째 배치 문장입니다.",
            "세 번째 배치 문장입니다."
        ],
        "language": "KR",
        "speed": 1.0,
        "format": "zip"
    }
    success = test_api(base_url, "POST", "/api/batch-tts", batch_data, "배치 TTS")
    update_results(results, success)

    # 4. STT API (올바른 파라미터명)
    print("\n🎤 STT API")
    try:
        # WAV 파일 생성
        wav_header = (
            b'RIFF' + (44 + 16000).to_bytes(4, 'little') +
            b'WAVE' + b'fmt ' + (16).to_bytes(4, 'little') +
            (1).to_bytes(2, 'little') + (1).to_bytes(2, 'little') +
            (16000).to_bytes(4, 'little') + (32000).to_bytes(4, 'little') +
            (2).to_bytes(2, 'little') + (16).to_bytes(2, 'little') +
            b'data' + (16000).to_bytes(4, 'little')
        )
        silence_data = b'\x00\x00' * 8000

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(wav_header + silence_data)
            temp_path = temp_file.name

        try:
            with open(temp_path, "rb") as f:
                # 올바른 파라미터명: audio_file
                files = {"audio_file": ("test.wav", f, "audio/wav")}
                response = requests.post(f"{base_url}/api/stt", files=files, timeout=30)

            success = response.status_code == 200
            status = "✅" if success else "❌"

            if success:
                data = response.json()
                text = data.get("text", "")
                confidence = data.get("confidence", 0)
                print(f"{status} STT API: '{text[:30]}...' (신뢰도: {confidence:.2f})")
            else:
                print(f"{status} STT API: HTTP {response.status_code} - {response.text[:100]}")

            update_results(results, success)

        finally:
            os.unlink(temp_path)

    except Exception as e:
        print(f"❌ STT API: 오류 - {e}")
        update_results(results, False)

    # 5. WebSocket 문서 API
    print("\n🔌 WebSocket 문서")
    websocket_apis = [
        ("GET", "/api/websocket/docs", None, "완전 문서"),
        ("GET", "/api/websocket/endpoints", None, "엔드포인트 목록"),
        ("GET", "/api/websocket/info", None, "WebSocket 정보"),
        ("GET", "/api/websocket/examples/chat", None, "채팅 예제"),
        ("GET", "/api/websocket/examples/stt", None, "STT 예제")
    ]

    for method, endpoint, data, desc in websocket_apis:
        success = test_api(base_url, method, endpoint, data, desc)
        update_results(results, success)

    # 6. 자동 대화 API
    print("\n🤖 자동 대화")
    auto_chat_apis = [
        ("GET", "/api/auto-chat/themes", None, "대화 테마"),
        ("GET", "/api/auto-chat/sessions", None, "활성 세션")
    ]

    for method, endpoint, data, desc in auto_chat_apis:
        success = test_api(base_url, method, endpoint, data, desc)
        update_results(results, success)

    # 7. 페이지 API
    print("\n🌐 페이지")
    page_apis = [
        ("GET", "/", None, "메인 페이지"),
        ("GET", "/test", None, "테스트 페이지")
    ]

    for method, endpoint, data, desc in page_apis:
        success = test_api(base_url, method, endpoint, data, desc)
        update_results(results, success)

    # 8. 중요 정적 파일
    print("\n📁 정적 파일")
    static_files = [
        ("GET", "/static/demo.html", None, "데모 페이지"),
        ("GET", "/static/quick_test.html", None, "빠른 테스트"),
        ("GET", "/static/css/style.css", None, "스타일시트"),
        ("GET", "/static/js/voice-chat.js", None, "JavaScript")
    ]

    for method, endpoint, data, desc in static_files:
        success = test_api(base_url, method, endpoint, data, desc)
        update_results(results, success)

    # 결과 요약
    print("\n" + "=" * 50)
    print("📊 최종 테스트 결과")
    print("=" * 50)

    success_rate = (results["success"] / results["total"]) * 100
    print(f"총 테스트: {results['total']}개")
    print(f"성공: {results['success']}개")
    print(f"실패: {results['total'] - results['success']}개")
    print(f"성공률: {success_rate:.1f}%")

    if success_rate >= 90:
        print("\n🎉 거의 모든 API가 정상 작동합니다!")
    elif success_rate >= 80:
        print("\n✅ 대부분의 API가 정상 작동합니다!")
    elif success_rate >= 70:
        print("\n⚠️  일부 API에 문제가 있을 수 있습니다.")
    else:
        print("\n❌ API에 심각한 문제가 있습니다.")

    print(f"\n🌐 접속 URL: {base_url}")
    print(f"📚 API 문서: {base_url}/docs")
    print(f"🎮 데모 페이지: {base_url}/static/demo.html")

def test_api(base_url, method, endpoint, data, description):
    """개별 API 테스트"""
    try:
        url = f"{base_url}{endpoint}"

        if method.upper() == "GET":
            response = requests.get(url, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, timeout=30)
        else:
            print(f"❌ {description}: 지원하지 않는 메서드 {method}")
            return False

        success = 200 <= response.status_code < 300
        status = "✅" if success else "❌"

        # 응답 데이터 요약
        if success:
            try:
                response_data = response.json()
                if "audio_url" in response_data:
                    filename = response_data["audio_url"].split("/")[-1]
                    print(f"{status} {description}: {filename}")
                elif "endpoints" in response_data:
                    count = len(response_data["endpoints"])
                    print(f"{status} {description}: {count}개 항목")
                elif "languages" in response_data:
                    count = len(response_data["languages"])
                    print(f"{status} {description}: {count}개 언어")
                elif "texts" in str(response_data):
                    print(f"{status} {description}: 배치 처리 완료")
                else:
                    content_size = len(response.content)
                    print(f"{status} {description}: {content_size} bytes")
            except:
                content_size = len(response.content)
                print(f"{status} {description}: {content_size} bytes")
        else:
            print(f"{status} {description}: HTTP {response.status_code}")

        return success

    except Exception as e:
        print(f"❌ {description}: 오류 - {str(e)[:50]}")
        return False

def update_results(results, success):
    """결과 업데이트"""
    results["total"] += 1
    if success:
        results["success"] += 1

if __name__ == "__main__":
    test_all_apis()