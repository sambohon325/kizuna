from pathlib import Path

from app.audio import generate_timing_slate


class VoiceProviderError(RuntimeError):
    pass


def generate_voice(provider: str, destination: Path, text: str, instructions: str, *, api_key: str = "", model: str = "gpt-4o-mini-tts", voice: str = "coral", duration: float = 2, pitch: float = 0, pace: float = 1) -> tuple[str, str]:
    if provider == "simulation":
        destination = destination.with_suffix(".wav")
        generate_timing_slate(destination, text, duration, pitch, pace)
        return destination.name, "audio/wav"
    if provider != "openai":
        raise VoiceProviderError(f"Unknown voice provider: {provider}")
    if not api_key:
        raise VoiceProviderError("Add KIZUNA_OPENAI_API_KEY to enable OpenAI speech generation")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise VoiceProviderError("Install the OpenAI SDK to enable speech generation") from exc
    destination = destination.with_suffix(".mp3")
    client = OpenAI(api_key=api_key)
    try:
        with client.audio.speech.with_streaming_response.create(model=model, voice=voice, input=text, instructions=instructions) as response:
            response.stream_to_file(destination)
    except Exception as exc:
        raise VoiceProviderError(str(exc)) from exc
    return destination.name, "audio/mpeg"
