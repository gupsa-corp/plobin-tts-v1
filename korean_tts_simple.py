#!/usr/bin/env python3
"""
Korean TTS using MeloTTS - Simple Test Version
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")

# Add MeloTTS to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'MeloTTS'))

def test_korean_tts():
    """Test Korean TTS functionality"""
    try:
        print("1. MeloTTS 모듈 import 시도...")
        from melo.api import TTS
        print("✓ MeloTTS import 성공!")

        print("2. 한국어 TTS 모델 초기화...")
        model = TTS(language='KR', device='cpu')
        print("✓ 모델 초기화 성공!")

        print("3. 간단한 텍스트 음성 변환 테스트...")
        text = "안녕하세요"
        output_file = "test_output.wav"

        model.tts_to_file(
            text=text,
            speaker_id=0,
            output_path=output_file,
            speed=1.0,
            quiet=True
        )

        if os.path.exists(output_file):
            print(f"✓ 음성 파일 생성 성공: {output_file}")
            file_size = os.path.getsize(output_file)
            print(f"  파일 크기: {file_size} bytes")
        else:
            print("✗ 음성 파일 생성 실패")

    except Exception as e:
        print(f"✗ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_korean_tts()