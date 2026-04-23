import json
import os
import shutil
import subprocess
import time
from pathlib import Path


AVAILABLE_MODELS = [
    {"id": "claude-opus-4-7", "label": "Opus 4.7", "desc": "Highest quality"},
    {"id": "claude-sonnet-4-6", "label": "Sonnet 4.6", "desc": "Balanced quality/speed"},
    {"id": "claude-haiku-4-5", "label": "Haiku 4.5", "desc": "Fast and economical"},
    {"id": "default", "label": "Default", "desc": "Use CLI default model"},
]


class ClaudeProvider:
    id = "claude"
    display_name = "Claude CLI"

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

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.settings = {"model": "default"}

    def save_settings(self, settings: dict):
        self.settings = settings

    def run(self, prompt: str, timeout: int | None = None):
        return (False, "", "Copilot provider is not implemented yet.")

    def run_text(self, prompt: str, timeout: int = 60):
        return (False, "", "Copilot provider is not implemented yet.")

    def run_tracked(self, prompt: str):
        return (False, "", "Copilot provider is not implemented yet.", [], {})

    def status(self):
        return {"connected": False, "version": "", "error": "Copilot provider is not implemented yet."}

    def diagnose(self):
        return {
            "cli_installed": False,
            "auth_ok": None,
            "quick_test_ok": False,
            "error": "Copilot provider is not implemented yet.",
            "advice": ["Keep using the Claude provider until the Copilot CLI command contract is verified."],
        }


def create_provider(project_root: Path):
    provider = os.environ.get("LLM_WIKI_PROVIDER", "claude").strip().lower()
    if provider == "copilot":
        return CopilotProvider(project_root)
    return ClaudeProvider(project_root)
