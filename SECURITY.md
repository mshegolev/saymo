# Security Policy

## Supported versions

Saymo is a single-track project; the latest release on `main` is the only supported version. Older versions do not receive security backports.

| Version | Supported |
|---------|-----------|
| `main` (latest tagged release) | ✅ |
| Any previous tag | ❌ — please upgrade |

## Reporting a vulnerability

**Do not open a public GitHub issue for security reports.** That includes anything you suspect is exploitable, leaks credentials, bypasses authentication, allows unauthorized audio capture, or otherwise puts users at risk.

Instead:

1. Email the maintainer at **mshegolev@gmail.com**, subject prefix `[security]`.
2. Include:
   - A clear description of the issue and its impact
   - Steps to reproduce (PoC if possible)
   - Affected version / commit
   - Whether you've shared this with anyone else

You can expect:
- An acknowledgement within 5 business days
- A fix or mitigation timeline within 14 days for confirmed issues
- Credit in the release notes once a fix ships, unless you prefer to remain anonymous

## Scope

In scope:

- The Saymo Python package and its install scripts
- Audio routing (BlackHole, virtual mic) integration
- Bundled Chrome JS for call-app automation under `saymo/providers/`
- Configuration handling, secret resolution, plugin loaders

Out of scope (please report upstream):

- Bugs in third-party deps (Coqui TTS, faster-whisper, Ollama, MLX, Applio, RVC, etc.)
- Issues in BlackHole, Chrome, or macOS itself
- LLM model weight behavior

## Threat model

Saymo is a **local-first** tool — it intentionally avoids sending data off-device. Threats we care about:

- A malicious config or plugin running arbitrary code on the user's machine
- Audio capture from non-consented sources (other apps' calls, system audio)
- Cloned voice samples being exfiltrated by code paths the user didn't enable
- Secrets (API keys for optional cloud providers, JIRA tokens, etc.) being logged or written to files outside the user's home

Threats we accept:

- Local users with shell access can read configs and voice samples — file-system permissions are the right boundary, not Saymo
- Cloud TTS/STT providers (when explicitly enabled by the user) see the data the user sends them; that's their privacy policy, not ours

## Hardening tips for users

- Keep `~/.saymo/config.yaml` and `~/.saymo/voice_samples/` in your home directory only — both are listed in `.gitignore`
- Use `${ENV_VAR}` interpolation for secrets in config rather than inlining them
- Review any third-party plugin (`saymo/plugins/`) before enabling
- Run `saymo` as your normal user, not as root
