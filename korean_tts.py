#!/usr/bin/env python3
"""
Korean TTS using MeloTTS
Simple interface for Korean text-to-speech synthesis
"""

import os
import sys
import argparse

# PyTorch 설치 확인
try:
    import torch
except ImportError:
    print("\n" + "="*50)
    print("❌ PyTorch가 설치되지 않았습니다!")
    print("가상환경을 사용하여 실행해주세요:")
    print("")
    print("  ./run_tts.sh \"변환할 텍스트\" \"언어\" \"디바이스\"")
    print("")
    print("예시:")
    print("  ./run_tts.sh \"안녕하세요\" \"KR\" \"auto\"")
    print("  ./run_tts.sh \"Hello World\" \"EN\" \"auto\"")
    print("")
    print("또는 직접 가상환경을 활성화:")
    print("  source korean_tts_env/bin/activate")
    print("  python3 korean_tts.py --text \"안녕하세요\" --language KR")
    print("="*50)
    sys.exit(1)

# Add MeloTTS to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'MeloTTS'))

from melo.api import TTS

class MeloTTS:
    def __init__(self, language='KR', device='auto'):
        """Initialize MeloTTS model"""
        print(f"{language} TTS 모델 초기화 중...")

        if device == 'auto':
            device = 'cuda' if torch.cuda.is_available() else 'cpu'

        # VRAM 최적화 (10GB VRAM 대응)
        if device == 'cuda' and torch.cuda.is_available():
            torch.cuda.empty_cache()
            print(f"CUDA device: {torch.cuda.get_device_name()}")
            print(f"VRAM 사용량: {torch.cuda.memory_allocated()/1024**3:.1f}GB / {torch.cuda.memory_reserved()/1024**3:.1f}GB")

        print(f"Using language: {language}, device: {device}")

        try:
            self.model = TTS(language=language, device=device)
            print(f"{language} TTS 모델 로드 완료!")

            # 로드 후 VRAM 사용량 확인
            if device == 'cuda' and torch.cuda.is_available():
                print(f"모델 로드 후 VRAM: {torch.cuda.memory_allocated()/1024**3:.1f}GB / {torch.cuda.memory_reserved()/1024**3:.1f}GB")

        except Exception as e:
            print(f"모델 로드 실패: {e}")
            raise

    def synthesize(self, text, output_path, speaker_id=0, speed=1.0):
        """
        텍스트를 음성으로 변환

        Args:
            text (str): 변환할 텍스트
            output_path (str): 출력 파일 경로 (.wav)
            speaker_id (int): 화자 ID (기본값: 0)
            speed (float): 음성 속도 (기본값: 1.0)
        """
        print(f"텍스트 변환 중: {text}")
        try:
            self.model.tts_to_file(
                text=text,
                speaker_id=speaker_id,
                output_path=output_path,
                speed=speed,
                quiet=False
            )
            print(f"음성 파일 저장 완료: {output_path}")
        except Exception as e:
            print(f"음성 변환 실패: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description='MeloTTS - 다국어 음성 합성')
    parser.add_argument('--text', '-t', type=str, required=True, help='변환할 텍스트')
    parser.add_argument('--language', '-l', type=str, default='KR',
                       choices=['KR', 'EN', 'EN_V2', 'EN_NEWEST', 'ZH', 'JP', 'FR', 'ES'],
                       help='언어 선택 (기본: KR)')
    parser.add_argument('--output', '-o', type=str, default='output.wav', help='출력 파일명')
    parser.add_argument('--speaker', '-s', type=int, default=0, help='화자 ID')
    parser.add_argument('--speed', type=float, default=1.0, help='음성 속도')
    parser.add_argument('--device', type=str, default='auto', help='디바이스 (auto/cuda/cpu/mps - 기본값: auto)')

    args = parser.parse_args()

    # TTS 모델 초기화
    tts = MeloTTS(language=args.language, device=args.device)

    # 음성 합성 실행
    tts.synthesize(
        text=args.text,
        output_path=args.output,
        speaker_id=args.speaker,
        speed=args.speed
    )

if __name__ == "__main__":
    main()