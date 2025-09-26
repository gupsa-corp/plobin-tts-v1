#!/usr/bin/env python3
"""
Korean TTS GUI Application
한국어 텍스트를 음성으로 변환하는 GUI 애플리케이션
"""

import os
import sys
import threading
import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# Add MeloTTS to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'MeloTTS'))

try:
    import customtkinter as ctk
    import pygame
    from tkinter import filedialog, messagebox
    from melo.api import TTS
except ImportError as e:
    print(f"필요한 패키지가 설치되지 않았습니다: {e}")
    sys.exit(1)

# Modern theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class KoreanTTSGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("한국어 TTS 변환기")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # TTS model
        self.tts_model = None
        self.current_audio_file = None

        # Pygame mixer 초기화
        pygame.mixer.init()

        self.setup_ui()
        self.load_model()

    def setup_ui(self):
        """UI 구성"""
        # 메인 프레임
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # 제목
        title = ctk.CTkLabel(
            main_frame,
            text="한국어 TTS 변환기",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        title.pack(pady=(20, 30))

        # 텍스트 입력 섹션
        text_frame = ctk.CTkFrame(main_frame)
        text_frame.pack(fill="x", padx=20, pady=(0, 20))

        text_label = ctk.CTkLabel(
            text_frame,
            text="변환할 텍스트:",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        text_label.pack(anchor="w", padx=20, pady=(20, 10))

        self.text_input = ctk.CTkTextbox(
            text_frame,
            height=120,
            font=ctk.CTkFont(size=14),
            wrap="word"
        )
        self.text_input.pack(fill="x", padx=20, pady=(0, 20))
        self.text_input.insert("1.0", "안녕하세요. 한국어 텍스트를 음성으로 변환하는 프로그램입니다.")

        # 설정 섹션
        settings_frame = ctk.CTkFrame(main_frame)
        settings_frame.pack(fill="x", padx=20, pady=(0, 20))

        settings_label = ctk.CTkLabel(
            settings_frame,
            text="음성 설정:",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        settings_label.pack(anchor="w", padx=20, pady=(20, 10))

        # 설정 옵션들
        options_frame = ctk.CTkFrame(settings_frame)
        options_frame.pack(fill="x", padx=20, pady=(0, 20))

        # 속도 설정
        speed_frame = ctk.CTkFrame(options_frame)
        speed_frame.pack(fill="x", pady=10)

        speed_label = ctk.CTkLabel(speed_frame, text="음성 속도:", font=ctk.CTkFont(size=14))
        speed_label.pack(side="left", padx=20)

        self.speed_var = ctk.StringVar(value="1.0")
        speed_entry = ctk.CTkEntry(speed_frame, textvariable=self.speed_var, width=80)
        speed_entry.pack(side="left", padx=10)

        speed_info = ctk.CTkLabel(speed_frame, text="(0.5 ~ 2.0, 기본값: 1.0)", font=ctk.CTkFont(size=12))
        speed_info.pack(side="left", padx=10)

        # 화자 설정
        speaker_frame = ctk.CTkFrame(options_frame)
        speaker_frame.pack(fill="x", pady=10)

        speaker_label = ctk.CTkLabel(speaker_frame, text="화자 ID:", font=ctk.CTkFont(size=14))
        speaker_label.pack(side="left", padx=20)

        self.speaker_var = ctk.StringVar(value="0")
        speaker_entry = ctk.CTkEntry(speaker_frame, textvariable=self.speaker_var, width=80)
        speaker_entry.pack(side="left", padx=10)

        speaker_info = ctk.CTkLabel(speaker_frame, text="(0 이상의 정수)", font=ctk.CTkFont(size=12))
        speaker_info.pack(side="left", padx=10)

        # 버튼 섹션
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", padx=20, pady=(0, 20))

        buttons_container = ctk.CTkFrame(button_frame)
        buttons_container.pack(pady=20)

        # 변환 버튼
        self.convert_button = ctk.CTkButton(
            buttons_container,
            text="🎤 음성 변환",
            command=self.convert_text_threaded,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            width=150
        )
        self.convert_button.pack(side="left", padx=10)

        # 재생 버튼
        self.play_button = ctk.CTkButton(
            buttons_container,
            text="▶️ 재생",
            command=self.play_audio,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            width=120,
            state="disabled"
        )
        self.play_button.pack(side="left", padx=10)

        # 정지 버튼
        self.stop_button = ctk.CTkButton(
            buttons_container,
            text="⏹️ 정지",
            command=self.stop_audio,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            width=120,
            state="disabled"
        )
        self.stop_button.pack(side="left", padx=10)

        # 저장 버튼
        self.save_button = ctk.CTkButton(
            buttons_container,
            text="💾 저장",
            command=self.save_audio,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            width=120,
            state="disabled"
        )
        self.save_button.pack(side="left", padx=10)

        # 상태 표시 섹션
        status_frame = ctk.CTkFrame(main_frame)
        status_frame.pack(fill="x", padx=20, pady=(0, 20))

        self.status_label = ctk.CTkLabel(
            status_frame,
            text="모델 로딩 중...",
            font=ctk.CTkFont(size=14)
        )
        self.status_label.pack(pady=20)

        # 프로그레스 바
        self.progress = ctk.CTkProgressBar(status_frame)
        self.progress.pack(fill="x", padx=20, pady=(0, 20))
        self.progress.set(0)

    def load_model(self):
        """TTS 모델 로딩"""
        def load():
            try:
                self.status_label.configure(text="한국어 TTS 모델 로딩 중...")
                self.progress.set(0.3)

                self.tts_model = TTS(language='KR', device='cpu')

                self.progress.set(1.0)
                self.status_label.configure(text="✅ 모델 로딩 완료! 텍스트를 입력하고 변환 버튼을 눌러주세요.")
                self.convert_button.configure(state="normal")

            except Exception as e:
                self.status_label.configure(text=f"❌ 모델 로딩 실패: {str(e)}")
                self.progress.set(0)

        # 별도 스레드에서 모델 로딩
        threading.Thread(target=load, daemon=True).start()

    def convert_text_threaded(self):
        """텍스트 변환 (스레드)"""
        threading.Thread(target=self.convert_text, daemon=True).start()

    def convert_text(self):
        """텍스트를 음성으로 변환"""
        if not self.tts_model:
            messagebox.showerror("오류", "TTS 모델이 로드되지 않았습니다.")
            return

        text = self.text_input.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showwarning("경고", "변환할 텍스트를 입력해주세요.")
            return

        try:
            # UI 업데이트
            self.status_label.configure(text="음성 변환 중...")
            self.progress.set(0)
            self.convert_button.configure(state="disabled")

            # 속도와 화자 설정
            try:
                speed = float(self.speed_var.get())
                if speed < 0.5 or speed > 2.0:
                    speed = 1.0
            except:
                speed = 1.0

            try:
                speaker_id = int(self.speaker_var.get())
                if speaker_id < 0:
                    speaker_id = 0
            except:
                speaker_id = 0

            # 임시 파일 생성
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name

            self.progress.set(0.3)

            # TTS 변환
            self.tts_model.tts_to_file(
                text=text,
                speaker_id=speaker_id,
                output_path=temp_path,
                speed=speed,
                quiet=True
            )

            self.current_audio_file = temp_path
            self.progress.set(1.0)

            # UI 업데이트
            self.status_label.configure(text="✅ 음성 변환 완료!")
            self.play_button.configure(state="normal")
            self.save_button.configure(state="normal")
            self.convert_button.configure(state="normal")

        except Exception as e:
            self.status_label.configure(text=f"❌ 변환 실패: {str(e)}")
            self.progress.set(0)
            self.convert_button.configure(state="normal")
            messagebox.showerror("오류", f"음성 변환 중 오류가 발생했습니다:\\n{str(e)}")

    def play_audio(self):
        """음성 재생"""
        if not self.current_audio_file or not os.path.exists(self.current_audio_file):
            messagebox.showwarning("경고", "재생할 음성 파일이 없습니다.")
            return

        try:
            pygame.mixer.music.load(self.current_audio_file)
            pygame.mixer.music.play()

            self.status_label.configure(text="🔊 음성 재생 중...")
            self.play_button.configure(state="disabled")
            self.stop_button.configure(state="normal")

            # 재생 완료 확인
            self.check_playback()

        except Exception as e:
            messagebox.showerror("오류", f"음성 재생 중 오류가 발생했습니다:\\n{str(e)}")

    def check_playback(self):
        """재생 상태 확인"""
        if pygame.mixer.music.get_busy():
            self.root.after(100, self.check_playback)
        else:
            self.status_label.configure(text="▶️ 재생 완료")
            self.play_button.configure(state="normal")
            self.stop_button.configure(state="disabled")

    def stop_audio(self):
        """음성 정지"""
        pygame.mixer.music.stop()
        self.status_label.configure(text="⏹️ 재생 정지")
        self.play_button.configure(state="normal")
        self.stop_button.configure(state="disabled")

    def save_audio(self):
        """음성 파일 저장"""
        if not self.current_audio_file or not os.path.exists(self.current_audio_file):
            messagebox.showwarning("경고", "저장할 음성 파일이 없습니다.")
            return

        file_path = filedialog.asksaveasfilename(
            title="음성 파일 저장",
            defaultextension=".wav",
            filetypes=[("WAV 파일", "*.wav"), ("모든 파일", "*.*")]
        )

        if file_path:
            try:
                import shutil
                shutil.copy2(self.current_audio_file, file_path)
                self.status_label.configure(text=f"💾 파일 저장 완료: {os.path.basename(file_path)}")
                messagebox.showinfo("성공", f"음성 파일이 저장되었습니다:\\n{file_path}")
            except Exception as e:
                messagebox.showerror("오류", f"파일 저장 중 오류가 발생했습니다:\\n{str(e)}")

    def run(self):
        """GUI 실행"""
        self.root.mainloop()

def main():
    app = KoreanTTSGUI()
    app.run()

if __name__ == "__main__":
    main()