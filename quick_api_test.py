#!/usr/bin/env python3
"""
빠른 API 테스트 - 개별 확인
"""

import requests
import json
import tempfile
import os

def test_individual_apis():
    """개별 API 테스트"""
    base_url = "http://localhost:40003"

    print("🧪 개별 API 테스트")
    print("=" * 40)

    # 1. TTS API 테스트 (한국어)
    print("\n1️⃣  TTS API (한국어)")
    try:
        tts_data = {
            "text": "안녕하세요! 개별 테스트입니다.",
            "language": "KR",
            "speed": 1.0
        }

        response = requests.post(
            f"{base_url}/api/tts",
            json=tts_data,
            headers={"Content-Type": "application/json"},
            timeout=15
        )

        print(f"   상태 코드: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 성공: {data.get('audio_url', '')}")
        else:
            print(f"   ❌ 실패: {response.text}")

    except Exception as e:
        print(f"   ❌ 오류: {e}")

    # 2. 영어 TTS 테스트
    print("\n2️⃣  TTS API (영어)")
    try:
        tts_data = {
            "text": "Hello! This is an individual test.",
            "language": "EN",
            "speed": 1.0
        }

        response = requests.post(
            f"{base_url}/api/tts",
            json=tts_data,
            headers={"Content-Type": "application/json"},
            timeout=15
        )

        print(f"   상태 코드: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 성공: {data.get('audio_url', '')}")
        else:
            print(f"   ❌ 실패: {response.text}")

    except Exception as e:
        print(f"   ❌ 오류: {e}")

    # 3. STT API 테스트
    print("\n3️⃣  STT API")
    try:
        # 간단한 WAV 파일 생성
        wav_header = (
            b'RIFF' + (44 + 16000).to_bytes(4, 'little') +
            b'WAVE' + b'fmt ' + (16).to_bytes(4, 'little') +
            (1).to_bytes(2, 'little') + (1).to_bytes(2, 'little') +
            (16000).to_bytes(4, 'little') + (32000).to_bytes(4, 'little') +
            (2).to_bytes(2, 'little') + (16).to_bytes(2, 'little') +
            b'data' + (16000).to_bytes(4, 'little')
        )

        silence_data = b'\x00\x00' * 8000  # 1초 무음

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(wav_header + silence_data)
            temp_path = temp_file.name

        try:
            with open(temp_path, "rb") as f:
                files = {"audio": ("test.webm", f, "audio/webm")}
                response = requests.post(
                    f"{base_url}/api/stt",
                    files=files,
                    timeout=30
                )

            print(f"   상태 코드: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ 성공: '{data.get('text', '')}' (신뢰도: {data.get('confidence', 0):.2f})")
            else:
                print(f"   ❌ 실패: {response.text}")

        finally:
            os.unlink(temp_path)

    except Exception as e:
        print(f"   ❌ 오류: {e}")

    # 4. 배치 TTS 테스트
    print("\n4️⃣  배치 TTS API")
    try:
        batch_data = {
            "requests": [
                {"text": "첫 번째 문장", "language": "KR", "speed": 1.0},
                {"text": "두 번째 문장", "language": "KR", "speed": 1.2}
            ]
        }

        response = requests.post(
            f"{base_url}/api/batch-tts",
            json=batch_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        print(f"   상태 코드: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"   ✅ 성공: {len(results)}개 파일 생성")
            for i, result in enumerate(results):
                print(f"      {i+1}: {result.get('audio_url', '')}")
        else:
            print(f"   ❌ 실패: {response.text}")

    except Exception as e:
        print(f"   ❌ 오류: {e}")

    # 5. 언어 목록 API
    print("\n5️⃣  언어 목록 API")
    try:
        response = requests.get(f"{base_url}/api/languages", timeout=10)
        print(f"   상태 코드: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            languages = data.get('languages', [])
            print(f"   ✅ 성공: {len(languages)}개 언어 지원")
            for lang in languages[:3]:
                print(f"      - {lang.get('code')}: {lang.get('name')}")
        else:
            print(f"   ❌ 실패: {response.text}")
    except Exception as e:
        print(f"   ❌ 오류: {e}")

    # 6. 모델 상태 API
    print("\n6️⃣  모델 상태 API")
    try:
        response = requests.get(f"{base_url}/api/models/status", timeout=10)
        print(f"   상태 코드: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 성공:")
            print(f"      - TTS 사용 가능: {data.get('tts_available')}")
            print(f"      - STT 사용 가능: {data.get('stt_available')}")
            print(f"      - 디바이스: {data.get('tts_device')}")
        else:
            print(f"   ❌ 실패: {response.text}")
    except Exception as e:
        print(f"   ❌ 오류: {e}")

    print("\n" + "=" * 40)
    print("🎯 개별 API 테스트 완료!")

if __name__ == "__main__":
    test_individual_apis()