#!/usr/bin/env python3
"""
Korean TTS using MeloTTS
Simple interface for Korean text-to-speech synthesis
"""

import os
import sys
import torch
import argparse

# Add MeloTTS to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'MeloTTS'))

from melo.api import TTS

class KoreanTTS:
    def __init__(self, device='auto'):
        """Initialize Korean TTS model"""
        print("한국어 TTS 모델 초기화 중...")
        try:
            self.model = TTS(language='KR', device=device)
            print("한국어 TTS 모델 로드 완료!")
        except Exception as e:
            print(f"모델 로드 실패: {e}")
            raise

    def synthesize(self, text, output_path, speaker_id=0, speed=1.0):
        """
        한국어 텍스트를 음성으로 변환

        Args:
            text (str): 변환할 한국어 텍스트
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
    parser = argparse.ArgumentParser(description='한국어 TTS')
    parser.add_argument('--text', '-t', type=str, required=True, help='변환할 텍스트')
    parser.add_argument('--output', '-o', type=str, default='output.wav', help='출력 파일명')
    parser.add_argument('--speaker', '-s', type=int, default=0, help='화자 ID')
    parser.add_argument('--speed', type=float, default=1.0, help='음성 속도')
    parser.add_argument('--device', type=str, default='auto', help='디바이스 (cpu/cuda/mps/auto)')

    args = parser.parse_args()

    # TTS 모델 초기화
    tts = KoreanTTS(device=args.device)

    # 음성 합성 실행
    tts.synthesize(
        text=args.text,
        output_path=args.output,
        speaker_id=args.speaker,
        speed=args.speed
    )

if __name__ == "__main__":
    main()