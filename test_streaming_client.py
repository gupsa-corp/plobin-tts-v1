#!/usr/bin/env python3
"""
WebSocket TTS 스트리밍 테스트 클라이언트
"""

import asyncio
import websockets
import json
import wave
import io

async def test_streaming_tts():
    """
    WebSocket TTS 스트리밍 테스트
    """
    uri = "ws://localhost:6001/ws/tts"

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to TTS streaming service")

            # 연결 확인 메시지 받기
            response = await websocket.recv()
            print(f"Server: {response}")

            # 테스트 텍스트
            test_text = "안녕하세요! 실시간 음성 변환 테스트입니다."

            print(f"Sending text: {test_text}")
            await websocket.send(test_text)

            # 오디오 데이터 수집
            audio_chunks = []
            audio_started = False

            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)

                    if isinstance(response, str):
                        print(f"Server message: {response}")

                        if response == "|AUDIO_START|":
                            audio_started = True
                            print("Audio streaming started")
                        elif response == "|AUDIO_END|":
                            print("Audio streaming ended")
                            break
                    elif isinstance(response, bytes) and audio_started:
                        # 오디오 청크 데이터
                        audio_chunks.append(response)
                        print(f"Received audio chunk: {len(response)} bytes")

                except asyncio.TimeoutError:
                    print("Timeout waiting for response")
                    break
                except Exception as e:
                    print(f"Error: {e}")
                    break

            # 오디오 데이터를 파일로 저장
            if audio_chunks:
                print(f"Total audio chunks received: {len(audio_chunks)}")
                save_audio_chunks(audio_chunks, "test_output.wav")
                print("Audio saved to test_output.wav")
            else:
                print("No audio data received")

    except Exception as e:
        print(f"Connection error: {e}")

def save_audio_chunks(audio_chunks, filename):
    """
    오디오 청크들을 WAV 파일로 저장

    Args:
        audio_chunks (list): 오디오 청크 리스트
        filename (str): 저장할 파일명
    """
    try:
        # 모든 청크를 연결
        audio_data = b''.join(audio_chunks)

        # WAV 파일로 저장 (16-bit, 24kHz, mono)
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(24000)  # 24kHz
            wav_file.writeframes(audio_data)

        print(f"Saved {len(audio_data)} bytes to {filename}")

    except Exception as e:
        print(f"Error saving audio: {e}")

async def test_language_change():
    """
    언어 변경 테스트
    """
    uri = "ws://localhost:6001/ws/tts"

    try:
        async with websockets.connect(uri) as websocket:
            print("Testing language change...")

            # 연결 확인
            response = await websocket.recv()
            print(f"Connected: {response}")

            # 언어를 영어로 변경
            await websocket.send("CHANGE_LANGUAGE:EN")
            response = await websocket.recv()
            print(f"Language change response: {response}")

            # 영어 텍스트 테스트
            await websocket.send("Hello, this is English text-to-speech test.")

            # 응답 처리
            audio_chunks = []
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)

                    if isinstance(response, str):
                        print(f"Message: {response}")
                        if response == "|AUDIO_END|":
                            break
                    elif isinstance(response, bytes):
                        audio_chunks.append(response)

                except asyncio.TimeoutError:
                    break

            if audio_chunks:
                save_audio_chunks(audio_chunks, "test_english.wav")
                print("English audio saved to test_english.wav")

    except Exception as e:
        print(f"Language test error: {e}")

if __name__ == "__main__":
    print("=== WebSocket TTS Streaming Test ===")

    # 기본 스트리밍 테스트
    print("\n1. Testing basic streaming...")
    asyncio.run(test_streaming_tts())

    # 언어 변경 테스트
    print("\n2. Testing language change...")
    asyncio.run(test_language_change())

    print("\nTest completed!")