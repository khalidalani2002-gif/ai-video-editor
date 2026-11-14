r"""Offline regression checks; isolate server functions to avoid touching user work.

Run: app\python\python.exe app\tools\test_codex.py
"""
import ast
import base64
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codex_path as CODEX


def server_functions(*names):
    tree = ast.parse((CODEX.ROOT / "app" / "server.py").read_text(encoding="utf-8"))
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    scope = dict(json=json, os=os, re=re, time=time, CODEX=CODEX,
                 subprocess=subprocess, threading=threading)
    exec(compile(ast.Module(body=selected, type_ignores=[]), "server.py", "exec"), scope)
    return scope


class CodexTests(unittest.TestCase):
    def test_prerelease_version_order(self):
        ordered = ["0.146.0", "0.169.0-alpha.2", "0.169.0-alpha.11.1", "0.169.0", "0.170.0-alpha.1"]
        self.assertEqual(sorted(reversed(ordered), key=CODEX.version_key), ordered)

    def test_newest_native_cli_and_broken_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old, new, broken = [root / n for n in ("old.exe", "codex.exe", "broken.exe")]
            for p in (old, new, broken): p.touch()
            def probe(args, **kw):
                if args[0] == "powershell": return Mock(stdout=str(new))
                if args[0] == str(broken): raise subprocess.TimeoutExpired(args, 15)
                return Mock(returncode=0, stdout="codex-cli " + ("0.146.0" if args[0] == str(old) else "0.169.0-alpha.11.1"))
            with patch.object(CODEX, "run", side_effect=probe), patch.object(CODEX.Path, "home", return_value=root), \
                 patch.object(CODEX.os, "get_exec_path", return_value=[td]), patch.object(CODEX.shutil, "which", return_value=str(broken)):
                result = CODEX.discover({"codex_path": str(old)})
            self.assertEqual(result, {"path": str(new), "version": "0.169.0-alpha.11.1"})

    def test_npm_wrapper_resolves_native_executable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wrapper = root / "codex.cmd"; wrapper.touch()
            native = root / "node_modules/@openai/codex/node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/codex/codex.exe"
            native.parent.mkdir(parents=True); native.touch()
            def probe(args, **kw):
                if args[0] == "powershell": return Mock(stdout="")
                return Mock(returncode=0, stdout="codex-cli 0.170.0")
            with patch.object(CODEX, "run", side_effect=probe), patch.object(CODEX.Path, "home", return_value=root), \
                 patch.object(CODEX.os, "get_exec_path", return_value=[td]), patch.object(CODEX.shutil, "which", return_value=str(wrapper)):
                self.assertEqual(CODEX.discover({})["path"], str(native))

    def test_account_only_exposes_display_fields(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / ".codex").mkdir()
            claims = {"email": "test@example.invalid", "https://api.openai.com/auth": {"chatgpt_plan_type": "plus"}}
            payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
            auth = root / ".codex/auth.json"
            auth.write_text(json.dumps({"tokens": {"id_token": "header." + payload + ".signature", "access_token": "private"}}))
            with patch.object(CODEX.Path, "home", return_value=root):
                self.assertEqual(CODEX.account(), {"method": "ChatGPT", "email": "test@example.invalid", "plan": "plus"})
                auth.write_text('{"OPENAI_API_KEY":"private","auth_mode":"apikey"}')
                self.assertEqual(CODEX.account(), {"method": "API key", "email": None, "plan": None})
                auth.write_text('{"tokens":{"id_token":"bad"}}')
                self.assertIsNone(CODEX.account()["email"])

    def test_cache_expires_after_ten_minutes(self):
        scope = server_functions("engine_info", "codex_bin")
        scope.update(_ENGINE_LOCK=threading.Lock(), _ENGINE_CACHE={"at": None}, SETTINGS={}, claude_bin=lambda: None)
        with patch.object(CODEX, "discover", return_value={"path": "new.exe", "version": "0.169.0"}) as discover, \
             patch.object(CODEX, "status", return_value={"signed_in": True, "email": None, "plan": None, "method": "ChatGPT"}), \
             patch.object(time, "monotonic", side_effect=[0, 0, 599, 600, 600]):
            self.assertEqual(scope["codex_bin"](), "new.exe")
            scope["engine_info"]()
            self.assertEqual(discover.call_count, 1)
            scope["engine_info"]()
            self.assertEqual(discover.call_count, 2)

    def job(self, failures, heavy=False, signed_in=True, cancel=False):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            note = {"id": "test", "engine": "codex", "video": "videos/test.mp4", "level": "heavy" if heavy else "normal"}
            scope = server_functions("run_job", "vkey")
            scope.update(ROOT=root, HERE=root, LOGS=root, FRAMES=root, SESS=root / "sessions.json", SETTINGS={"codex_sandbox": "workspace-write"},
                         CODEX_MODEL="gpt-6.1-sol", CODEX_FALLBACK_MODEL="gpt-5.6-sol", ENGINE_NAME={"claude": "Claude", "codex": "Codex"},
                         get_note=lambda nid: note, update_note=lambda nid, **kw: note.update(kw), codex_bin=lambda: "codex.exe",
                         engine_info=lambda force=False: {"codex_signed_in": signed_in}, prompt_for=lambda n: "same prompt\nArabic: \u0645\u0631\u062d\u0628\u0627",
                         load=lambda *a: {"codex:videos/test.mp4": "existing-thread"}, save=Mock(), RUNNING={}, NOWIN=0,
                         PLATFORM="windows", PY_REL="../app/python/python.exe", platform_block=lambda: "", export_copy=lambda rel: None)
            commands, prompts = [], []
            def launch(cmd, **kw):
                commands.append(list(cmd))
                proc = Mock(returncode=1 if len(commands) <= len(failures) else 0)
                proc.stdin = Mock()
                proc.stdin.write.side_effect = prompts.append
                ev = failures[len(commands) - 1] if len(commands) <= len(failures) else {"type": "item.completed", "item": {"type": "agent_message", "text": "RESULT: none\nCompleted"}}
                proc.stdout = io.StringIO(json.dumps(ev) + "\n")
                if cancel: note["status"] = "cancelled"
                return proc
            with patch.object(subprocess, "Popen", side_effect=launch): scope["run_job"]("test", "edit")
            log = (root / "test.jsonl").read_text() if (root / "test.jsonl").exists() else ""
            return commands, prompts, note, log

    def test_model_fallback_once_and_resume_options(self):
        rejected = {"type": "turn.failed", "error": {"message": "The model gpt-6.1-sol is not supported"}}
        commands, prompts, note, log = self.job([rejected], heavy=True)
        self.assertEqual(len(commands), 2)
        self.assertEqual(prompts[0], prompts[1])
        self.assertIn("retrying once", log)
        self.assertEqual(commands[1][commands[1].index("-m") + 1], "gpt-5.6-sol")
        self.assertLess(commands[1].index("-s"), commands[1].index("resume"))
        self.assertIn("model_reasoning_effort=high", commands[1])
        self.assertEqual(note["status"], "done")
        self.assertEqual(len(self.job([rejected, rejected])[0]), 2)

    def test_other_errors_cancellation_and_signed_out_do_not_retry(self):
        commands, _, note, _ = self.job([{"type": "error", "message": "Network unavailable"}])
        self.assertEqual(len(commands), 1)
        self.assertIn("model_reasoning_effort=medium", commands[0])
        self.assertEqual(note["status"], "failed")
        rejected = {"type": "error", "message": "model not found"}
        self.assertEqual(len(self.job([rejected], cancel=True)[0]), 1)
        commands, _, note, _ = self.job([], signed_in=False)
        self.assertFalse(commands)
        self.assertIn("Codex Login.bat", note["summary"])


if __name__ == "__main__":
    unittest.main()
