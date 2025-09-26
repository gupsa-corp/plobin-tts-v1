#!/usr/bin/env python3
"""
Korean TTS GUI Application - Final Working Version
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

# Try importing GUI libraries
try:
    import customtkinter as ctk
    import tkinter as tk
    USE_MODERN_UI = True
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
except ImportError:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    USE_MODERN_UI = False

# Try importing audio
try:
    import pygame
    AUDIO_AVAILABLE = True
    pygame.mixer.init()
except ImportError:
    AUDIO_AVAILABLE = False

class KoreanTTSGUI:
    def __init__(self):
        if USE_MODERN_UI:
            self.root = ctk.CTk()
        else:
            self.root = tk.Tk()

        self.root.title("한국어 TTS 변환기")
        self.root.geometry("600x400")

        self.tts_model = None
        self.current_audio_file = None

        self.setup_ui()
        self.load_model()

    def setup_ui(self):
        """UI 구성"""
        if USE_MODERN_UI:
            self.setup_modern_ui()
        else:
            self.setup_classic_ui()

    def setup_modern_ui(self):
        """Modern UI with CustomTkinter"""
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Title
        title = ctk.CTkLabel(main_frame, text="한국어 TTS 변환기",
                           font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=15)

        # Text input
        text_label = ctk.CTkLabel(main_frame, text="변환할 텍스트:",
                                font=ctk.CTkFont(size=12))
        text_label.pack(anchor="w", padx=15, pady=(10, 5))

        self.text_input = ctk.CTkTextbox(main_frame, height=80,
                                       font=ctk.CTkFont(size=11))
        self.text_input.pack(fill="x", padx=15, pady=(0, 15))
        self.text_input.insert("1.0", "안녕하세요. 한국어 텍스트 음성 변환 테스트입니다.")

        # Settings
        settings_frame = ctk.CTkFrame(main_frame)
        settings_frame.pack(fill="x", padx=15, pady=10)

        speed_label = ctk.CTkLabel(settings_frame, text="속도:",
                                 font=ctk.CTkFont(size=11))
        speed_label.pack(side="left", padx=15, pady=10)

        self.speed_var = tk.StringVar(value="1.0")
        speed_entry = ctk.CTkEntry(settings_frame, textvariable=self.speed_var, width=60)
        speed_entry.pack(side="left", padx=10, pady=10)

        speed_info = ctk.CTkLabel(settings_frame, text="(0.5-2.0)",
                                font=ctk.CTkFont(size=10))
        speed_info.pack(side="left", padx=10, pady=10)

        # Buttons
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(pady=15)

        self.convert_button = ctk.CTkButton(button_frame, text="🎤 변환",
                                          command=self.convert_text_threaded,
                                          width=80, height=35)
        self.convert_button.pack(side="left", padx=5)

        if AUDIO_AVAILABLE:
            self.play_button = ctk.CTkButton(button_frame, text="▶️ 재생",
                                           command=self.play_audio,
                                           width=80, height=35, state="disabled")
            self.play_button.pack(side="left", padx=5)

        self.save_button = ctk.CTkButton(button_frame, text="💾 저장",
                                       command=self.save_audio,
                                       width=80, height=35, state="disabled")
        self.save_button.pack(side="left", padx=5)

        # Status
        self.status_label = ctk.CTkLabel(main_frame, text="모델 로딩 중...",
                                       font=ctk.CTkFont(size=11))
        self.status_label.pack(pady=15)

    def setup_classic_ui(self):
        """Classic UI with tkinter"""
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Title
        title_label = tk.Label(main_frame, text="한국어 TTS 변환기",
                             font=("Arial", 16, "bold"))
        title_label.pack(pady=15)

        # Text input
        tk.Label(main_frame, text="변환할 텍스트:", font=("Arial", 10)).pack(anchor="w", pady=(10, 2))

        self.text_input = tk.Text(main_frame, height=5, font=("Arial", 9), wrap="word")
        self.text_input.pack(fill="x", pady=(0, 15))
        self.text_input.insert("1.0", "안녕하세요. 한국어 텍스트 음성 변환 테스트입니다.")

        # Settings
        settings_frame = tk.LabelFrame(main_frame, text="설정")
        settings_frame.pack(fill="x", pady=10)

        tk.Label(settings_frame, text="속도:").pack(side="left", padx=10, pady=5)
        self.speed_var = tk.StringVar(value="1.0")
        tk.Entry(settings_frame, textvariable=self.speed_var, width=8).pack(side="left", padx=5, pady=5)
        tk.Label(settings_frame, text="(0.5-2.0)").pack(side="left", padx=5, pady=5)

        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(pady=15)

        self.convert_button = tk.Button(button_frame, text="변환", command=self.convert_text_threaded)
        self.convert_button.pack(side="left", padx=5)

        if AUDIO_AVAILABLE:
            self.play_button = tk.Button(button_frame, text="재생", command=self.play_audio, state="disabled")
            self.play_button.pack(side="left", padx=5)

        self.save_button = tk.Button(button_frame, text="저장", command=self.save_audio, state="disabled")
        self.save_button.pack(side="left", padx=5)

        # Status
        self.status_label = tk.Label(main_frame, text="모델 로딩 중...", font=("Arial", 9))
        self.status_label.pack(pady=15)

    def load_model(self):
        """TTS 모델 로딩"""
        def load():
            try:
                self.update_status("한국어 TTS 모델 로딩 중...")

                # 실제 모델 로드
                from melo.api import TTS
                self.tts_model = TTS(language='KR', device='cpu')

                self.update_status("✅ 모델 로딩 완료! 텍스트를 입력하고 변환하세요.")
                self.enable_button(self.convert_button)

            except Exception as e:
                error_msg = f"❌ 모델 로딩 실패: {str(e)}"
                self.update_status(error_msg)
                print(f"모델 로딩 오류 상세: {e}")

        threading.Thread(target=load, daemon=True).start()

    def convert_text_threaded(self):
        """텍스트 변환 (스레드)"""
        threading.Thread(target=self.convert_text, daemon=True).start()

    def convert_text(self):
        """텍스트를 음성으로 변환"""
        if not self.tts_model:
            self.show_error("TTS 모델이 로드되지 않았습니다.")
            return

        text = self.get_text_input().strip()
        if not text:
            self.show_warning("변환할 텍스트를 입력해주세요.")
            return

        try:
            self.update_status("🔄 음성 변환 중...")
            self.disable_button(self.convert_button)

            # 속도 설정
            try:
                speed = float(self.speed_var.get())
                speed = max(0.5, min(2.0, speed))
            except:
                speed = 1.0

            # 임시 파일 생성
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name

            # TTS 변환 실행
            self.tts_model.tts_to_file(
                text=text,
                speaker_id=0,
                output_path=temp_path,
                speed=speed,
                quiet=True
            )

            self.current_audio_file = temp_path
            self.update_status("✅ 음성 변환 완료!")

            # 버튼 활성화
            if AUDIO_AVAILABLE:
                self.enable_button(self.play_button)
            self.enable_button(self.save_button)
            self.enable_button(self.convert_button)

        except Exception as e:
            self.update_status(f"❌ 변환 실패: {str(e)}")
            self.enable_button(self.convert_button)
            self.show_error(f"음성 변환 오류:\\n{str(e)}")

    def play_audio(self):
        """음성 재생"""
        if not AUDIO_AVAILABLE:
            self.show_info("오디오 재생 기능을 사용할 수 없습니다.")
            return

        if not self.current_audio_file or not os.path.exists(self.current_audio_file):
            self.show_warning("재생할 음성 파일이 없습니다.")
            return

        try:
            pygame.mixer.music.load(self.current_audio_file)
            pygame.mixer.music.play()
            self.update_status("🔊 재생 중...")
        except Exception as e:
            self.show_error(f"재생 오류:\\n{str(e)}")

    def save_audio(self):
        """음성 파일 저장"""
        if not self.current_audio_file or not os.path.exists(self.current_audio_file):
            self.show_warning("저장할 음성 파일이 없습니다.")
            return

        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            title="음성 파일 저장",
            defaultextension=".wav",
            filetypes=[("WAV 파일", "*.wav"), ("모든 파일", "*.*")]
        )

        if file_path:
            try:
                import shutil
                shutil.copy2(self.current_audio_file, file_path)
                self.update_status(f"💾 저장 완료: {os.path.basename(file_path)}")
                self.show_info(f"파일이 저장되었습니다:\\n{file_path}")
            except Exception as e:
                self.show_error(f"저장 오류:\\n{str(e)}")

    # 유틸리티 메서드
    def get_text_input(self):
        return self.text_input.get("1.0", "end-1c")

    def update_status(self, text):
        if USE_MODERN_UI:
            self.status_label.configure(text=text)
        else:
            self.status_label.config(text=text)

    def enable_button(self, button):
        if USE_MODERN_UI:
            button.configure(state="normal")
        else:
            button.config(state="normal")

    def disable_button(self, button):
        if USE_MODERN_UI:
            button.configure(state="disabled")
        else:
            button.config(state="disabled")

    def show_error(self, message):
        from tkinter import messagebox
        messagebox.showerror("오류", message)

    def show_warning(self, message):
        from tkinter import messagebox
        messagebox.showwarning("경고", message)

    def show_info(self, message):
        from tkinter import messagebox
        messagebox.showinfo("정보", message)

    def run(self):
        """GUI 실행"""
        self.root.mainloop()

def main():
    print("한국어 TTS GUI 시작...")
    print(f"Modern UI: {'Yes' if USE_MODERN_UI else 'No'}")
    print(f"Audio Support: {'Yes' if AUDIO_AVAILABLE else 'No'}")

    try:
        app = KoreanTTSGUI()
        app.run()
    except Exception as e:
        print(f"GUI 실행 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()