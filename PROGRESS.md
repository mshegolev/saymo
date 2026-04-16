# Saymo — Progress & Next Steps

## What works NOW

```bash
# Full local pipeline (Obsidian → Ollama → Piper/macOS say → headphones)
python3 -m saymo speak

# Test individual components
python3 -m saymo test-notes      # Read Obsidian daily notes
python3 -m saymo test-compose    # Generate standup text via Ollama
python3 -m saymo test-tts "текст" # Test TTS
python3 -m saymo test-devices    # List audio devices
python3 -m saymo test-ollama     # Check Ollama status
python3 -m saymo test-jira       # Test JIRA connection (needs network)
python3 -m saymo record-voice    # Record voice sample for future cloning
```

## What was done

- Phase 1 MVP: Obsidian + Ollama + macOS say/Piper — fully local, no API keys
- JIRA integration (fallback via `--source jira`)
- Piper TTS with Russian voice (dmitri) installed at ~/.saymo/piper_models/
- Voice recorder for Plantronics mic
- All committed to git

## NEXT: Voice Clone after arm64 terminal restart

### Problem
PyTorch 2.2.2 runs under Rosetta (x86_64), but Coqui TTS / Bark need PyTorch 2.6+
which requires native arm64 Python.

### Steps after switching to arm64 terminal:

1. **Reinstall Python deps for arm64:**
   ```bash
   # In arm64 terminal:
   pip3 install -e /opt/develop/saymo
   pip3 install torch torchaudio  # Will get arm64 native with MPS support
   pip3 install TTS               # Coqui TTS should now install for Python <3.12
   # OR if Python 3.12:
   pip3 install coqui-tts          # Fork that supports 3.12
   ```

2. **Record voice sample:**
   ```bash
   python3 -m saymo record-voice --duration 60
   # Speak naturally in Russian for 60 seconds
   # Saved to ~/.saymo/voice_samples/voice_sample.wav
   ```

3. **Implement coqui_clone.py:**
   - File: `saymo/tts/coqui_clone.py`
   - Uses XTTS v2 with voice_sample.wav as reference
   - 6-second minimum, 30-60s recommended

4. **Update config.yaml:**
   ```yaml
   tts:
     engine: "coqui_clone"
   ```

## Installed dependencies

### Under x86_64 (Rosetta):
- sounddevice, soundfile, numpy
- anthropic, openai, jira
- click, rich, pynput, pyyaml
- httpx, aiohttp
- piper-tts + ru_RU-dmitri-medium model
- torch 2.2.2 (x86_64), transformers 4.x
- scipy, onnxruntime

### May need reinstall under arm64:
- torch (will get native arm64 + MPS)
- All compiled packages (numpy, scipy, etc.)
- TTS / coqui-tts

## Config
- Obsidian vault: `/Users/m.v.shchegolev/Documents/Obsidian Vault`
- Ollama model: `qwen2.5-coder:7b` (4.4 GB, already installed)
- Piper model: `~/.saymo/piper_models/ru_RU-dmitri-medium.onnx`
- Audio output: `Plantronics Blackwire 3220 Series`
