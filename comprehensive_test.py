#!/usr/bin/env python3
"""
종합 API 테스트 - 모든 엔드포인트와 기능 검증
"""

import requests
import json
import time
import tempfile
import os
from pathlib import Path

class APITester:
    def __init__(self, base_url="http://localhost:40003"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = {}

    def test_endpoint(self, method, endpoint, data=None, files=None, description=""):
        """개별 엔드포인트 테스트"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == "GET":
                response = self.session.get(url, timeout=10)
            elif method.upper() == "POST":
                if files:
                    response = self.session.post(url, files=files, timeout=30)
                else:
                    headers = {"Content-Type": "application/json"}
                    response = self.session.post(url, data=json.dumps(data), headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            return {
                "status_code": response.status_code,
                "success": 200 <= response.status_code < 300,
                "response_time": response.elapsed.total_seconds(),
                "content_type": response.headers.get("content-type", ""),
                "content_length": len(response.content),
                "data": response.json() if "application/json" in response.headers.get("content-type", "") else None
            }
        except Exception as e:
            return {
                "status_code": 0,
                "success": False,
                "error": str(e),
                "response_time": 0
            }

    def run_comprehensive_test(self):
        """종합 테스트 실행"""
        print("🔍 종합 API 테스트 시작")
        print("=" * 60)

        # 1. 기본 시스템 API 테스트
        self.test_system_apis()

        # 2. TTS API 테스트 (모든 언어)
        self.test_tts_apis()

        # 3. STT API 테스트
        self.test_stt_apis()

        # 4. WebSocket 문서 API 테스트
        self.test_websocket_docs()

        # 5. 자동 대화 API 테스트
        self.test_auto_chat_apis()

        # 6. 페이지 API 테스트
        self.test_page_apis()

        # 7. 정적 파일 테스트
        self.test_static_files()

        # 8. 숨겨진 엔드포인트 검색
        self.discover_hidden_endpoints()

        # 결과 요약
        self.print_summary()

    def test_system_apis(self):
        """시스템 정보 API 테스트"""
        print("\n1️⃣  시스템 정보 API")
        print("-" * 30)

        tests = [
            ("GET", "/api/models/status", None, "모델 상태 확인"),
            ("GET", "/api/languages", None, "지원 언어 목록"),
            ("GET", "/api/health", None, "헬스 체크"),
            ("GET", "/openapi.json", None, "OpenAPI 스펙"),
            ("GET", "/docs", None, "Swagger UI"),
            ("GET", "/redoc", None, "ReDoc")
        ]

        for method, endpoint, data, desc in tests:
            result = self.test_endpoint(method, endpoint, data, description=desc)
            self.results[endpoint] = result

            status = "✅" if result["success"] else "❌"
            time_str = f"{result['response_time']:.3f}s"
            print(f"{status} {endpoint:25} {desc:20} ({time_str})")

            if not result["success"] and "error" in result:
                print(f"     오류: {result['error']}")

    def test_tts_apis(self):
        """TTS API 테스트 (모든 언어)"""
        print("\n2️⃣  TTS API (다국어)")
        print("-" * 30)

        languages = [
            ("KR", "안녕하세요! TTS 테스트입니다."),
            ("EN", "Hello! This is a TTS test."),
            ("EN_V2", "Hello! This is version 2."),
            ("EN_NEWEST", "Hello! This is the newest version."),
            ("JP", "こんにちは！TTSテストです。"),
            ("ZH", "你好！这是TTS测试。"),
            ("FR", "Bonjour! Ceci est un test TTS."),
            ("ES", "¡Hola! Esta es una prueba de TTS.")
        ]

        for lang_code, text in languages:
            data = {
                "text": text,
                "language": lang_code,
                "speed": 1.0
            }

            result = self.test_endpoint("POST", "/api/tts", data, f"TTS {lang_code}")
            endpoint_key = f"/api/tts_{lang_code}"
            self.results[endpoint_key] = result

            status = "✅" if result["success"] else "❌"
            time_str = f"{result['response_time']:.3f}s"

            if result["success"] and result["data"]:
                audio_url = result["data"].get("audio_url", "")
                filename = audio_url.split("/")[-1] if audio_url else "None"
                print(f"{status} TTS {lang_code:10} {filename:35} ({time_str})")
            else:
                error_msg = result.get("error", "Unknown error")
                print(f"{status} TTS {lang_code:10} Failed: {error_msg:35} ({time_str})")

        # 배치 TTS 테스트
        batch_data = {
            "requests": [
                {"text": "첫 번째 문장", "language": "KR", "speed": 1.0},
                {"text": "두 번째 문장", "language": "KR", "speed": 1.2}
            ]
        }

        result = self.test_endpoint("POST", "/api/batch-tts", batch_data, "배치 TTS")
        self.results["/api/batch-tts"] = result

        status = "✅" if result["success"] else "❌"
        time_str = f"{result['response_time']:.3f}s"
        print(f"{status} 배치 TTS                                        ({time_str})")

    def test_stt_apis(self):
        """STT API 테스트"""
        print("\n3️⃣  STT API")
        print("-" * 30)

        # 임시 오디오 파일 생성 (WAV 헤더)
        temp_audio = self.create_test_audio_file()

        try:
            with open(temp_audio, "rb") as f:
                files = {"audio": ("test.webm", f, "audio/webm")}
                result = self.test_endpoint("POST", "/api/stt", files=files, description="STT 테스트")
                self.results["/api/stt"] = result

                status = "✅" if result["success"] else "❌"
                time_str = f"{result['response_time']:.3f}s"

                if result["success"] and result["data"]:
                    text = result["data"].get("text", "")
                    confidence = result["data"].get("confidence", 0)
                    print(f"{status} STT API         텍스트: '{text[:30]}...' 신뢰도: {confidence:.2f} ({time_str})")
                else:
                    error_msg = result.get("error", "Unknown error")
                    print(f"{status} STT API         Failed: {error_msg} ({time_str})")
        finally:
            if os.path.exists(temp_audio):
                os.unlink(temp_audio)

    def test_websocket_docs(self):
        """WebSocket 문서 API 테스트"""
        print("\n4️⃣  WebSocket 문서 API")
        print("-" * 30)

        tests = [
            ("GET", "/api/websocket/docs", None, "WebSocket 완전 문서"),
            ("GET", "/api/websocket/endpoints", None, "WebSocket 엔드포인트 목록"),
            ("GET", "/api/websocket/info", None, "WebSocket 정보"),
            ("GET", "/api/websocket/examples/chat", None, "채팅 예제"),
            ("GET", "/api/websocket/examples/stt", None, "STT 예제")
        ]

        for method, endpoint, data, desc in tests:
            result = self.test_endpoint(method, endpoint, data, description=desc)
            self.results[endpoint] = result

            status = "✅" if result["success"] else "❌"
            time_str = f"{result['response_time']:.3f}s"

            if result["success"] and result["data"]:
                if "endpoints" in result["data"]:
                    count = len(result["data"]["endpoints"])
                    print(f"{status} {endpoint:30} {count}개 엔드포인트 ({time_str})")
                elif "examples" in result["data"]:
                    print(f"{status} {endpoint:30} 예제 코드 포함 ({time_str})")
                else:
                    print(f"{status} {endpoint:30} {desc} ({time_str})")
            else:
                print(f"{status} {endpoint:30} Failed ({time_str})")

    def test_auto_chat_apis(self):
        """자동 대화 API 테스트"""
        print("\n5️⃣  자동 대화 API")
        print("-" * 30)

        tests = [
            ("GET", "/api/auto-chat/themes", None, "대화 테마 목록"),
            ("GET", "/api/auto-chat/sessions", None, "활성 세션 목록"),
        ]

        for method, endpoint, data, desc in tests:
            result = self.test_endpoint(method, endpoint, data, description=desc)
            self.results[endpoint] = result

            status = "✅" if result["success"] else "❌"
            time_str = f"{result['response_time']:.3f}s"

            if result["success"] and result["data"]:
                if isinstance(result["data"], list):
                    count = len(result["data"])
                    print(f"{status} {endpoint:30} {count}개 항목 ({time_str})")
                else:
                    print(f"{status} {endpoint:30} {desc} ({time_str})")
            else:
                print(f"{status} {endpoint:30} Failed ({time_str})")

    def test_page_apis(self):
        """페이지 API 테스트"""
        print("\n6️⃣  페이지 API")
        print("-" * 30)

        tests = [
            ("GET", "/", None, "메인 페이지"),
            ("GET", "/test", None, "테스트 페이지"),
        ]

        for method, endpoint, data, desc in tests:
            result = self.test_endpoint(method, endpoint, data, description=desc)
            self.results[endpoint] = result

            status = "✅" if result["success"] else "❌"
            time_str = f"{result['response_time']:.3f}s"
            content_size = result.get("content_length", 0)
            print(f"{status} {endpoint:15} {desc:15} {content_size:>8} bytes ({time_str})")

    def test_static_files(self):
        """정적 파일 테스트"""
        print("\n7️⃣  정적 파일")
        print("-" * 30)

        static_files = [
            "/static/demo.html",
            "/static/quick_test.html",
            "/static/css/style.css",
            "/static/js/voice-chat.js",
        ]

        for file_path in static_files:
            result = self.test_endpoint("GET", file_path, description="정적 파일")
            self.results[file_path] = result

            status = "✅" if result["success"] else "❌"
            time_str = f"{result['response_time']:.3f}s"
            content_size = result.get("content_length", 0)
            print(f"{status} {file_path:25} {content_size:>8} bytes ({time_str})")

    def discover_hidden_endpoints(self):
        """숨겨진 엔드포인트 발견"""
        print("\n8️⃣  숨겨진 엔드포인트 검색")
        print("-" * 30)

        # 일반적인 엔드포인트 패턴 시도
        potential_endpoints = [
            "/robots.txt",
            "/favicon.ico",
            "/api",
            "/api/v1",
            "/admin",
            "/debug",
            "/metrics",
            "/status",
            "/ping",
            "/version",
            "/api/user",
            "/api/auth",
            "/api/config",
        ]

        found_endpoints = []

        for endpoint in potential_endpoints:
            result = self.test_endpoint("GET", endpoint, description="탐색")

            if result["success"]:
                found_endpoints.append(endpoint)
                time_str = f"{result['response_time']:.3f}s"
                print(f"🔍 {endpoint:20} 발견! ({time_str})")

        if not found_endpoints:
            print("   추가 엔드포인트를 찾을 수 없습니다.")

    def create_test_audio_file(self):
        """테스트용 WAV 파일 생성"""
        # 간단한 WAV 헤더 + 1초 무음 데이터
        wav_header = (
            b'RIFF' + (44 + 16000).to_bytes(4, 'little') +
            b'WAVE' + b'fmt ' + (16).to_bytes(4, 'little') +
            (1).to_bytes(2, 'little') + (1).to_bytes(2, 'little') +
            (16000).to_bytes(4, 'little') + (32000).to_bytes(4, 'little') +
            (2).to_bytes(2, 'little') + (16).to_bytes(2, 'little') +
            b'data' + (16000).to_bytes(4, 'little')
        )

        silence_data = b'\x00\x00' * 8000  # 1초 무음

        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_file.write(wav_header + silence_data)
        temp_file.close()

        return temp_file.name

    def print_summary(self):
        """결과 요약 출력"""
        print("\n" + "=" * 60)
        print("📊 테스트 결과 요약")
        print("=" * 60)

        total_tests = len(self.results)
        successful_tests = sum(1 for result in self.results.values() if result["success"])
        failed_tests = total_tests - successful_tests

        print(f"전체 테스트: {total_tests}개")
        print(f"성공: {successful_tests}개 (✅)")
        print(f"실패: {failed_tests}개 (❌)")
        print(f"성공률: {successful_tests/total_tests*100:.1f}%")

        # 응답 시간 통계
        response_times = [r["response_time"] for r in self.results.values() if r["response_time"] > 0]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            print(f"평균 응답시간: {avg_time:.3f}s")
            print(f"최대 응답시간: {max_time:.3f}s")

        # 실패한 테스트 상세
        if failed_tests > 0:
            print("\n❌ 실패한 테스트:")
            for endpoint, result in self.results.items():
                if not result["success"]:
                    error = result.get("error", f"HTTP {result['status_code']}")
                    print(f"   - {endpoint}: {error}")

        print("\n🎯 테스트 완료!")
        print(f"접속 URL: {self.base_url}")

def main():
    tester = APITester()
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main()