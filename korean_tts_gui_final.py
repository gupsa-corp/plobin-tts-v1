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
import glob
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

def find_model_files():
    """시스템에서 사용 가능한 TTS 모델 파일들을 찾기"""
    model_files = {}

    # 로컬 models 디렉토리
    local_models = glob.glob("models/**/checkpoint.pth", recursive=True)
    for model_path in local_models:
        model_name = os.path.basename(os.path.dirname(model_path))
        model_files[f"Local: {model_name}"] = model_path

    # Hugging Face 캐시
    hf_cache = os.path.expanduser("~/.cache/huggingface/hub")
    if os.path.exists(hf_cache):
        for item in os.listdir(hf_cache):
            if "melotts" in item.lower() or "tts" in item.lower():
                model_path = os.path.join(hf_cache, item)
                # 실제 모델 파일이 있는지 확인
                pth_files = glob.glob(f"{model_path}/**/pytorch_model.bin", recursive=True)
                if not pth_files:
                    pth_files = glob.glob(f"{model_path}/**/checkpoint.pth", recursive=True)
                if pth_files:
                    display_name = item.replace("models--", "").replace("--", "/")
                    model_files[f"HF: {display_name}"] = pth_files[0]

    # 기본 언어 옵션도 포함
    default_languages = ["KR", "EN", "EN_V2", "EN_NEWEST", "ZH", "JP", "FR", "ES"]
    for lang in default_languages:
        model_files[f"언어: {lang}"] = f"language:{lang}"

    return model_files

class KoreanTTSGUI:
    def __init__(self):
        if USE_MODERN_UI:
            self.root = ctk.CTk()
        else:
            self.root = tk.Tk()

        self.root.title("MeloTTS - 다국어 음성 변환기")
        self.root.geometry("800x500")

        self.tts_model = None
        self.current_audio_file = None
        self.current_language = None
        self.model_loading = False  # 모델 로딩 중복 방지

        # 사용 가능한 모델 파일들 검색
        self.model_files = find_model_files()
        print(f"발견된 모델 파일: {len(self.model_files)}개")

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
        title = ctk.CTkLabel(main_frame, text="MeloTTS - 다국어 음성 변환기",
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

        # Model selection
        model_label = ctk.CTkLabel(settings_frame, text="모델:",
                                 font=ctk.CTkFont(size=11))
        model_label.pack(side="left", padx=15, pady=10)

        self.model_var = tk.StringVar(value="언어: KR")
        self.model_var.trace('w', self.on_model_change)  # 모델 변경 감지
        model_options = list(self.model_files.keys())
        self.model_menu = ctk.CTkOptionMenu(settings_frame, values=model_options,
                                          variable=self.model_var, width=150)
        self.model_menu.pack(side="left", padx=10, pady=10)

        # Device selection
        device_label = ctk.CTkLabel(settings_frame, text="디바이스:",
                                  font=ctk.CTkFont(size=11))
        device_label.pack(side="left", padx=15, pady=10)

        self.device_var = tk.StringVar(value="auto")  # 자동 감지 기본값
        device_options = ["auto", "cuda", "cpu"]  # auto를 맨 앞으로
        device_menu = ctk.CTkOptionMenu(settings_frame, values=device_options,
                                      variable=self.device_var, width=80)
        device_menu.pack(side="left", padx=10, pady=10)

        # Speed
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

        self.reload_button = ctk.CTkButton(button_frame, text="🔄 모델 재로드",
                                         command=self.reload_model,
                                         width=100, height=35)
        self.reload_button.pack(side="left", padx=5)

        self.save_model_button = ctk.CTkButton(button_frame, text="📁 모델별 저장",
                                             command=self.save_with_model_name,
                                             width=120, height=35, state="disabled")
        self.save_model_button.pack(side="left", padx=5)

        # Status
        self.status_label = ctk.CTkLabel(main_frame, text="모델 로딩 중...",
                                       font=ctk.CTkFont(size=11))
        self.status_label.pack(pady=15)

    def setup_classic_ui(self):
        """Classic UI with tkinter"""
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Title
        title_label = tk.Label(main_frame, text="MeloTTS - 다국어 음성 변환기",
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

        # Model selection
        tk.Label(settings_frame, text="모델:").pack(side="left", padx=10, pady=5)
        self.model_var = tk.StringVar(value="언어: KR")
        self.model_var.trace('w', self.on_model_change)  # 모델 변경 감지
        model_options = list(self.model_files.keys())
        self.model_combo = ttk.Combobox(settings_frame, textvariable=self.model_var,
                                      values=model_options, state="readonly", width=15)
        self.model_combo.pack(side="left", padx=5, pady=5)

        # Device selection
        tk.Label(settings_frame, text="디바이스:").pack(side="left", padx=10, pady=5)
        self.device_var = tk.StringVar(value="auto")  # 자동 감지 기본값
        device_combo = ttk.Combobox(settings_frame, textvariable=self.device_var,
                                  values=["auto", "cuda", "cpu"], state="readonly", width=8)
        device_combo.pack(side="left", padx=5, pady=5)

        # Speed
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

        self.reload_button = tk.Button(button_frame, text="모델 재로드", command=self.reload_model)
        self.reload_button.pack(side="left", padx=5)

        self.save_model_button = tk.Button(button_frame, text="모델별 저장",
                                         command=self.save_with_model_name, state="disabled")
        self.save_model_button.pack(side="left", padx=5)

        # Status
        self.status_label = tk.Label(main_frame, text="모델 로딩 중...", font=("Arial", 9))
        self.status_label.pack(pady=15)

    def load_model(self):
        """TTS 모델 로딩"""
        def load():
            try:
                self.model_loading = True  # 로딩 시작

                # 실제 모델 로드 - 사용자 선택 모델/디바이스 사용
                import torch
                from melo.api import TTS

                model_selection = self.model_var.get()
                model_path = self.model_files.get(model_selection)

                device_choice = self.device_var.get()
                if device_choice == 'auto':
                    device = 'cuda' if torch.cuda.is_available() else 'cpu'
                else:
                    device = device_choice

                # VRAM 최적화 설정 (10GB VRAM 대응)
                if device == 'cuda':
                    torch.cuda.empty_cache()  # VRAM 정리
                    # VRAM 사용량 모니터링
                    if torch.cuda.is_available():
                        print(f"CUDA device: {torch.cuda.get_device_name()}")
                        print(f"VRAM 사용량: {torch.cuda.memory_allocated()/1024**3:.1f}GB / {torch.cuda.memory_reserved()/1024**3:.1f}GB")

                # 모델 로드 방식 결정
                if model_path.startswith("language:"):
                    # 언어 기반 로드
                    language = model_path.split(":")[1]
                    print(f"Using language model: {language}, device: {device}")
                    self.update_status(f"{language} 모델 로딩 중... ({device})")
                    self.tts_model = TTS(language=language, device=device)
                    self.current_model = language
                else:
                    # 파일 기반 로드 (향후 확장 가능)
                    language = "KR"  # 기본값
                    print(f"Using custom model: {model_selection}, device: {device}")
                    self.update_status(f"{model_selection} 모델 로딩 중... ({device})")
                    self.tts_model = TTS(language=language, device=device)
                    self.current_model = model_selection

                self.update_status("✅ 모델 로딩 완료! 텍스트를 입력하고 변환하세요.")
                self.enable_button(self.convert_button)

            except Exception as e:
                error_msg = f"❌ 모델 로딩 실패: {str(e)}"
                self.update_status(error_msg)
                print(f"모델 로딩 오류 상세: {e}")
                import traceback
                print("전체 오류 스택:")
                traceback.print_exc()
            finally:
                self.model_loading = False  # 로딩 완료

        threading.Thread(target=load, daemon=True).start()

    def on_model_change(self, *args):
        """모델 변경 시 자동으로 모델 재로드"""
        if self.model_loading:
            return  # 이미 로딩 중이면 무시

        new_model = self.model_var.get()
        if hasattr(self, 'current_model') and self.current_model and self.current_model != new_model:
            print(f"모델 변경 감지: {self.current_model} → {new_model}")
            self.reload_model()

    def reload_model(self):
        """모델 재로드"""
        self.tts_model = None
        self.disable_button(self.convert_button)
        if hasattr(self, 'play_button'):
            self.disable_button(self.play_button)
        self.disable_button(self.save_button)
        self.load_model()

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
            self.enable_button(self.save_model_button)  # 모델별 저장 버튼도 활성화
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

    def save_with_model_name(self):
        """현재 모델명을 포함한 파일명으로 저장"""
        if not self.current_audio_file or not os.path.exists(self.current_audio_file):
            self.show_warning("저장할 음성 파일이 없습니다.")
            return

        # 현재 모델과 텍스트로 파일명 생성
        model_name = getattr(self, 'current_model', 'unknown')
        text_sample = self.get_text_input()[:20]  # 텍스트 첫 20자

        # 파일명에 사용할 수 없는 문자 제거
        safe_model = "".join(c for c in model_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_text = "".join(c for c in text_sample if c.isalnum() or c in (' ', '-', '_')).strip()

        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        default_filename = f"{safe_model}_{safe_text}_{timestamp}.wav"

        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            title="모델별 음성 파일 저장",
            initialname=default_filename,
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

    # PyTorch 설치 확인
    try:
        import torch
    except ImportError:
        print("\n" + "="*50)
        print("❌ PyTorch가 설치되지 않았습니다!")
        print("가상환경을 사용하여 실행해주세요:")
        print("")
        print("  ./run_gui.sh")
        print("")
        print("또는 직접 가상환경을 활성화:")
        print("  source korean_tts_env/bin/activate")
        print("  python3 korean_tts_gui_final.py")
        print("="*50)
        return

    try:
        app = KoreanTTSGUI()
        app.run()
    except Exception as e:
        print(f"GUI 실행 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()