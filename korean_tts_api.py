#!/usr/bin/env python3
"""
Korean TTS API Server using FastAPI
간단한 웹 API 서버로 한국어 TTS 기능 제공
"""

import os
import sys
import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# Add MeloTTS to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'MeloTTS'))

try:
    from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
    from fastapi.responses import FileResponse
    from pydantic import BaseModel
    from melo.api import TTS
    from RealtimeTTS import TextToAudioStream
except ImportError as e:
    print(f"필요한 패키지가 설치되지 않았습니다: {e}")
    print("다음 명령어로 설치하세요:")
    print("pip install fastapi uvicorn realtimetts[minimal]")
    sys.exit(1)

# FastAPI 앱 생성 (Swagger 포함)
app = FastAPI(
    title="Korean TTS API with Streaming",
    version="2.0.0",
    description="""
    ## 한국어 TTS API with 실시간 스트리밍

    이 API는 다음 기능을 제공합니다:

    ### HTTP API
    - **POST /tts**: 텍스트를 음성 파일(WebM)로 변환
    - **GET /health**: 서버 상태 확인

    ### WebSocket API
    - **WebSocket /ws/tts**: 실시간 TTS 스트리밍
        - 실시간 텍스트 → 음성 변환
        - 언어 변경: `CHANGE_LANGUAGE:EN`
        - 스피커 변경: `CHANGE_SPEAKER:0`

    ### 지원 언어
    - **KR**: 한국어 (기본)
    - **EN**: 영어 (v1)
    - **EN_V2**: 영어 (v2)
    - **EN_NEWEST**: 영어 (v3, 최신)
    - **ZH**: 중국어
    - **JP**: 일본어
    - **FR**: 프랑스어
    - **ES**: 스페인어

    ### 기술 스택
    - **TTS Engine**: MeloTTS + RealtimeTTS
    - **Streaming**: WebSocket 기반 실시간 스트리밍
    - **GPU 지원**: CUDA 자동 감지 및 최적화
    """,
    contact={
        "name": "Gupsa Corp",
        "url": "https://github.com/gupsa-corp/plobin-tts-v1",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# 전역 모델들
tts_model = None
stt_model = None

# Import custom MeloTTS engine
try:
    from melo_realtime_engine import MeloEngine
except ImportError as e:
    print(f"Warning: MeloEngine not available: {e}")
    MeloEngine = None

# Import Whisper STT module
try:
    from whisper_stt_module import WhisperSTT, AudioProcessor
except ImportError as e:
    print(f"Warning: WhisperSTT not available: {e}")
    WhisperSTT = None
    AudioProcessor = None

class TTSRequest(BaseModel):
    text: str = "안녕하세요! TTS 테스트입니다."
    speaker_id: int = 0
    speed: float = 1.0

    class Config:
        schema_extra = {
            "example": {
                "text": "안녕하세요! 한국어 음성 변환 테스트입니다.",
                "speaker_id": 0,
                "speed": 1.0
            }
        }

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    server_info: dict

class RootResponse(BaseModel):
    message: str
    status: str
    version: str
    endpoints: dict

class STTRequest(BaseModel):
    language: str = "auto"

    class Config:
        schema_extra = {
            "example": {
                "language": "ko"
            }
        }

class STTResponse(BaseModel):
    text: str
    language: str
    confidence: float
    processing_time: float

class BatchTTSRequest(BaseModel):
    texts: list[str]
    speaker_id: int = 0
    speed: float = 1.0
    format: str = "zip"

    class Config:
        schema_extra = {
            "example": {
                "texts": [
                    "첫 번째 텍스트입니다.",
                    "두 번째 텍스트입니다.",
                    "세 번째 텍스트입니다."
                ],
                "speaker_id": 0,
                "speed": 1.0,
                "format": "zip"
            }
        }

@app.on_event("startup")
async def startup_event():
    """서버 시작시 TTS 및 STT 모델 로드"""
    global tts_model, stt_model

    # TTS 모델 로드
    try:
        print("한국어 TTS 모델 로딩 중...")
        tts_model = TTS(language='KR', device='cpu')
        print("✓ TTS 모델 로드 완료!")
    except Exception as e:
        print(f"✗ TTS 모델 로드 실패: {e}")
        # TTS 실패해도 서버는 계속 실행

    # STT 모델 로드
    try:
        if WhisperSTT:
            print("Whisper STT 모델 로딩 중...")
            stt_model = WhisperSTT(model_name="base", device="auto", language="auto")
            print("✓ STT 모델 로드 완료!")
        else:
            print("⚠ STT 모델을 사용할 수 없습니다")
    except Exception as e:
        print(f"⚠ STT 모델 로드 실패: {e}")
        # STT 실패해도 서버는 계속 실행

@app.get("/", response_model=RootResponse, tags=["Info"])
async def root():
    """
    ## 기본 정보 엔드포인트

    서버 상태와 사용 가능한 엔드포인트 정보를 반환합니다.
    """
    return {
        "message": "Korean TTS API Server with Streaming",
        "status": "running",
        "version": "2.0.0",
        "endpoints": {
            "tts": "POST /tts - 텍스트를 음성으로 변환",
            "stt": "POST /stt - 음성을 텍스트로 변환",
            "batch_tts": "POST /batch-tts - 여러 텍스트 일괄 변환",
            "streaming_tts": "WebSocket /ws/tts - 실시간 TTS 스트리밍",
            "streaming_stt": "WebSocket /ws/stt - 실시간 STT 스트리밍",
            "conversation": "WebSocket /ws/conversation - STT+TTS 통합 대화",
            "health": "GET /health - 서버 상태 확인",
            "docs": "GET /docs - Swagger 문서",
            "redoc": "GET /redoc - ReDoc 문서"
        }
    }

@app.post("/tts", tags=["TTS"],
          summary="텍스트를 음성으로 변환",
          description="""
## 텍스트를 음성(WebM 파일)으로 변환

### 매개변수:
- **text**: 변환할 텍스트 (한국어, 영어 등 지원)
- **speaker_id**: 스피커 ID (기본값: 0)
- **speed**: 음성 속도 (기본값: 1.0)

### 응답:
- WebM 형식의 오디오 파일 (Opus 코덱, 64kbps)

### 예시 요청:
```json
{
  "text": "안녕하세요! 한국어 음성 변환 테스트입니다.",
  "speaker_id": 0,
  "speed": 1.0
}
```
          """)
async def text_to_speech(request: TTSRequest):
    if not tts_model:
        raise HTTPException(status_code=500, detail="TTS 모델이 로드되지 않았습니다")

    try:
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name

        # TTS 수행
        tts_model.tts_to_file(
            text=request.text,
            speaker_id=request.speaker_id,
            output_path=temp_path,
            speed=request.speed,
            quiet=True
        )

        return FileResponse(
            path=temp_path,
            media_type="audio/wav",
            filename=f"tts_output.wav"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS 처리 실패: {str(e)}")

@app.post("/stt", response_model=STTResponse, tags=["STT"],
          summary="음성을 텍스트로 변환",
          description="""
## 음성 파일을 텍스트로 변환

### 매개변수:
- **audio_file**: 업로드할 음성 파일 (WAV, MP3, M4A 등)
- **language**: 음성 언어 (auto, ko, en, ja, zh 등)

### 응답:
- 변환된 텍스트와 신뢰도, 처리 시간

### 지원 형식:
- WAV, MP3, M4A, FLAC, OGG 등 대부분의 오디오 형식

### 지원 언어:
- ko (한국어), en (영어), ja (일본어), zh (중국어), auto (자동감지) 등
          """)
async def speech_to_text(audio_file: UploadFile = File(...), language: str = "auto"):
    """음성 파일을 텍스트로 변환"""
    if not stt_model:
        raise HTTPException(status_code=500, detail="STT 모델이 로드되지 않았습니다")

    if not audio_file:
        raise HTTPException(status_code=400, detail="음성 파일이 제공되지 않았습니다")

    try:
        import time
        start_time = time.time()

        # 파일 확장자 확인
        file_extension = audio_file.filename.lower().split('.')[-1] if audio_file.filename else ""
        if file_extension not in ["wav", "mp3", "m4a", "flac", "ogg", "aac", "wma"]:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식: {file_extension}")

        # 파일 데이터 읽기
        audio_data = await audio_file.read()

        # 임시 파일로 저장하여 처리
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=f".{file_extension}", delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name

        try:
            # STT 처리
            result = stt_model.transcribe_file(temp_path, language if language != "auto" else None)

            processing_time = time.time() - start_time

            # 임시 파일 삭제
            os.unlink(temp_path)

            if "error" in result:
                raise HTTPException(status_code=500, detail=f"STT 처리 실패: {result['error']}")

            return {
                "text": result.get("text", ""),
                "language": result.get("language", "unknown"),
                "confidence": result.get("confidence", 0.0),
                "processing_time": round(processing_time, 2)
            }

        except Exception as e:
            # 임시 파일 정리
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT 처리 실패: {str(e)}")

@app.post("/batch-tts", tags=["TTS"],
          summary="여러 텍스트 일괄 변환",
          description="""
## 여러 텍스트를 한 번에 음성으로 변환

### 매개변수:
- **texts**: 변환할 텍스트 목록
- **speaker_id**: 스피커 ID (기본값: 0)
- **speed**: 음성 속도 (기본값: 1.0)
- **format**: 출력 형식 ("zip" 또는 "individual")

### 응답:
- ZIP 파일 (format="zip") 또는 개별 파일들

### 예시:
```json
{
  "texts": ["첫 번째 문장", "두 번째 문장"],
  "speaker_id": 0,
  "speed": 1.0,
  "format": "zip"
}
```
          """)
async def batch_text_to_speech(request: BatchTTSRequest):
    """여러 텍스트를 일괄적으로 음성으로 변환"""
    if not tts_model:
        raise HTTPException(status_code=500, detail="TTS 모델이 로드되지 않았습니다")

    if not request.texts:
        raise HTTPException(status_code=400, detail="변환할 텍스트가 제공되지 않았습니다")

    if len(request.texts) > 50:
        raise HTTPException(status_code=400, detail="한 번에 최대 50개의 텍스트만 처리 가능합니다")

    try:
        import tempfile
        import zipfile
        import os
        from pathlib import Path

        audio_files = []
        temp_dir = tempfile.mkdtemp()

        try:
            # 각 텍스트를 TTS 처리
            for i, text in enumerate(request.texts):
                if not text.strip():
                    continue

                # 파일명 생성 (인덱스 기반)
                filename = f"tts_output_{i:03d}.wav"
                file_path = os.path.join(temp_dir, filename)

                # TTS 변환
                tts_model.tts_to_file(
                    text=text.strip(),
                    speaker_id=request.speaker_id,
                    output_path=file_path,
                    speed=request.speed,
                    quiet=True
                )

                audio_files.append((filename, file_path))

            if not audio_files:
                raise HTTPException(status_code=400, detail="변환 가능한 텍스트가 없습니다")

            # ZIP 파일로 압축
            if request.format == "zip":
                zip_path = os.path.join(temp_dir, "batch_tts_output.zip")
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for filename, file_path in audio_files:
                        zipf.write(file_path, filename)

                return FileResponse(
                    path=zip_path,
                    media_type="application/zip",
                    filename="batch_tts_output.zip"
                )
            else:
                # 개별 파일 처리 (첫 번째 파일만 반환)
                if audio_files:
                    filename, file_path = audio_files[0]
                    return FileResponse(
                        path=file_path,
                        media_type="audio/wav",
                        filename=filename
                    )

        finally:
            # 임시 파일들 정리 (나중에 정리되도록 백그라운드 작업으로)
            import threading
            def cleanup_temp_files():
                try:
                    import shutil
                    import time
                    time.sleep(60)  # 1분 후 정리
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                except:
                    pass

            cleanup_thread = threading.Thread(target=cleanup_temp_files)
            cleanup_thread.daemon = True
            cleanup_thread.start()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"배치 TTS 처리 실패: {str(e)}")

@app.get("/health", response_model=HealthResponse, tags=["Health"],
         summary="서버 상태 확인",
         description="""
## 서버 상태 및 모델 로딩 상태 확인

### 응답:
- **status**: 서버 상태 (healthy/unhealthy)
- **model_loaded**: TTS 모델 로딩 여부
- **server_info**: 서버 세부 정보

이 엔드포인트를 통해 서버가 정상 작동 중이며 TTS 모델이 로드되었는지 확인할 수 있습니다.
         """)
async def health_check():
    import psutil
    import os

    try:
        # 시스템 정보 수집
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_info = psutil.virtual_memory()

        server_info = {
            "cpu_usage": f"{cpu_percent}%",
            "memory_usage": f"{memory_info.percent}%",
            "memory_available": f"{memory_info.available // (1024**3)}GB",
            "process_id": os.getpid(),
            "tts_engine": "MeloTTS",
            "streaming_support": MeloEngine is not None,
            "supported_languages": ["KR", "EN", "EN_V2", "EN_NEWEST", "ZH", "JP", "FR", "ES"]
        }
    except:
        server_info = {
            "tts_engine": "MeloTTS",
            "stt_engine": "Whisper" if WhisperSTT else None,
            "streaming_support": MeloEngine is not None,
            "stt_support": WhisperSTT is not None,
            "conversation_support": (MeloEngine is not None and WhisperSTT is not None),
            "supported_languages": ["KR", "EN", "EN_V2", "EN_NEWEST", "ZH", "JP", "FR", "ES"]
        }

    return {
        "status": "healthy" if (tts_model is not None and stt_model is not None) else "degraded",
        "model_loaded": tts_model is not None,
        "server_info": server_info
    }

@app.websocket("/ws/tts")
async def websocket_tts(websocket: WebSocket):
    """
    WebSocket 엔드포인트로 실시간 TTS 스트리밍
    """
    await websocket.accept()

    if not MeloEngine:
        await websocket.close(code=1011, reason="MeloEngine not available")
        return

    try:
        # Initialize streaming TTS engine
        melo_engine = MeloEngine(language='KR', device='auto')
        stream = TextToAudioStream(melo_engine)

        print("WebSocket TTS connection established")
        await websocket.send_text("Connected to TTS streaming service")

        while True:
            try:
                # Receive text from client
                data = await websocket.receive_text()
                print(f"Received text: {data[:50]}...")

                # Handle special commands
                if data.startswith("CHANGE_LANGUAGE:"):
                    language = data.split(":")[1]
                    try:
                        melo_engine.set_voice_parameters(language=language)
                        await websocket.send_text(f"Language changed to {language}")
                        continue
                    except Exception as e:
                        await websocket.send_text(f"Error changing language: {e}")
                        continue

                if data.startswith("CHANGE_SPEAKER:"):
                    speaker_id = int(data.split(":")[1])
                    try:
                        melo_engine.set_voice_parameters(speaker_id=speaker_id)
                        await websocket.send_text(f"Speaker changed to {speaker_id}")
                        continue
                    except Exception as e:
                        await websocket.send_text(f"Error changing speaker: {e}")
                        continue

                # Send start marker
                await websocket.send_text("|AUDIO_START|")

                # Stream TTS audio
                await stream_tts_audio(stream, data, websocket)

                # Send end marker
                await websocket.send_text("|AUDIO_END|")

            except WebSocketDisconnect:
                print("WebSocket disconnected")
                break
            except Exception as e:
                print(f"Error in WebSocket TTS: {e}")
                await websocket.send_text(f"Error: {e}")
                break

    except Exception as e:
        print(f"WebSocket setup error: {e}")
        await websocket.close(code=1011, reason=str(e))
    finally:
        try:
            if 'stream' in locals():
                stream.stop()
            if 'melo_engine' in locals():
                melo_engine.shutdown()
        except:
            pass

async def stream_tts_audio(stream: TextToAudioStream, text: str, websocket: WebSocket):
    """
    Stream TTS audio data through WebSocket

    Args:
        stream: TextToAudioStream instance
        text: Text to synthesize
        websocket: WebSocket connection
    """
    try:
        # Start synthesis in a separate thread
        import threading
        import queue
        import time

        audio_queue = queue.Queue()
        synthesis_complete = threading.Event()

        def synthesize_and_queue():
            try:
                # Start streaming synthesis
                stream.feed(text)
                stream.play_async()

                # Get audio chunks from the stream
                while stream.is_playing() and not synthesis_complete.is_set():
                    try:
                        # Get audio chunk from the engine queue
                        if hasattr(stream.engine, 'queue'):
                            try:
                                chunk = stream.engine.queue.get(timeout=0.1)
                                if chunk is None:  # End of synthesis
                                    break
                                audio_queue.put(chunk)
                            except queue.Empty:
                                continue
                        else:
                            # Fallback: wait a bit and check again
                            time.sleep(0.1)
                    except Exception as e:
                        print(f"Error getting audio chunk: {e}")
                        break

            except Exception as e:
                print(f"Synthesis thread error: {e}")
            finally:
                synthesis_complete.set()
                audio_queue.put(None)  # Signal end

        # Start synthesis thread
        synthesis_thread = threading.Thread(target=synthesize_and_queue)
        synthesis_thread.start()

        # Stream audio chunks to WebSocket
        while True:
            try:
                chunk = audio_queue.get(timeout=5.0)  # 5 second timeout
                if chunk is None:  # End of synthesis
                    break

                # Send audio chunk
                await websocket.send_bytes(chunk)

            except queue.Empty:
                if synthesis_complete.is_set():
                    break
                continue
            except Exception as e:
                print(f"Error sending audio chunk: {e}")
                break

        # Wait for synthesis to complete
        synthesis_thread.join(timeout=10.0)

    except Exception as e:
        print(f"Stream TTS error: {e}")
        raise e

@app.websocket("/ws/stt")
async def websocket_stt(websocket: WebSocket):
    """
    WebSocket 엔드포인트로 실시간 STT (음성 → 텍스트)
    """
    await websocket.accept()

    if not WhisperSTT or not stt_model:
        await websocket.close(code=1011, reason="STT model not available")
        return

    try:
        print("WebSocket STT connection established")
        await websocket.send_text("Connected to STT streaming service")

        # STT 스트리밍 시작
        streaming_generator = stt_model.start_streaming_transcription()

        while True:
            try:
                # 클라이언트로부터 오디오 데이터 또는 명령어 받기
                data = await websocket.receive()

                if data["type"] == "websocket.receive":
                    if "bytes" in data:
                        # 오디오 데이터 처리
                        audio_bytes = data["bytes"]
                        stt_model.add_audio_chunk(audio_bytes)

                    elif "text" in data:
                        text_data = data["text"]

                        # 언어 변경 명령
                        if text_data.startswith("CHANGE_LANGUAGE:"):
                            language = text_data.split(":")[1]
                            stt_model.language = language if language != "auto" else None
                            await websocket.send_text(f"Language changed to {language}")
                            continue

                        # STT 중지 명령
                        if text_data == "STOP_STT":
                            stt_model.stop_streaming_transcription()
                            await websocket.send_text("STT stopped")
                            break

                # 변환 결과 확인 및 전송
                try:
                    result = next(streaming_generator)
                    if result and result.get("text"):
                        # 결과를 JSON으로 전송
                        import json
                        await websocket.send_text(json.dumps(result, ensure_ascii=False))
                except StopIteration:
                    break

            except WebSocketDisconnect:
                print("WebSocket STT disconnected")
                break
            except Exception as e:
                print(f"Error in WebSocket STT: {e}")
                await websocket.send_text(f"Error: {e}")
                break

    except Exception as e:
        print(f"WebSocket STT setup error: {e}")
        await websocket.close(code=1011, reason=str(e))
    finally:
        try:
            if stt_model:
                stt_model.stop_streaming_transcription()
        except:
            pass

@app.websocket("/ws/conversation")
async def websocket_conversation(websocket: WebSocket):
    """
    WebSocket 엔드포인트로 STT + TTS 통합 대화 시스템
    음성 입력 → 텍스트 변환 → TTS 음성 응답
    """
    await websocket.accept()

    if not WhisperSTT or not stt_model or not MeloEngine:
        await websocket.close(code=1011, reason="STT or TTS model not available")
        return

    try:
        # TTS 엔진 초기화
        melo_engine = MeloEngine(language='KR', device='auto')
        tts_stream = TextToAudioStream(melo_engine)

        print("WebSocket Conversation connection established")
        await websocket.send_text("Connected to conversation service (STT + TTS)")

        # STT 스트리밍 시작
        streaming_generator = stt_model.start_streaming_transcription()

        while True:
            try:
                # 클라이언트로부터 데이터 받기
                data = await websocket.receive()

                if data["type"] == "websocket.receive":
                    if "bytes" in data:
                        # 오디오 데이터를 STT로 처리
                        audio_bytes = data["bytes"]
                        stt_model.add_audio_chunk(audio_bytes)

                    elif "text" in data:
                        text_data = data["text"]

                        # 언어 변경 명령
                        if text_data.startswith("CHANGE_LANGUAGE:"):
                            language = text_data.split(":")[1]
                            stt_model.language = language if language != "auto" else None
                            melo_engine.set_voice_parameters(language=language)
                            await websocket.send_text(f"Language changed to {language}")
                            continue

                        # 직접 텍스트 입력 (TTS만 실행)
                        if text_data.startswith("TTS:"):
                            tts_text = text_data[4:]  # "TTS:" 제거
                            await websocket.send_text("|AUDIO_START|")
                            await stream_tts_audio(tts_stream, tts_text, websocket)
                            await websocket.send_text("|AUDIO_END|")
                            continue

                        # 대화 종료
                        if text_data == "END_CONVERSATION":
                            await websocket.send_text("Conversation ended")
                            break

                # STT 결과 확인
                try:
                    stt_result = next(streaming_generator)
                    if stt_result and stt_result.get("text"):
                        recognized_text = stt_result["text"]

                        # STT 결과 전송
                        import json
                        await websocket.send_text(json.dumps({
                            "type": "stt_result",
                            "text": recognized_text,
                            "language": stt_result.get("language", "unknown"),
                            "confidence": stt_result.get("confidence", 0.0)
                        }, ensure_ascii=False))

                        # 인식된 텍스트를 TTS로 응답 (에코 기능)
                        if recognized_text.strip():
                            response_text = f"인식됨: {recognized_text}"

                            await websocket.send_text("|AUDIO_START|")
                            await stream_tts_audio(tts_stream, response_text, websocket)
                            await websocket.send_text("|AUDIO_END|")

                except StopIteration:
                    break

            except WebSocketDisconnect:
                print("WebSocket Conversation disconnected")
                break
            except Exception as e:
                print(f"Error in WebSocket Conversation: {e}")
                await websocket.send_text(f"Error: {e}")
                break

    except Exception as e:
        print(f"WebSocket Conversation setup error: {e}")
        await websocket.close(code=1011, reason=str(e))
    finally:
        try:
            if stt_model:
                stt_model.stop_streaming_transcription()
            if 'tts_stream' in locals():
                tts_stream.stop()
            if 'melo_engine' in locals():
                melo_engine.shutdown()
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    print("Korean TTS API 서버 시작...")
    print("사용법:")
    print("  POST /tts - 텍스트를 음성으로 변환")
    print("  WebSocket /ws/tts - 실시간 TTS 스트리밍")
    print("  GET /health - 서버 상태 확인")
    print("  GET / - 기본 정보")
    print("\n서버 주소: http://localhost:6001")
    print("WebSocket 주소: ws://localhost:6001/ws/tts")

    uvicorn.run(app, host="0.0.0.0", port=6001)