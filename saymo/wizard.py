"""Interactive setup wizard for Saymo."""

import os
os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1")

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def _record_voice_interactive(recording_device: str, ollama_url: str = "http://localhost:11434", ollama_model: str = "qwen2.5-coder:7b"):
    """Record a 5-minute voice sample with on-screen reading text."""
    import time
    import threading
    from saymo.audio.devices import find_device
    DURATION = 300  # 5 minutes
    SAMPLE_RATE = 22050

    # Resolve mic
    mic = find_device(recording_device, kind="input") if recording_device else None
    if not mic:
        try:
            import sounddevice as sd
            default_dev = sd.query_devices(kind="input")
            if default_dev:
                recording_device = default_dev["name"]  # type: ignore[index]
                mic = find_device(recording_device, kind="input")
        except Exception:
            pass
    if not mic:
        console.print("[bold red]  Микрофон не найден! Пропускаю запись.[/]")
        return

    # Generate reading text via Ollama (or use static fallback)
    from saymo.reading_text import generate_paragraphs
    with console.status("[bold blue]Генерирую текст для чтения через Ollama...", spinner="dots"):
        paragraphs = generate_paragraphs(ollama_url=ollama_url, model=ollama_model)

    console.print(f"  [green]Готово — {len(paragraphs)} абзацев[/]\n")

    console.print(f"  [bold]Микрофон:[/] {recording_device}")
    console.print(f"  [bold]Длительность:[/] 5 минут")
    console.print()
    console.print(Panel(
        "[bold]Советы:[/]\n"
        "  \u2022 Говори в обычном темпе — не торопись, но и не тяни\n"
        "  \u2022 Держи микрофон на расстоянии ~20 см\n"
        "  \u2022 Читай текст естественно, как будто рассказываешь коллеге\n"
        "  \u2022 Паузы между абзацами — это нормально, новый текст появится автоматически",
        border_style="blue",
    ))
    console.print()

    if not click.confirm("  Начинаем запись?", default=True):
        console.print("  [yellow]Запись пропущена.[/]")
        return

    console.print("\n  [bold yellow]Запись начнётся через 3 секунды...[/]")
    for i in range(3, 0, -1):
        console.print(f"    {i}...")
        time.sleep(1)

    # Start recording in background thread
    import sounddevice as sd

    audio_data = []
    recording_done = threading.Event()

    def _record():
        try:
            data = sd.rec(
                int(DURATION * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                device=mic.index,
            )
            sd.wait()
            audio_data.append(data)
        finally:
            recording_done.set()

    rec_thread = threading.Thread(target=_record, daemon=True)
    rec_thread.start()
    import datetime
    console.print(f"  [bold green]● ЗАПИСЬ НАЧАТА[/] {datetime.datetime.now().strftime('%H:%M:%S')}\n")

    # Display paragraphs one by one with timing
    seconds_per_para = DURATION / len(paragraphs)
    for i, para in enumerate(paragraphs):
        remaining = DURATION - int(i * seconds_per_para)
        mins, secs = divmod(remaining, 60)
        console.print(f"  [dim]\u2014 {i + 1}/{len(paragraphs)}  (осталось {mins}:{secs:02d}) \u2014[/]\n")
        console.print(Panel(para, border_style="green", padding=(1, 2)))
        console.print()

        if i < len(paragraphs) - 1:
            deadline = time.monotonic() + seconds_per_para
            while time.monotonic() < deadline:
                left = deadline - time.monotonic()
                mins_left, secs_left = divmod(int(left), 60)
                print(f"\r  ● REC  |  следующий абзац через {mins_left}:{secs_left:02d}    ", end="", flush=True)
                time.sleep(1)
            print("\r" + " " * 60 + "\r", end="", flush=True)

    # Wait for recording to finish
    console.print(f"  [bold yellow]■ ЗАПИСЬ ОСТАНОВЛЕНА[/] {datetime.datetime.now().strftime('%H:%M:%S')}")
    console.print("  [dim]Сохраняю файл...[/]")
    recording_done.wait(timeout=60)

    if not audio_data:
        console.print("  [bold red]Ошибка записи![/]")
        return

    # Save WAV
    import wave
    voice_dir = Path.home() / ".saymo" / "voice_samples"
    voice_dir.mkdir(parents=True, exist_ok=True)
    out_path = voice_dir / "voice_sample.wav"

    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_data[0].tobytes())

    size_mb = out_path.stat().st_size / (1024 * 1024)
    console.print(f"\n  [bold green]Сэмпл сохранён:[/] {out_path} ({size_mb:.1f} MB)")


def run_wizard(config_path: str | None = None):
    """Interactive wizard for first-time setup and meeting configuration."""

    console.print(Panel("[bold]Saymo Setup Wizard[/]", border_style="blue"))
    console.print()

    if config_path is None:
        config_path = str(Path(__file__).parent.parent / "config.yaml")

    import yaml

    if Path(config_path).exists():
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
        console.print(f"[green]Found existing config: {config_path}[/]\n")
    else:
        config = {}

    # Step 1: User info
    console.print("[bold cyan]Step 1: Your info[/]")
    name = click.prompt("  Your name (как тебя зовут)", default=config.get("user", {}).get("name", ""))
    if not name:
        console.print("[red]Name is required[/]")
        return

    variants = click.prompt(
        "  Name variants (comma-separated, как тебя могут звать)",
        default=", ".join(config.get("user", {}).get("name_variants", [name]))
    )
    name_variants = [v.strip() for v in variants.split(",") if v.strip()]

    lang = click.prompt("  Language (ru/en)", default=config.get("user", {}).get("language", "ru"))

    config.setdefault("user", {})
    config["user"]["name"] = name
    config["user"]["name_variants"] = name_variants
    config["user"]["language"] = lang

    # Step 2: Audio devices
    console.print("\n[bold cyan]Step 2: Audio devices[/]")
    devices = []
    try:
        from saymo.audio.devices import list_devices
        devices = list_devices()
        table = Table(title="Available Devices")
        table.add_column("#")
        table.add_column("Name")
        table.add_column("In/Out")
        for d in devices:
            io_type = []
            if d.max_input_channels > 0:
                io_type.append("IN")
            if d.max_output_channels > 0:
                io_type.append("OUT")
            table.add_row(str(d.index), d.name, "/".join(io_type))
        console.print(table)
    except Exception:
        console.print("[yellow]Could not list audio devices[/]")

    # Show input devices separately for mic selection
    input_devices = [d for d in devices if d.max_input_channels > 0]
    if input_devices:
        console.print("\n  [bold]Input devices (microphones):[/]")
        for i, d in enumerate(input_devices, 1):
            console.print(f"    {i}. {d.name}")

    current_mic = config.get("audio", {}).get("recording_device", "")
    if input_devices:
        default_idx = "1"
        for i, d in enumerate(input_devices, 1):
            if current_mic and current_mic.lower() in d.name.lower():
                default_idx = str(i)
                break
        mic_choice = click.prompt(
            "  Recording mic (number or device name)",
            default=default_idx,
        )
        if mic_choice.isdigit() and 1 <= int(mic_choice) <= len(input_devices):
            recording_device = input_devices[int(mic_choice) - 1].name
        else:
            recording_device = mic_choice
    else:
        recording_device = click.prompt(
            "  Recording mic (device name)",
            default=current_mic or "MacBook Pro Microphone",
        )

    playback = click.prompt(
        "  Playback device (headphones)",
        default=config.get("audio", {}).get("playback_device", "Plantronics Blackwire 3220 Series")
    )
    monitor = click.prompt(
        "  Monitor device (hear yourself)",
        default=config.get("audio", {}).get("monitor_device", playback)
    )

    config.setdefault("audio", {})
    config["audio"]["recording_device"] = recording_device
    config["audio"]["playback_device"] = playback
    config["audio"]["monitor_device"] = monitor
    config["audio"]["capture_device"] = config["audio"].get("capture_device", "BlackHole 16ch")

    # Step 3: Voice sample
    console.print("\n[bold cyan]Шаг 3: Голосовой сэмпл[/]")
    voice_path = Path.home() / ".saymo" / "voice_samples" / "voice_sample.wav"
    if voice_path.exists():
        size_mb = voice_path.stat().st_size / (1024 * 1024)
        console.print(f"  [green]Сэмпл найден: {voice_path} ({size_mb:.1f} MB)[/]")
        do_record = click.confirm("  Перезаписать?", default=False)
    else:
        console.print("  [yellow]Сэмпл не найден. Для клонирования голоса нужна 5-минутная запись.[/]")
        do_record = click.confirm("  Записать сейчас?", default=True)

    if do_record:
        ollama_cfg = config.get("ollama", {})
        _record_voice_interactive(
            recording_device,
            ollama_url=ollama_cfg.get("url", "http://localhost:11434"),
            ollama_model=ollama_cfg.get("model", "qwen2.5-coder:7b"),
        )

    # Step 4: Meeting profiles
    console.print("\n[bold cyan]Step 4: Meeting profiles[/]")

    meetings = config.get("meetings", {})
    if meetings:
        table = Table(title="Current Meetings")
        table.add_column("Name")
        table.add_column("Team")
        table.add_column("Triggers")
        for mname, mdata in meetings.items():
            if isinstance(mdata, dict):
                triggers = ", ".join(mdata.get("trigger_phrases", [])[:3])
                table.add_row(mname, str(mdata.get("team", False)), triggers + "...")
        console.print(table)

    if click.confirm("  Add/edit a meeting profile?", default=True):
        while True:
            console.print()
            mname = click.prompt("  Meeting name (e.g., standup, scrum, weekly)", default="")
            if not mname:
                break

            existing = meetings.get(mname, {})
            desc = click.prompt("  Description", default=existing.get("description", ""))
            is_team = click.confirm("  Team report? (includes all members)", default=existing.get("team", False))
            source = click.prompt("  Task source (confluence/obsidian/jira)", default=existing.get("source", "confluence"))

            triggers_str = click.prompt(
                "  Trigger phrases (comma-separated)",
                default=", ".join(existing.get("trigger_phrases", name_variants))
            )
            triggers = [t.strip() for t in triggers_str.split(",") if t.strip()]

            meetings[mname] = {
                "description": desc,
                "team": is_team,
                "source": source,
                "trigger_phrases": triggers,
                "glip_url_pattern": "v.ringcentral.com/conf",
            }

            console.print(f"  [green]Meeting '{mname}' configured[/]")

            if not click.confirm("  Add another meeting?", default=False):
                break

    config["meetings"] = meetings

    # Step 5: Ollama
    console.print("\n[bold cyan]Шаг 5: Ollama (локальная LLM)[/]")
    ollama_cfg = config.get("ollama", {})
    ollama_url = ollama_cfg.get("url", "http://localhost:11434")

    # Check if Ollama is running
    import httpx
    ollama_running = False
    models = []
    try:
        resp = httpx.get(ollama_url, timeout=5.0, proxy=None)
        ollama_running = resp.status_code == 200
    except Exception:
        pass

    if not ollama_running:
        console.print("  [yellow]Ollama не запущена. Пробую запустить...[/]")
        import subprocess, time
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(10):
            time.sleep(1)
            try:
                resp = httpx.get(ollama_url, timeout=3.0, proxy=None)
                if resp.status_code == 200:
                    ollama_running = True
                    console.print("  [green]Ollama запущена[/]")
                    break
            except Exception:
                pass
        if not ollama_running:
            console.print("  [bold red]Не удалось запустить Ollama![/]")
            console.print("  Установи: https://ollama.ai  и запусти: ollama serve")

    if ollama_running:
        # List available models
        try:
            resp = httpx.get(f"{ollama_url}/api/tags", timeout=10.0, proxy=None)
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            pass

    current_model = ollama_cfg.get("model", "qwen2.5-coder:7b")

    if models:
        console.print("\n  [bold]Установленные модели:[/]")
        for i, m in enumerate(models, 1):
            marker = " [bold green]← текущая[/]" if m == current_model else ""
            console.print(f"    {i}. {m}{marker}")

        default_idx = "1"
        for i, m in enumerate(models, 1):
            if m == current_model:
                default_idx = str(i)
                break

        model_choice = click.prompt(
            "  Выбери модель (номер)",
            default=default_idx,
        )
        if model_choice.isdigit() and 1 <= int(model_choice) <= len(models):
            current_model = models[int(model_choice) - 1]
        else:
            current_model = model_choice

    elif ollama_running:
        console.print("  [yellow]Нет установленных моделей[/]")
        suggested = "qwen2.5-coder:7b"
        if click.confirm(f"  Установить {suggested}?", default=True):
            console.print(f"  [blue]Скачиваю {suggested}...[/]")
            import subprocess
            result = subprocess.run(["ollama", "pull", suggested], capture_output=False)
            if result.returncode == 0:
                current_model = suggested
                console.print(f"  [green]Модель {suggested} установлена[/]")
            else:
                console.print(f"  [red]Ошибка установки[/]")

    config.setdefault("ollama", {})
    config["ollama"]["url"] = ollama_url
    config["ollama"]["model"] = current_model

    # Step 6: TTS engine
    console.print("\n[bold cyan]Шаг 6: TTS движок[/]")

    import subprocess as sp
    tts_venv = Path(__file__).parent.parent / ".venv-tts"
    tts_python = tts_venv / "bin" / "python3"

    # Check Coqui availability via worker
    coqui_available = False
    if tts_python.exists():
        try:
            import importlib.util
            coqui_available = importlib.util.find_spec("TTS") is not None
        except Exception:
            pass

    engines = [
        ("coqui_clone", "coqui_clone (клонирование голоса, XTTS v2)", coqui_available),
        ("macos_say", "macos_say (встроенный macOS, без установки)", True),
    ]
    current = config.get("tts", {}).get("engine", "coqui_clone")

    for i, (key, label, avail) in enumerate(engines):
        status = "[green]готов[/]" if avail else "[yellow]не установлен[/]"
        marker = " [bold green]← текущий[/]" if key == current else ""
        console.print(f"  {i+1}. {label}  ({status}){marker}")

    default_idx = next((str(i+1) for i, (k, _, _) in enumerate(engines) if k == current), "1")
    choice = click.prompt(f"  Выбери движок (1-{len(engines)})", default=default_idx)
    try:
        selected_engine = engines[int(choice) - 1][0]
    except (ValueError, IndexError):
        selected_engine = current

    # Install coqui_clone if needed
    if selected_engine == "coqui_clone" and not coqui_available:
        console.print("\n  [yellow]Coqui TTS требует отдельный Python 3.11 venv (.venv-tts)[/]")
        if click.confirm("  Создать venv и установить TTS? (скачает ~2 GB)", default=True):
            # Create venv if missing
            if not tts_python.exists():
                console.print("  [blue]Создаю .venv-tts (Python 3.11)...[/]")
                result = sp.run(["python3.11", "-m", "venv", str(tts_venv)], capture_output=True, text=True)
                if result.returncode != 0:
                    console.print(f"  [red]Ошибка: python3.11 не найден. Установи: brew install python@3.11[/]")
                    selected_engine = "macos_say"

            if selected_engine == "coqui_clone":
                console.print("  [blue]Устанавливаю TTS (может занять несколько минут)...[/]")
                result = sp.run(
                    [str(tts_python), "-m", "pip", "install", "TTS"],
                    capture_output=False,
                    timeout=600,
                )
                if result.returncode == 0:
                    console.print("  [green]Coqui TTS установлен![/]")
                else:
                    console.print("  [red]Ошибка установки TTS[/]")
                    console.print("  [yellow]Переключаю на macos_say[/]")
                    selected_engine = "macos_say"
        else:
            console.print("  [yellow]Переключаю на macos_say[/]")
            selected_engine = "macos_say"

    config.setdefault("tts", {})
    config["tts"]["engine"] = selected_engine

    # Save
    console.print(f"\n[bold cyan]Saving to {config_path}...[/]")
    with open(config_path, "w") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    console.print("[bold green]Configuration saved![/]\n")

    # Summary
    console.print(Panel(
        f"[bold]Name:[/] {config['user']['name']}\n"
        f"[bold]Meetings:[/] {', '.join(config.get('meetings', {}).keys())}\n"
        f"[bold]TTS:[/] {config['tts']['engine']}\n"
        f"[bold]Recording mic:[/] {config['audio'].get('recording_device', 'not set')}\n"
        f"[bold]Playback:[/] {config['audio']['playback_device']}",
        title="Configuration Summary",
        border_style="green",
    ))
