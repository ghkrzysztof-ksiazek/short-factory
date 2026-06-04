import struct
import wave
from pathlib import Path

from short_factory.config.logging import get_logger
from short_factory.config.settings import settings

logger = get_logger(__name__)


def generate_speech(text: str, output_path: Path) -> tuple[Path, float, list[dict]]:
    if settings.tts_provider == "openai" and settings.openai_api_key:
        return _openai_tts(text, output_path)
    if settings.elevenlabs_api_key:
        return _elevenlabs_tts(text, output_path)
    logger.warning("tts_credentials_missing", using="silent_placeholder")
    return _placeholder_audio(text, output_path)


def _openai_tts(text: str, output_path: Path) -> tuple[Path, float, list[dict]]:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    response = client.audio.speech.create(
        model="tts-1",
        voice=settings.openai_tts_voice,
        input=text,
        response_format="mp3",
    )
    response.stream_to_file(str(output_path))
    duration = _estimate_duration(text)
    timing = _estimate_word_timing(text, duration)
    return output_path, duration, timing


def _elevenlabs_tts(text: str, output_path: Path) -> tuple[Path, float, list[dict]]:
    import httpx

    output_path.parent.mkdir(parents=True, exist_ok=True)
    response = httpx.post(
        "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM",
        headers={"xi-api-key": settings.elevenlabs_api_key, "Content-Type": "application/json"},
        json={"text": text, "model_id": "eleven_monolingual_v1"},
        timeout=60,
    )
    response.raise_for_status()
    output_path.write_bytes(response.content)
    duration = _estimate_duration(text)
    timing = _estimate_word_timing(text, duration)
    return output_path, duration, timing


def _placeholder_audio(text: str, output_path: Path) -> tuple[Path, float, list[dict]]:
    duration = _estimate_duration(text)
    output_path = output_path.with_suffix(".wav")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 22050
    n_frames = int(sample_rate * duration)
    with wave.open(str(output_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack("<h", 0) * n_frames)
    timing = _estimate_word_timing(text, duration)
    return output_path, duration, timing


def _estimate_duration(text: str) -> float:
    word_count = len(text.split())
    return max(1.0, word_count / 2.5)


def _estimate_word_timing(text: str, total_duration: float) -> list[dict]:
    words = text.split()
    if not words:
        return []
    word_duration = total_duration / len(words)
    timing = []
    for i, word in enumerate(words):
        timing.append({"word": word, "start": i * word_duration, "end": (i + 1) * word_duration})
    return timing


def merge_audio_files(paths: list[Path], output_path: Path) -> Path:
    import subprocess

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if len(paths) == 1:
        import shutil

        shutil.copy2(paths[0], output_path)
        return output_path

    list_file = output_path.parent / "concat_list.txt"
    with list_file.open("w") as f:
        for p in paths:
            f.write(f"file '{p.resolve()}'\n")

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(output_path)],
        check=True,
        capture_output=True,
    )
    list_file.unlink(missing_ok=True)
    return output_path
