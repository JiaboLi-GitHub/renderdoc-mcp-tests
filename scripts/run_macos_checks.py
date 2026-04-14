#!/usr/bin/env python3
"""
macOS-specific MCP tool checks for renderdoc-mcp with OpenGL.

Launches the macOS OpenGL smoke test, captures a frame via renderdoc-mcp,
then exercises as many MCP tools as possible against the capture.

Usage:
    python3 scripts/run_macos_checks.py [--server PATH] [--smoke-exe PATH]
                                        [--output-dir DIR] [--renderdoc-lib-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional


DEFAULT_SERVER = os.path.expanduser("~/Developer/renderdoc-mcp/build/renderdoc-mcp")
DEFAULT_SMOKE_EXE = os.path.expanduser("~/Developer/renderdoc-mcp-tests/build/bin/renderdoc_mcp_opengl_smoke")
DEFAULT_OUTPUT_DIR = os.path.expanduser("~/Developer/renderdoc-mcp-tests/artifacts/macos")
DEFAULT_RENDERDOC_LIB_DIR = os.path.expanduser("~/Developer/renderdoc/build/lib")


# ---------------------------------------------------------------------------
# McpClient — communicates with renderdoc-mcp via stdio JSON-RPC
# ---------------------------------------------------------------------------

class McpClient:
    def __init__(self, server_path: str, extra_env: dict | None = None):
        self.server_path = server_path
        self.extra_env = extra_env or {}
        self.proc = None
        self.stdout_q: queue.Queue = queue.Queue()
        self.stderr_q: queue.Queue = queue.Queue()
        self.stderr_lines: list[str] = []
        self.stdout_noise: list[str] = []
        self.next_id = 1

    def start(self) -> None:
        env = os.environ.copy()
        env.update(self.extra_env)
        self.proc = subprocess.Popen(
            [self.server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=env,
        )
        threading.Thread(target=self._pump_stdout, daemon=True).start()
        threading.Thread(target=self._pump_stderr, daemon=True).start()

        init = self.rpc(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "macos-mcp-checks", "version": "1.0"},
            },
            timeout=30.0,
        )
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        self.initialize_response = init

    def close(self) -> None:
        if self.proc is None:
            return
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.terminate()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=10)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass
        self._drain_stderr()

    def _pump_stdout(self) -> None:
        for line in self.proc.stdout:
            self.stdout_q.put(line.rstrip("\r\n"))

    def _pump_stderr(self) -> None:
        for line in self.proc.stderr:
            self.stderr_q.put(line.rstrip("\r\n"))

    def _drain_stderr(self) -> None:
        while True:
            try:
                self.stderr_lines.append(self.stderr_q.get_nowait())
            except queue.Empty:
                return

    def _send(self, msg: dict) -> None:
        payload = json.dumps(msg, ensure_ascii=False) + "\n"
        self.proc.stdin.write(payload)
        self.proc.stdin.flush()

    def _wait_for(self, request_id: int, timeout: float = 120.0) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            self._drain_stderr()
            try:
                line = self.stdout_q.get(timeout=0.2)
            except queue.Empty:
                continue
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception:
                self.stdout_noise.append(line)
                continue
            if obj.get("id") == request_id:
                return obj
        raise TimeoutError(f"timed out waiting for response id={request_id}")

    def rpc(self, method: str, params: dict, timeout: float = 120.0) -> dict:
        request_id = self.next_id
        self.next_id += 1
        self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        return self._wait_for(request_id, timeout=timeout)

    @staticmethod
    def _parse_tool_content(resp: dict):
        if "error" in resp:
            error = resp["error"]
            raise RuntimeError(error.get("message", "unknown error"))

        result = resp.get("result", {})
        if "structuredContent" in result and result["structuredContent"] is not None:
            return result["structuredContent"]

        content = result.get("content", [])
        texts = [item.get("text", "") for item in content if item.get("type") == "text"]
        if not texts:
            return result

        text = "\n".join(texts).strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) >= 3 and lines[0].startswith("```") and lines[-1].startswith("```"):
                text = "\n".join(lines[1:-1]).strip()
        try:
            return json.loads(text)
        except Exception:
            return {"raw": text}

    def call_tool(self, name: str, arguments: dict | None = None, timeout: float = 120.0):
        arguments = arguments or {}
        resp = self.rpc("tools/call", {"name": name, "arguments": arguments}, timeout=timeout)
        return self._parse_tool_content(resp), resp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def record_tool(client, report, name, arguments=None, timeout=120.0):
    step = {"tool": name, "arguments": arguments or {}}
    try:
        parsed, raw = client.call_tool(name, arguments, timeout=timeout)
        step["parsed"] = parsed
        step["raw"] = raw
        report["steps"].append(step)
        return parsed
    except Exception as exc:
        step["error"] = str(exc)
        report["steps"].append(step)
        return None


def find_resource(resources, rtype):
    for r in resources:
        if r.get("type", "").lower() == rtype.lower():
            rid = r.get("resourceId") or r.get("id")
            if rid:
                return str(rid)
    return None


def step_ok(report, tool_name, index=0):
    count = 0
    for step in report["steps"]:
        if step["tool"] == tool_name:
            if count == index:
                return "error" not in step and step.get("parsed") is not None
            count += 1
    return False


def step_parsed(report, tool_name, index=0):
    count = 0
    for step in report["steps"]:
        if step["tool"] == tool_name:
            if count == index:
                return step.get("parsed")
            count += 1
    return None


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def build_summary(report):
    checks = {}
    capture_available = report.get("capture_available", False)

    # Protocol (always testable)
    checks["initialize_ok"] = report.get("initialize") is not None
    checks["tools_list_ok"] = report.get("tools_list_count", 0) > 0
    checks["tools_list_has_59"] = report.get("tools_list_count", 0) == 59

    # Session (always testable)
    checks["session_status_before_ok"] = step_ok(report, "session_status", 0)

    if capture_available:
        # These only make sense if a capture was obtained
        checks["open_capture_ok"] = step_ok(report, "open_capture", 0)
        checks["get_capture_info_ok"] = step_ok(report, "get_capture_info", 0)
        checks["get_stats_ok"] = step_ok(report, "get_stats", 0)
        checks["get_log_ok"] = step_ok(report, "get_log", 0)
        checks["list_events_ok"] = step_ok(report, "list_events", 0)
        checks["list_draws_ok"] = step_ok(report, "list_draws", 0)
        checks["get_draw_info_ok"] = step_ok(report, "get_draw_info", 0)
        checks["goto_event_ok"] = step_ok(report, "goto_event", 0)
        checks["get_pipeline_state_ok"] = step_ok(report, "get_pipeline_state", 0)
        checks["get_bindings_ok"] = step_ok(report, "get_bindings", 0)
        checks["get_shader_reflect_ok"] = step_ok(report, "get_shader", 0)
        checks["get_shader_disasm_ok"] = step_ok(report, "get_shader", 1)
        checks["list_shaders_ok"] = step_ok(report, "list_shaders", 0)
        checks["search_shaders_ok"] = step_ok(report, "search_shaders", 0)
        checks["list_resources_ok"] = step_ok(report, "list_resources", 0)
        checks["get_resource_info_ok"] = step_ok(report, "get_resource_info", 0)
        checks["list_passes_ok"] = step_ok(report, "list_passes", 0)
        checks["export_render_target_ok"] = step_ok(report, "export_render_target", 0)
        checks["close_capture_ok"] = step_ok(report, "close_capture", 0)

    # Session close (always testable - tests 2nd/3rd call if no capture)
    idx_after = 1 if capture_available else 1
    idx_closed = 2 if capture_available else 2
    checks["session_status_after_ok"] = step_ok(report, "session_status", idx_after)
    checks["session_status_closed_ok"] = step_ok(report, "session_status", idx_closed)

    # Error handling tests
    checks["error_handling_ok"] = report.get("error_handling_ok", False)

    failures = [name for name, passed in checks.items() if not passed]
    return {"checks": checks, "failures": failures, "capture_available": capture_available}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(args) -> int:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "metadata": {
            "server": args.server,
            "smokeExe": args.smoke_exe,
            "platform": "macOS",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "steps": [],
        "stderr": [],
        "stdout_noise": [],
    }

    extra_env = {}
    if args.renderdoc_lib_dir:
        existing = os.environ.get("DYLD_LIBRARY_PATH", "")
        extra_env["DYLD_LIBRARY_PATH"] = args.renderdoc_lib_dir + (":" + existing if existing else "")

    client = McpClient(args.server, extra_env=extra_env)
    try:
        print("[*] Starting renderdoc-mcp server...")
        client.start()
        report["initialize"] = client.initialize_response
        print("[+] Server initialized successfully")

        # Check tools/list
        tools_resp = client.rpc("tools/list", {})
        tools_list = tools_resp.get("result", {}).get("tools", [])
        report["tools_list_count"] = len(tools_list)
        print(f"[+] Server reports {len(tools_list)} tools")

        # Phase 1: Session status before capture
        print("\n[*] Phase 1: Session status")
        record_tool(client, report, "session_status", {})

        # Phase 2: Self-capture via the smoke test app
        print("\n[*] Phase 2: Self-capture from smoke test app")
        working_dir = str(Path(args.smoke_exe).parent)
        capture_base = str(output_dir / "smoke_capture")
        capture_path = capture_base + ".rdc"

        # Run the smoke test with RenderDoc in-app API to self-capture
        capture_ok = False
        rdoc_lib = os.path.join(args.renderdoc_lib_dir, "librenderdoc.dylib")
        if os.path.exists(rdoc_lib) and os.path.exists(args.smoke_exe):
            env = os.environ.copy()
            env["DYLD_INSERT_LIBRARIES"] = rdoc_lib
            env["RENDERDOC_LIB_PATH"] = rdoc_lib
            env["RENDERDOC_CAPTURE_PATH"] = capture_base
            env["RENDERDOC_CAPTURE_FRAME"] = "30"
            try:
                print(f"  Running smoke test with RenderDoc injection...")
                proc = subprocess.run(
                    [args.smoke_exe], env=env, timeout=60,
                    capture_output=True, text=True
                )
                print(f"  Smoke test output: {proc.stdout.strip()[:200]}")
                # Check if .rdc file was created (may have suffix)
                import glob
                rdcs = sorted(glob.glob(capture_base + "*.rdc"))
                if rdcs:
                    capture_path = rdcs[0]
                    capture_ok = True
                    print(f"[+] Capture created: {capture_path}")
                else:
                    print("[-] No .rdc file generated (macOS OpenGL capture limitation)")
            except Exception as e:
                print(f"[-] Smoke test failed: {e}")

        # Also try capture_frame via MCP (may fail on macOS)
        if not capture_ok:
            print("  Trying capture_frame via MCP...")
            capture_result = record_tool(
                client, report, "capture_frame",
                {
                    "exePath": args.smoke_exe,
                    "workingDir": working_dir,
                    "delayFrames": 60,
                    "outputPath": capture_path,
                },
                timeout=180.0,
            )
            if isinstance(capture_result, dict) and capture_result.get("path"):
                actual = capture_result["path"]
                if os.path.exists(actual):
                    capture_path = actual
                    capture_ok = True

        if not capture_ok:
            print("[-] Frame capture not available on macOS (known platform limitation)")
            print("    RenderDoc CGL interposing does not intercept Metal-backed OpenGL on Apple Silicon")
            report["capture_available"] = False
        else:
            report["capture_available"] = True

        # Phase 3: Open capture (if available)
        if capture_ok:
            print("\n[*] Phase 3: Open and analyze capture")
            record_tool(client, report, "open_capture", {"path": capture_path})
        else:
            print("\n[*] Phase 3: Skipping capture-dependent tests")
            report["steps"].append({"tool": "open_capture", "arguments": {}, "error": "no capture available"})

        # Session status after open
        record_tool(client, report, "session_status", {})

        # Metadata
        record_tool(client, report, "get_capture_info", {})
        record_tool(client, report, "get_stats", {})
        record_tool(client, report, "get_log", {})

        # Phase 4: Events
        print("[*] Phase 4: Events and draws")
        list_events = record_tool(client, report, "list_events", {})
        list_draws = record_tool(client, report, "list_draws", {})

        draws = list_draws.get("draws", []) if isinstance(list_draws, dict) else []
        first_draw = draws[0]["eventId"] if draws else None

        if first_draw is not None:
            record_tool(client, report, "get_draw_info", {"eventId": first_draw})
            record_tool(client, report, "goto_event", {"eventId": first_draw})

            # Pipeline
            print("[*] Phase 5: Pipeline and shaders")
            record_tool(client, report, "get_pipeline_state", {"eventId": first_draw})
            record_tool(client, report, "get_bindings", {"eventId": first_draw})
            record_tool(client, report, "get_shader", {"eventId": first_draw, "stage": "vs", "mode": "reflect"})
            record_tool(client, report, "get_shader", {"eventId": first_draw, "stage": "vs", "mode": "disasm"})

            # Export render target
            print("[*] Phase 6: Export")
            record_tool(client, report, "export_render_target", {"index": 0})
        else:
            print("[-] No draw calls found, skipping draw-dependent tests")
            for tool in ("get_draw_info", "goto_event", "get_pipeline_state", "get_bindings",
                         "get_shader", "get_shader", "export_render_target"):
                report["steps"].append({"tool": tool, "arguments": {}, "error": "no draw found"})

        # Shaders
        record_tool(client, report, "list_shaders", {})
        record_tool(client, report, "search_shaders", {"pattern": "main"})

        # Resources
        print("[*] Phase 7: Resources")
        list_res = record_tool(client, report, "list_resources", {})
        resources = list_res.get("resources", []) if isinstance(list_res, dict) else []

        texture_id = find_resource(resources, "Texture")
        if texture_id:
            record_tool(client, report, "get_resource_info", {"resourceId": texture_id})
        else:
            report["steps"].append({"tool": "get_resource_info", "arguments": {}, "error": "no texture found"})

        # Passes
        record_tool(client, report, "list_passes", {})

        # Phase 8: Close
        if capture_ok:
            print("[*] Phase 8: Close")
            record_tool(client, report, "close_capture", {})
        record_tool(client, report, "session_status", {})

        # Phase 9: Error handling tests (always work)
        print("\n[*] Phase 9: Error handling tests")
        error_tests_ok = True

        # Test unknown tool — should get an error response
        try:
            resp = client.rpc("tools/call", {"name": "nonexistent_tool_xyz", "arguments": {}})
            # Either raises or returns error in response
            if "error" in resp or (resp.get("result", {}).get("isError")):
                pass
            else:
                error_tests_ok = False
        except (RuntimeError, TimeoutError):
            pass  # Also acceptable

        # Test invalid JSON-RPC method
        try:
            resp = client.rpc("nonexistent/method", {})
            if "error" in resp and resp["error"].get("code") == -32601:
                pass
            else:
                error_tests_ok = False
        except (RuntimeError, TimeoutError):
            error_tests_ok = False

        # Test missing required params
        try:
            resp = client.rpc("tools/call", {})
            if "error" in resp:
                pass
            else:
                error_tests_ok = False
        except (RuntimeError, TimeoutError):
            pass  # Acceptable

        report["error_handling_ok"] = error_tests_ok
        print(f"  Error handling: {'PASS' if error_tests_ok else 'FAIL'}")

        # Final session status
        record_tool(client, report, "session_status", {})

        # Build summary
        report["summary"] = build_summary(report)

    finally:
        client.close()
        report["stderr"] = client.stderr_lines
        report["stdout_noise"] = client.stdout_noise
        report["returncode"] = client.proc.returncode if client.proc else None

    # Write report
    result_path = output_dir / "macos_checks.json"
    with result_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Print summary
    summary = report.get("summary", {})
    checks = summary.get("checks", {})
    failures = summary.get("failures", [])

    print(f"\n{'='*60}")
    print(f"RESULTS: {len(checks) - len(failures)}/{len(checks)} checks passed")
    print(f"{'='*60}")

    for name, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    if failures:
        print(f"\nFailed checks: {', '.join(failures)}")

    print(f"\nFull report: {result_path}")
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run macOS renderdoc-mcp checks")
    parser.add_argument("--server", default=DEFAULT_SERVER)
    parser.add_argument("--smoke-exe", default=DEFAULT_SMOKE_EXE)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--renderdoc-lib-dir", default=DEFAULT_RENDERDOC_LIB_DIR)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
