"""
MeloTTS Engine for RealtimeTTS
Custom engine integrating MeloTTS with RealtimeTTS framework
"""

import os
import sys
import tempfile
import warnings
import numpy as np
import pyaudio
from typing import Union
from pathlib import Path

warnings.filterwarnings("ignore")

# Add MeloTTS to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'MeloTTS'))

from RealtimeTTS.engines.base_engine import BaseEngine

try:
    from melo.api import TTS
except ImportError as e:
    print(f"MeloTTS not found: {e}")
    raise ImportError("MeloTTS is required for this engine")


class MeloVoice:
    def __init__(self, language: str, speaker_id: int = 0):
        self.language = language
        self.speaker_id = speaker_id
        self.name = f"{language}_speaker_{speaker_id}"

    def __repr__(self):
        return self.name


class MeloEngine(BaseEngine):
    def __init__(self, language: str = 'KR', device: str = 'auto', speaker_id: int = 0):
        """
        Initialize MeloTTS engine for RealtimeTTS

        Args:
            language (str): Language code (KR, EN, ZH, JP, etc.)
            device (str): Device to use ('cpu', 'cuda', 'auto')
            speaker_id (int): Speaker ID for voice
        """
        self.language = language
        self.device = device
        self.speaker_id = speaker_id
        self.tts_model = None

        # Initialize TTS model
        try:
            self.tts_model = TTS(language=language, device=device)
            print(f"✓ MeloTTS model loaded: {language} on {device}")
        except Exception as e:
            print(f"✗ Failed to load MeloTTS model: {e}")
            raise e

    def post_init(self):
        """Called after BaseEngine.__init__"""
        self.engine_name = "melo"

    def get_stream_info(self):
        """
        Returns PyAudio stream configuration for MeloTTS

        Returns:
            tuple: (format, channels, sample_rate)
        """
        return pyaudio.paInt16, 1, 24000  # MeloTTS default: 24kHz, mono, 16-bit

    def synthesize(self, text: str) -> bool:
        """
        Synthesize text and put audio chunks into queue

        Args:
            text (str): Text to synthesize

        Returns:
            bool: True if synthesis was successful
        """
        if not self.tts_model:
            return False

        try:
            # Call parent method to clear stop event
            super().synthesize(text)

            # Create temporary file for audio output
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name

            # Generate audio
            self.tts_model.tts_to_file(
                text=text,
                speaker_id=self.speaker_id,
                output_path=temp_path,
                speed=1.0,
                quiet=True
            )

            # Read audio file and convert to numpy array
            audio_data = self._load_audio_file(temp_path)

            # Clean up temp file
            os.unlink(temp_path)

            if audio_data is not None:
                # Apply audio processing (trim silence, fade)
                audio_data = self._trim_silence(audio_data)

                # Convert to int16 format for streaming
                audio_int16 = (audio_data * 32767).astype(np.int16)

                # Split into chunks and put into queue
                chunk_size = 1024  # Audio chunk size
                for i in range(0, len(audio_int16), chunk_size):
                    if self.stop_synthesis_event.is_set():
                        break

                    chunk = audio_int16[i:i + chunk_size]
                    self.queue.put(chunk.tobytes())

                # Signal end of synthesis
                self.queue.put(None)
                return True

        except Exception as e:
            print(f"Synthesis error: {e}")
            self.queue.put(None)
            return False

        return False

    def _load_audio_file(self, file_path: str) -> np.ndarray:
        """
        Load audio file and return as numpy array

        Args:
            file_path (str): Path to audio file

        Returns:
            np.ndarray: Audio data as float32 array
        """
        try:
            import librosa
            audio_data, _ = librosa.load(file_path, sr=24000, mono=True)
            return audio_data.astype(np.float32)
        except ImportError:
            # Fallback to wave module
            import wave
            with wave.open(file_path, 'rb') as wav_file:
                frames = wav_file.readframes(-1)
                audio_data = np.frombuffer(frames, dtype=np.int16)
                # Convert to float32 and normalize
                audio_data = audio_data.astype(np.float32) / 32768.0
                return audio_data
        except Exception as e:
            print(f"Error loading audio file: {e}")
            return None

    def get_voices(self):
        """
        Get available voices for current language

        Returns:
            list: List of available MeloVoice objects
        """
        # For MeloTTS, voices are typically differentiated by speaker_id
        # The exact number depends on the model
        voices = []

        # Most MeloTTS models have at least 1 speaker (speaker_id=0)
        if self.language == 'KR':
            voices = [MeloVoice(self.language, i) for i in range(1)]  # Korean usually has 1 speaker
        elif self.language in ['EN', 'EN_V2', 'EN_NEWEST']:
            voices = [MeloVoice(self.language, i) for i in range(1)]  # English variants
        elif self.language == 'ZH':
            voices = [MeloVoice(self.language, i) for i in range(10)]  # Chinese may have more speakers
        else:
            voices = [MeloVoice(self.language, 0)]  # Default single speaker

        return voices

    def set_voice(self, voice: Union[str, MeloVoice]):
        """
        Set the voice for synthesis

        Args:
            voice (Union[str, MeloVoice]): Voice to set
        """
        if isinstance(voice, str):
            # Parse voice string (e.g., "KR_speaker_0")
            if "_speaker_" in voice:
                parts = voice.split("_speaker_")
                if len(parts) == 2:
                    self.language = parts[0]
                    self.speaker_id = int(parts[1])
            else:
                # Assume it's a language code
                self.language = voice
                self.speaker_id = 0
        elif isinstance(voice, MeloVoice):
            self.language = voice.language
            self.speaker_id = voice.speaker_id

        # Reinitialize TTS model if language changed
        try:
            self.tts_model = TTS(language=self.language, device=self.device)
        except Exception as e:
            print(f"Error changing voice: {e}")

    def set_voice_parameters(self, **voice_parameters):
        """
        Set voice parameters

        Args:
            **voice_parameters: Parameters like speaker_id, speed, etc.
        """
        if 'speaker_id' in voice_parameters:
            self.speaker_id = voice_parameters['speaker_id']

        if 'language' in voice_parameters:
            self.language = voice_parameters['language']
            # Reinitialize model with new language
            try:
                self.tts_model = TTS(language=self.language, device=self.device)
            except Exception as e:
                print(f"Error changing language: {e}")

    def shutdown(self):
        """
        Shutdown the engine
        """
        if self.tts_model:
            del self.tts_model
            self.tts_model = None
        super().shutdown()