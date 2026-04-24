import json
import os
import shutil
import subprocess
import time
from pathlib import Path


CLAUDE_MODELS = [
    {"id": "claude-opus-4-7", "label": "Opus 4.7", "desc": "Highest quality"},
    {"id": "claude-sonnet-4-6", "label": "Sonnet 4.6", "desc": "Balanced quality/speed"},
    {"id": "claude-haiku-4-5", "label": "Haiku 4.5", "desc": "Fast and economical"},
    {"id": "default", "label": "Default", "desc": "Use CLI default model"},
]

COPILOT_MODELS = [
    {"id": "default", "label": "Default / Auto", "desc": "Use COPILOT_MODEL or Copilot CLI default"},
    {"id": "gpt-4.1", "label": "GPT-4.1", "desc": "Fast, broad coding model"},
    {"id": "gpt-5-mini", "label": "GPT-5 mini", "desc": "Low-cost GPT-5 family model"},
    {"id": "gpt-5.2", "label": "GPT-5.2", "desc": "General high-quality model"},
    {"id": "gpt-5.2-codex", "label": "GPT-5.2-Codex", "desc": "Coding-specialized model"},
    {"id": "gpt-5.3-codex", "label": "GPT-5.3-Codex", "desc": "Coding-specialized model"},
    {"id": "gpt-5.4", "label": "GPT-5.4", "desc": "Strongest GPT-5 family model"},
    {"id": "gpt-5.4-mini", "label": "GPT-5.4 mini", "desc": "Efficient GPT-5.4 family model"},
    {"id": "claude-haiku-4.5", "label": "Claude Haiku 4.5", "desc": "Fast Anthropic model"},
    {"id": "claude-sonnet-4", "label": "Claude Sonnet 4", "desc": "Balanced Anthropic model"},
    {"id": "claude-sonnet-4.5", "label": "Claude Sonnet 4.5", "desc": "Copilot CLI documented default"},
    {"id": "claude-sonnet-4.6", "label": "Claude Sonnet 4.6", "desc": "Balanced Anthropic model"},
    {"id": "claude-opus-4.5", "label": "Claude Opus 4.5", "desc": "High-capability Anthropic model"},
    {"id": "claude-opus-4.6", "label": "Claude Opus 4.6", "desc": "High-capability Anthropic model"},
    {"id": "claude-opus-4.7", "label": "Claude Opus 4.7", "desc": "High-capability Anthropic model"},
    {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro", "desc": "Google model"},
    {"id": "gemini-3-flash", "label": "Gemini 3 Flash", "desc": "Fast Google model"},
    {"id": "gemini-3.1-pro", "label": "Gemini 3.1 Pro", "desc": "Google model"},
    {"id": "grok-code-fast-1", "label": "Grok Code Fast 1", "desc": "Fast coding model"},
    {"id": "raptor-mini", "label": "Raptor mini", "desc": "Efficient coding model"},
    {"id": "goldeneye", "label": "Goldeneye", "desc": "Fine-tuned coding model"},
]

AVAILABLE_MODELS = CLAUDE_MODELS


class ClaudeProvider:
    id = "claude"
    display_name = "Claude CLI"
    models = CLAUDE_MODELS

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.settings_file = self.project_root / ".dashboard-settings.json"
        self.tools = os.environ.get("CLAUDE_TOOLS", "Edit,Write,Read,Glob,Grep")
        self.timeout = int(os.environ.get("CLAUDE_TIMEOUT", "600"))
        self.quick_timeout = int(os.environ.get("CLAUDE_QUICK_TIMEOUT", "30"))
        self.settings = self._load_settings()
        self._ensure_cli_on_path()

    def _ensure_cli_on_path(self):
        if shutil.which("claude"):
            return
        for base in [Path.home() / ".nvm/versions/node", Path("/usr/local/bin"), Path("/opt/homebrew/bin")]:
            if not base.is_dir():
                continue
            for root, _, files in os.walk(base):
                if "claude" in files:
                    os.environ["PATH"] = root + ":" + os.environ.get("PATH", "")
                    return

    def _load_settings(self):
        if self.settings_file.exists():
            try:
                return json.loads(self.settings_file.read_text("utf-8"))
            except Exception:
                pass
        return {"model": "default"}

    def save_settings(self, settings: dict):
        self.settings = settings
        self.settings_file.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def model_args(self):
        model = self.settings.get("model", "default")
        if not model or model == "default":
            return []
        return ["--model", model]

    def timeout_hint(self):
        return (
            f"Claude CLI timeout ({self.timeout}s). Possible causes and fixes:\n"
            f"  1. Claude CLI is not authenticated: run 'claude' in a terminal.\n"
            f"  2. Model is too slow: switch to Sonnet or Haiku.\n"
            f"  3. Task is large: restart with CLAUDE_TIMEOUT=1200.\n"
            f"  4. Run /api/claude/diagnose for a quick check."
        )

    def run(self, prompt: str, timeout: int | None = None):
        t = timeout or self.timeout
        try:
            r = subprocess.run(
                ["claude", "-p", "--allowedTools", self.tools]
                + self.model_args()
                + ["--output-format", "text", prompt],
                capture_output=True,
                text=True,
                timeout=t,
                cwd=str(self.project_root),
            )
            err = r.stderr[:500] if r.returncode != 0 else ""
            return (r.returncode == 0, r.stdout[:4000], err)
        except subprocess.TimeoutExpired:
            return (False, "", self.timeout_hint())
        except FileNotFoundError:
            return (False, "", "claude CLI not found in PATH. Install: npm install -g @anthropic-ai/claude-code")

    def run_text(self, prompt: str, timeout: int = 60):
        try:
            r = subprocess.run(
                ["claude", "-p"] + self.model_args() + ["--output-format", "text", prompt],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.project_root),
            )
            return (r.returncode == 0, r.stdout.strip(), r.stderr[:300] if r.returncode != 0 else "")
        except subprocess.TimeoutExpired:
            return (False, "", "timeout")
        except FileNotFoundError:
            return (False, "", "claude CLI not found")

    def run_tracked(self, prompt: str):
        try:
            r = subprocess.run(
                ["claude", "-p", "--allowedTools", self.tools]
                + self.model_args()
                + ["--output-format", "stream-json", "--verbose", prompt],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(self.project_root),
            )
        except subprocess.TimeoutExpired:
            return (False, "", self.timeout_hint(), [], {})
        except FileNotFoundError:
            return (False, "", "claude CLI not found in PATH. Install: npm install -g @anthropic-ai/claude-code", [], {})

        files_read = []
        answer = ""
        token_usage = {}

        for line in r.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                continue

            if evt.get("type") == "user":
                tur = evt.get("tool_use_result")
                if tur and isinstance(tur, dict):
                    fp = tur.get("file", {}).get("filePath", "")
                    if fp:
                        try:
                            rel = str(Path(fp).relative_to(self.project_root))
                        except ValueError:
                            rel = fp
                        if rel not in files_read:
                            files_read.append(rel)

            if evt.get("type") == "result":
                answer = evt.get("result", "")
                token_usage = {
                    "input_tokens": evt.get("usage", {}).get("input_tokens", 0),
                    "output_tokens": evt.get("usage", {}).get("output_tokens", 0),
                    "cost_usd": evt.get("total_cost_usd", 0),
                }

        err = r.stderr[:500] if r.returncode != 0 else ""
        return (r.returncode == 0, answer[:4000], err, files_read, token_usage)

    def status(self):
        ok, version = False, ""
        try:
            r = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                ok = True
                version = r.stdout.strip().split("\n")[0]
        except Exception:
            pass
        return {"connected": ok, "version": version}

    def diagnose(self):
        result = {
            "cli_installed": False,
            "version": "",
            "auth_ok": None,
            "model": self.settings.get("model", "default"),
            "model_args": self.model_args(),
            "quick_test_seconds": None,
            "quick_test_ok": False,
            "quick_test_output": "",
            "error": "",
            "config_timeout": self.timeout,
            "advice": [],
        }

        try:
            r = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                result["cli_installed"] = True
                result["version"] = r.stdout.strip().split("\n")[0]
            else:
                result["error"] = r.stderr[:200] or "claude --version failed"
        except FileNotFoundError:
            result["error"] = "Claude CLI not installed. npm install -g @anthropic-ai/claude-code"
            result["advice"].append("Install Claude CLI: npm install -g @anthropic-ai/claude-code")
            return result
        except subprocess.TimeoutExpired:
            result["error"] = "claude --version timeout"
            return result

        if not result["cli_installed"]:
            return result

        try:
            t0 = time.time()
            ok, out, err = self.run_text("Reply with the single word OK.", timeout=self.quick_timeout)
            elapsed = time.time() - t0
            result["quick_test_seconds"] = round(elapsed, 1)
            result["quick_test_ok"] = ok
            result["quick_test_output"] = (out or err).strip()[:200]
            result["auth_ok"] = ok
            if not ok:
                low = (err or "").lower()
                if "auth" in low or "login" in low or "unauthorized" in low:
                    result["advice"].append("Claude CLI authentication required. Run 'claude' in a terminal.")
                else:
                    result["advice"].append(f"Claude response failed: {(err or '')[:200]}")
            if elapsed > 15:
                result["advice"].append(f"Slow response ({elapsed:.1f}s). Consider Sonnet or Haiku.")
        except subprocess.TimeoutExpired:
            result["auth_ok"] = False
            result["error"] = f"quick diagnostic timeout ({self.quick_timeout}s)"
            result["advice"].append("Claude CLI is not responding. Check auth/network in a terminal.")

        if self.settings.get("model") == "claude-opus-4-7":
            result["advice"].append("Opus 4.7 is slowest. Sonnet 4.6 is recommended for large ingests.")

        return result


class CopilotProvider:
    id = "copilot"
    display_name = "GitHub Copilot CLI"
    models = COPILOT_MODELS

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.settings_file = self.project_root / ".dashboard-settings.json"
        self.settings = {"model": self._load_model()}

    def _load_model(self):
        if os.environ.get("COPILOT_MODEL"):
            return os.environ["COPILOT_MODEL"]
        if self.settings_file.exists():
            try:
                settings = json.loads(self.settings_file.read_text("utf-8"))
                return settings.get("copilot_model", "default")
            except Exception:
                pass
        return "default"

    def save_settings(self, settings: dict):
        self.settings = settings
        existing = {}
        if self.settings_file.exists():
            try:
                existing = json.loads(self.settings_file.read_text("utf-8"))
            except Exception:
                existing = {}
        existing["copilot_model"] = settings.get("model", "default")
        self.settings_file.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def model_args(self):
        model = self.settings.get("model", "default")
        if not model or model == "default":
            return []
        return ["--model", model]

    def command(self, prompt: str):
        return [
            "copilot",
            "-p",
            prompt,
            "--allow-all-tools",
            "--add-dir",
            str(self.project_root),
            "--stream",
            "off",
        ] + self.model_args()

    def run(self, prompt: str, timeout: int | None = None):
        try:
            r = subprocess.run(
                self.command(prompt),
                capture_output=True,
                text=True,
                timeout=timeout or int(os.environ.get("COPILOT_TIMEOUT", "600")),
                cwd=str(self.project_root),
            )
            err = r.stderr[:500] if r.returncode != 0 else ""
            return (r.returncode == 0, r.stdout[:4000], err)
        except subprocess.TimeoutExpired:
            return (False, "", "Copilot CLI timeout. Try COPILOT_TIMEOUT=1200 or a smaller source.")
        except FileNotFoundError:
            return (False, "", "copilot CLI not found in PATH.")

    def run_text(self, prompt: str, timeout: int = 60):
        ok, out, err = self.run(prompt, timeout=timeout)
        return (ok, out.strip(), err)

    def run_tracked(self, prompt: str):
        ok, out, err = self.run(prompt)
        return (ok, out, err, [], {})

    def status(self):
        try:
            r = subprocess.run(["copilot", "--version"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return {"connected": True, "version": r.stdout.strip().split("\n")[0]}
            return {"connected": False, "version": "", "error": r.stderr[:200]}
        except Exception as exc:
            return {"connected": False, "version": "", "error": str(exc)}

    def diagnose(self):
        status = self.status()
        return {
            "cli_installed": status.get("connected", False),
            "version": status.get("version", ""),
            "auth_ok": None,
            "model": self.settings.get("model", "default"),
            "model_args": self.model_args(),
            "quick_test_ok": None,
            "error": status.get("error", ""),
            "advice": [
                "No prompt was executed by diagnose to avoid consuming model quota.",
                "Use LLM_WIKI_PROVIDER=copilot and COPILOT_MODEL=<model> to run real ingests.",
            ],
        }


def create_provider(project_root: Path):
    provider = os.environ.get("LLM_WIKI_PROVIDER", "claude").strip().lower()
    if provider == "copilot":
        return CopilotProvider(project_root)
    return ClaudeProvider(project_root)
