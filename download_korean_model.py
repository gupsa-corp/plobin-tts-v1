#!/usr/bin/env python3
"""
MeloTTS Korean 모델 다운로드 스크립트
Hugging Face에서 한국어 TTS 모델을 직접 다운로드합니다.
"""

import os
import sys
import requests
from pathlib import Path
from huggingface_hub import hf_hub_download, snapshot_download

def download_korean_model():
    """한국어 TTS 모델 다운로드"""
    print("=" * 50)
    print("MeloTTS 한국어 모델 다운로드")
    print("=" * 50)

    model_repo = "myshell-ai/MeloTTS-Korean"

    try:
        print(f"1. {model_repo}에서 모델 다운로드 시도...")

        # 모델 저장 디렉토리 생성
        model_dir = Path("./models/korean")
        model_dir.mkdir(parents=True, exist_ok=True)

        print("2. 모델 파일들 다운로드 중...")

        # 전체 리포지토리 다운로드
        local_dir = snapshot_download(
            repo_id=model_repo,
            local_dir=str(model_dir),
            local_dir_use_symlinks=False
        )

        print(f"✅ 모델 다운로드 완료: {local_dir}")

        # 다운로드된 파일 확인
        print("\n3. 다운로드된 파일 목록:")
        for file_path in model_dir.rglob("*"):
            if file_path.is_file():
                size_mb = file_path.stat().st_size / (1024 * 1024)
                print(f"   - {file_path.name}: {size_mb:.1f} MB")

        return True

    except Exception as e:
        print(f"❌ 모델 다운로드 실패: {e}")

        # 대안: 개별 파일 다운로드 시도
        print("\n대안 방법으로 개별 파일 다운로드 시도...")
        try:
            essential_files = [
                "config.json",
                "G_latest.pth",
                "model.pth"
            ]

            for filename in essential_files:
                try:
                    print(f"다운로드 중: {filename}")
                    file_path = hf_hub_download(
                        repo_id=model_repo,
                        filename=filename,
                        local_dir=str(model_dir),
                        local_dir_use_symlinks=False
                    )
                    print(f"✅ {filename} 다운로드 완료")
                except Exception as file_error:
                    print(f"⚠️  {filename} 다운로드 실패: {file_error}")

            return True

        except Exception as alt_error:
            print(f"❌ 대안 다운로드도 실패: {alt_error}")
            return False

def test_model_download():
    """다운로드된 모델 테스트"""
    print("\n4. 다운로드된 모델 테스트...")

    try:
        # MeloTTS 경로 추가
        sys.path.append('./MeloTTS')

        from melo.api import TTS

        # 모델 로드 테스트
        print("모델 로드 테스트 중...")
        model = TTS(language='KR', device='cpu')

        print("✅ 모델 로드 성공!")

        # 간단한 음성 변환 테스트
        test_text = "안녕하세요. 모델 테스트입니다."
        output_path = "model_test.wav"

        print("음성 변환 테스트 중...")
        model.tts_to_file(
            text=test_text,
            speaker_id=0,
            output_path=output_path,
            speed=1.0,
            quiet=True
        )

        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ 음성 변환 성공! ({output_path}, {file_size} bytes)")
            return True
        else:
            print("❌ 음성 파일 생성 실패")
            return False

    except Exception as e:
        print(f"❌ 모델 테스트 실패: {e}")
        return False

def main():
    print("MeloTTS 한국어 모델 다운로드 스크립트 시작\n")

    # 모델 다운로드
    download_success = download_korean_model()

    if download_success:
        # 모델 테스트
        test_success = test_model_download()

        if test_success:
            print("\n" + "=" * 50)
            print("✅ 모든 작업이 성공적으로 완료되었습니다!")
            print("이제 GUI 애플리케이션을 실행할 수 있습니다.")
            print("python korean_tts_gui_final.py")
            print("=" * 50)
        else:
            print("\n⚠️  모델은 다운로드되었지만 테스트에 실패했습니다.")
            print("GUI에서 직접 테스트해보세요.")
    else:
        print("\n❌ 모델 다운로드에 실패했습니다.")
        print("인터넷 연결을 확인하고 다시 시도해주세요.")

if __name__ == "__main__":
    main()