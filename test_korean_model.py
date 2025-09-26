#!/usr/bin/env python3
"""
Korean TTS Model Test
간단하게 한국어 TTS 모델 테스트
"""

import os
import sys
import warnings

warnings.filterwarnings("ignore")

# MeloTTS 경로 추가
sys.path.append('./MeloTTS')

def test_korean_tts():
    """한국어 TTS 테스트"""
    print("한국어 TTS 모델 테스트 시작")
    print("=" * 40)

    try:
        print("1. MeloTTS 라이브러리 import 중...")
        from melo.api import TTS

        print("2. 한국어 모델 로드 중...")
        model = TTS(language='KR', device='cpu')
        print("✅ 모델 로드 성공!")

        print("3. 테스트 텍스트 음성 변환 중...")
        test_text = "안녕하세요. 한국어 텍스트를 음성으로 변환하는 테스트입니다."
        output_file = "korean_test.wav"

        model.tts_to_file(
            text=test_text,
            speaker_id=0,
            output_path=output_file,
            speed=1.0,
            quiet=True
        )

        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"✅ 음성 변환 성공!")
            print(f"   출력 파일: {output_file}")
            print(f"   파일 크기: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
            return True
        else:
            print("❌ 음성 파일 생성 실패")
            return False

    except ImportError as e:
        print(f"❌ Import 오류: {e}")
        return False
    except Exception as e:
        print(f"❌ 모델 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_dependencies():
    """의존성 확인"""
    print("의존성 패키지 확인:")
    print("-" * 30)

    dependencies = [
        'torch',
        'torchaudio',
        'librosa',
        'transformers',
        'g2pkk',
        'jamo',
        'pykakasi',
        'protobuf',
        'huggingface_hub'
    ]

    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✅ {dep}")
        except ImportError:
            print(f"❌ {dep} - 설치 필요")

    print()

if __name__ == "__main__":
    check_dependencies()
    success = test_korean_tts()

    if success:
        print("\n" + "=" * 40)
        print("🎉 모든 테스트 완료!")
        print("이제 GUI 애플리케이션을 사용할 수 있습니다.")
        print("python korean_tts_gui_final.py")
    else:
        print("\n❌ 테스트 실패. 오류를 확인하고 다시 시도해주세요.")