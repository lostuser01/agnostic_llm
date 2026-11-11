"""macOS Voice Engine.
Provides native text-to-speech synthesis (using macOS `say`), voice profiles per employee,
asynchronous speech queue, audio file generation, and voice chat interaction helpers.
"""
from __future__ import annotations
import logging
import os
import re
import shlex
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

log = logging.getLogger("agnostic_llm.voice")

# Voice profiles assigned to employee personas
DEFAULT_EMPLOYEE_VOICES = {
    "alex": "Samantha",     # Chief of Staff - poised, executive, clear
    "morgan": "Daniel",     # Freelance & BizDev - confident, articulate, persuasive
    "taylor": "Karen",      # Marketing - energetic, dynamic, engaging
    "elena": "Moira",       # High-Empathy Wordsmith - warm, reflective, resonant
    "supervisor": "Samantha",
    "default": "Samantha",
}


@dataclass
class VoiceInfo:
    name: str
    locale: str
    sample: str


class VoiceEngine:
    """Manages speech synthesis on macOS via native `say` and audio generation."""

    def __init__(self, default_rate: int = 185, enabled: bool = True):
        self.default_rate = default_rate
        self.enabled = enabled
        self._current_proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._voices_cache: Optional[list[VoiceInfo]] = None

    def get_available_voices(self) -> list[VoiceInfo]:
        """List all voices installed on the current macOS system."""
        if self._voices_cache is not None:
            return self._voices_cache
        voices: list[VoiceInfo] = []
        try:
            res = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    match = re.match(r"^([\w\s\-]+?)\s+([a-z]{2}_[A-Z]{2})\s+#\s*(.*)$", line.strip())
                    if match:
                        name, locale, sample = match.groups()
                        voices.append(VoiceInfo(name=name.strip(), locale=locale.strip(), sample=sample.strip()))
        except Exception as e:
            log.warning("Could not list macOS voices: %s", e)
        self._voices_cache = voices
        return voices

    def get_voice_for_employee(self, employee_name: str) -> str:
        """Resolve the optimal macOS voice for an employee persona."""
        desired = DEFAULT_EMPLOYEE_VOICES.get(employee_name.lower(), "Samantha")
        all_voices = [v.name.lower() for v in self.get_available_voices()]
        if not all_voices:
            return desired
        if desired.lower() in all_voices:
            return desired
        # Fallback to Samantha, Daniel, or the first English voice
        for fallback in ["Samantha", "Daniel", "Karen", "Alex", "Fred"]:
            if fallback.lower() in all_voices:
                return fallback
        return desired

    def stop_speaking(self):
        """Cancel any ongoing speech."""
        with self._lock:
            if self._current_proc and self._current_proc.poll() is None:
                try:
                    self._current_proc.terminate()
                    self._current_proc.wait(timeout=1)
                except Exception:
                    pass
                self._current_proc = None

    def clean_text_for_speech(self, text: str) -> str:
        """Clean markdown formatting, code blocks, URLs, and tool markers for natural speech."""
        # Strip code blocks
        t = re.sub(r"```[\s\S]*?```", " [Code omitted] ", text)
        # Strip inline code
        t = re.sub(r"`([^`]+)`", r"\1", t)
        # Strip links [text](url) -> text
        t = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", t)
        # Strip markdown headers, bold, italics, bullets
        t = re.sub(r"[#*_~>]+", " ", t)
        t = re.sub(r"^\s*-\s+", "", t, flags=re.MULTILINE)
        # Strip excess whitespace
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def speak(self, text: str, voice: Optional[str] = None, rate: Optional[int] = None,
              wait: bool = False, employee_name: Optional[str] = None) -> bool:
        """Speak text aloud using macOS `say`. Non-blocking by default."""
        if not self.enabled:
            return False

        clean_text = self.clean_text_for_speech(text)
        if not clean_text:
            return False

        resolved_voice = voice or (self.get_voice_for_employee(employee_name) if employee_name else "Samantha")
        actual_rate = rate or self.default_rate

        self.stop_speaking()

        cmd = ["say", "-v", resolved_voice, "-r", str(actual_rate), clean_text]

        try:
            with self._lock:
                self._current_proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            if wait and self._current_proc:
                self._current_proc.wait()
            return True
        except Exception as e:
            log.warning("Speech synthesis error: %s", e)
            return False

    def generate_audio_file(self, text: str, output_path: str | Path,
                            voice: Optional[str] = None, rate: Optional[int] = None) -> bool:
        """Synthesize text and save to an audio file (.aiff or .wav) on disk."""
        clean_text = self.clean_text_for_speech(text)
        if not clean_text:
            return False

        resolved_voice = voice or "Samantha"
        actual_rate = rate or self.default_rate
        out_str = str(output_path)

        cmd = ["say", "-v", resolved_voice, "-r", str(actual_rate), "-o", out_str, clean_text]
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=30)
            return res.returncode == 0 and os.path.exists(out_str)
        except Exception as e:
            log.warning("Error generating audio file: %s", e)
            return False


# Shared singleton voice engine
voice_engine = VoiceEngine()
