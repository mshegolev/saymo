"""Configuration loader with YAML parsing and env var substitution."""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


def _resolve_env_vars(value: str) -> str:
    """Replace ${VAR_NAME} with environment variable values."""
    def replace(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, "")
    return re.sub(r'\$\{(\w+)\}', replace, value)


def _resolve_dict(d: dict) -> dict:
    """Recursively resolve env vars in a dict."""
    result = {}
    for k, v in d.items():
        if isinstance(v, str):
            result[k] = _resolve_env_vars(v)
        elif isinstance(v, dict):
            result[k] = _resolve_dict(v)
        elif isinstance(v, list):
            result[k] = [_resolve_env_vars(i) if isinstance(i, str) else i for i in v]
        else:
            result[k] = v
    return result


@dataclass
class UserConfig:
    name: str = "User"
    name_variants: list[str] = field(default_factory=list)
    role: str = ""
    team: str = ""
    tech_stack: str = ""
    language: str = "ru"


@dataclass
class AudioConfig:
    capture_device: str = "BlackHole 16ch"
    playback_device: str = "BlackHole 2ch"
    monitor_device: str = ""  # Hear yourself (e.g., Plantronics) when playback goes to BlackHole
    recording_device: str = ""  # Mic for voice sample recording (e.g., MacBook Pro Microphone)
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024


@dataclass
class DeepgramConfig:
    api_key: str = ""
    model: str = "nova-3"
    language: str = "ru"


@dataclass
class WhisperConfig:
    model_size: str = "large-v3"
    device: str = "cpu"
    compute_type: str = "int8"


@dataclass
class STTConfig:
    engine: str = "deepgram"
    deepgram: DeepgramConfig = field(default_factory=DeepgramConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)


@dataclass
class AnthropicLLMConfig:
    api_key: str = ""
    model: str = "claude-sonnet-4-20250514"


@dataclass
class TurnDetectionConfig:
    keyword_trigger: bool = True
    llm_trigger: bool = True
    llm_interval_seconds: int = 5
    confidence_threshold: float = 0.8


@dataclass
class AnalysisConfig:
    llm_provider: str = "anthropic"
    anthropic: AnthropicLLMConfig = field(default_factory=AnthropicLLMConfig)
    turn_detection: TurnDetectionConfig = field(default_factory=TurnDetectionConfig)
    trigger_phrases: list[str] = field(default_factory=list)


@dataclass
class OpenAITTSConfig:
    api_key: str = ""
    model: str = "tts-1"
    voice: str = "onyx"


@dataclass
class ElevenLabsTTSConfig:
    api_key: str = ""
    voice_id: str = ""


@dataclass
class MacOSSayConfig:
    voice: str = "Milena"


@dataclass
class PiperConfig:
    model_path: str = ""


@dataclass
class VoiceTrainingConfig:
    dataset_dir: str = ""  # defaults to ~/.saymo/training_dataset/
    model_dir: str = ""  # defaults to ~/.saymo/models/xtts_finetuned/
    epochs: int = 5
    batch_size: int = 2
    learning_rate: float = 5e-6
    use_finetuned: bool = True  # prefer fine-tuned model for synthesis


@dataclass
class TTSConfig:
    engine: str = "piper"
    piper: PiperConfig = field(default_factory=PiperConfig)
    openai: OpenAITTSConfig = field(default_factory=OpenAITTSConfig)
    elevenlabs: ElevenLabsTTSConfig = field(default_factory=ElevenLabsTTSConfig)
    macos_say: MacOSSayConfig = field(default_factory=MacOSSayConfig)
    voice_training: VoiceTrainingConfig = field(default_factory=VoiceTrainingConfig)


@dataclass
class JiraConfig:
    use_selfhelper_config: bool = False
    selfhelper_path: str = ""
    url: str = ""
    token: str = ""
    project_key: str = ""  # e.g. "ABC" — scopes JQL queries
    user_query: str = "assignee = currentUser() AND updated >= -1d ORDER BY updated DESC"
    worklog_query: str = "worklogAuthor = currentUser() AND worklogDate >= -1d"
    max_results: int = 15
    team_members: dict = field(default_factory=dict)  # {username: display_name}


@dataclass
class ObsidianConfig:
    vault_path: str = ""
    subfolder: str = ""
    date_format: str = "%Y-%m-%d"


@dataclass
class OllamaConfig:
    url: str = "http://localhost:11434"
    model: str = "qwen2.5-coder:7b"


@dataclass
class SpeechConfig:
    style: str = "concise"
    language: str = "ru"
    source: str = "obsidian"  # "obsidian" or "jira"
    composer: str = "ollama"  # "ollama" or "anthropic"


@dataclass
class MeetingProfile:
    description: str = ""
    provider: str = "glip"
    team: bool = False
    source: str = "confluence"
    trigger_phrases: list[str] = field(default_factory=list)


@dataclass
class SafetyConfig:
    require_confirmation: bool = True
    hotkey_speak: str = "<cmd>+<shift>+s"
    hotkey_stop: str = "<cmd>+<shift>+x"
    hotkey_toggle: str = "<cmd>+<shift>+m"
    max_speech_duration: int = 120


@dataclass
class SaymoConfig:
    user: UserConfig = field(default_factory=UserConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    jira: JiraConfig = field(default_factory=JiraConfig)
    obsidian: ObsidianConfig = field(default_factory=ObsidianConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    speech: SpeechConfig = field(default_factory=SpeechConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    meetings: dict = field(default_factory=dict)
    prompts: dict = field(default_factory=dict)
    vocabulary: dict = field(default_factory=dict)

    def get_meeting(self, name: str) -> MeetingProfile | None:
        """Get meeting profile by name."""
        data = self.meetings.get(name)
        if data and isinstance(data, dict):
            return MeetingProfile(**{k: v for k, v in data.items()
                                     if k in MeetingProfile.__dataclass_fields__})
        return None

    def list_meetings(self) -> list[str]:
        """List available meeting profile names."""
        return list(self.meetings.keys()) if isinstance(self.meetings, dict) else []


def _dict_to_dataclass(cls, data: dict):
    """Recursively convert a dict to a nested dataclass instance."""
    if not isinstance(data, dict):
        return data
    field_types = {f.name: f.type for f in cls.__dataclass_fields__.values()}
    kwargs = {}
    for key, value in data.items():
        if key in field_types:
            ft = field_types[key]
            # Resolve string type annotations
            if isinstance(ft, str):
                ft = eval(ft, {}, {
                    k: v for k, v in globals().items()
                    if isinstance(v, type)
                })
            if isinstance(value, dict) and hasattr(ft, '__dataclass_fields__'):
                kwargs[key] = _dict_to_dataclass(ft, value)
            else:
                kwargs[key] = value
    return cls(**kwargs)


def load_config(config_path: Optional[str] = None) -> SaymoConfig:
    """Load config from YAML file, resolve env vars, return SaymoConfig."""
    if config_path is None:
        # Look in current dir, then project root
        candidates = [
            Path.cwd() / "config.yaml",
            Path(__file__).parent.parent / "config.yaml",
        ]
        for c in candidates:
            if c.exists():
                config_path = str(c)
                break

    if config_path and Path(config_path).exists():
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}
        resolved = _resolve_dict(raw)
        return _dict_to_dataclass(SaymoConfig, resolved)

    return SaymoConfig()
