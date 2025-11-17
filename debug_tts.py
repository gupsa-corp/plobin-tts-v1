#!/usr/bin/env python3
"""
TTS 디버깅 스크립트
"""

import os
import sys
import tempfile
import traceback
from pathlib import Path

# Add MeloTTS to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'MeloTTS'))

try:
    import torch
    from melo.api import TTS
    print("✅ TTS 모듈 임포트 성공")

    # TTS 모델 로드
    print("🔄 TTS 모델 로드 시작...")
    tts_model = TTS(language='KR', device='cuda' if torch.cuda.is_available() else 'cpu')
    print(f"✅ TTS 모델 로드 완료 (device: {tts_model.device})")

    # 테스트 텍스트
    test_text = "안녕하세요"
    print(f"📝 테스트 텍스트: {test_text}")

    # 화자 ID
    speaker_ids = tts_model.hps.data.spk2id
    speaker_key = list(speaker_ids.keys())[0]
    speaker_id = speaker_ids[speaker_key]
    print(f"🎭 화자 ID: {speaker_id} ({speaker_key})")

    # 오디오 생성 테스트
    print("🔄 음성 생성 시작...")

    # 임시 파일로 테스트
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        print(f"📁 임시 파일: {temp_file.name}")

        try:
            tts_model.tts_to_file(
                test_text,
                speaker_id,
                temp_file.name,
                speed=2.0
            )
            print(f"✅ 음성 생성 성공! 파일: {temp_file.name}")

            # 파일 크기 확인
            file_size = os.path.getsize(temp_file.name)
            print(f"📊 파일 크기: {file_size} bytes")

        except Exception as e:
            print(f"❌ 음성 생성 실패: {e}")
            print("상세 에러:")
            traceback.print_exc()

        finally:
            # 임시 파일 정리
            try:
                os.unlink(temp_file.name)
                print(f"🗑️ 임시 파일 삭제: {temp_file.name}")
            except:
                pass

except Exception as e:
    print(f"❌ 초기화 실패: {e}")
    traceback.print_exc()