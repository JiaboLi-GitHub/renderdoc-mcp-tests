#!/usr/bin/env python3
"""
Full-coverage MCP tool tests for renderdoc-mcp.

Targets the 19+ tools NOT covered by run_extended_mcp_checks.py:
  session management, capture metadata, resource detail, pass info,
  export (buffer/mesh/snapshot), shader edit chain, diff extensions,
  assertions, and GPU counters.

Usage:
    python scripts/run_full_coverage_checks.py [--server PATH] [--advanced-exe PATH] [--output-dir DIR]
"""
import argparse
import glob
import json
import os
import queue
import subprocess
import threading
import time
from pathlib import Path


DEFAULT_SERVER = r"C:\Users\Administrator\.codex\vendor_imports\renderdoc-mcp\bin\renderdoc-mcp.exe"
DEFAULT_ADVANCED_EXE = r"D:\renderdoc\test\build\bin\Release\renderdoc_mcp_opengl_advanced.exe"
DEFAULT_OUTPUT_DIR = r"D:\renderdoc\test\artifacts\full-coverage"


# ---------------------------------------------------------------------------
# McpClient (reused from run_extended_mcp_checks.py, kept self-contained)
# ---------------------------------------------------------------------------

class McpClient:
    def __init__(self, server_path: str):
        self.server_path = server_path
        self.proc = None
        self.stdout_q: queue.Queue = queue.Queue()
        self.stderr_q: queue.Queue = queue.Queue()
        self.stderr_lines: list[str] = []
        self.stdout_noise: list[str] = []
        self.next_id = 1

    def start(self) -> None:
        self.proc = subprocess.Popen(
            [self.server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        threading.Thread(target=self._pump_stdout, daemon=True).start()
        threading.Thread(target=self._pump_stderr, daemon=True).start()

        init = self.rpc(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "full-coverage-checks", "version": "1.0"},
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

    # -- internal helpers --

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
            message = error.get("message", "unknown error")
            raise RuntimeError(message)

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

    def call_tool(self, name: str, arguments: dict | None = None, timeout: float = 120.0) -> tuple[dict, dict]:
        arguments = arguments or {}
        resp = self.rpc("tools/call", {"name": name, "arguments": arguments}, timeout=timeout)
        return self._parse_tool_content(resp), resp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def record_tool(client: McpClient, report: dict, name: str, arguments: dict | None = None, timeout: float = 120.0):
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


def latest_generated(base_path: str) -> list[str]:
    stem = Path(base_path).stem
    pattern = str(Path(base_path).with_name(stem + "*.rdc"))
    return sorted(glob.glob(pattern))


def find_resource(resources: list[dict], rtype: str) -> str | None:
    """Find the first resource matching a type string (case-insensitive)."""
    for r in resources:
        if r.get("type", "").lower() == rtype.lower():
            rid = r.get("resourceId") or r.get("id")
            if rid:
                return str(rid)
    return None


def find_resource_by_name(resources: list[dict], substr: str) -> str | None:
    """Find the first resource whose name contains substr."""
    for r in resources:
        name = r.get("name", "")
        if substr.lower() in name.lower():
            rid = r.get("resourceId") or r.get("id")
            if rid:
                return str(rid)
    return None


def step_ok(report: dict, tool_name: str, index: int = 0) -> bool:
    """Check if the n-th step for a tool succeeded (no error key)."""
    count = 0
    for step in report["steps"]:
        if step["tool"] == tool_name:
            if count == index:
                return "error" not in step and step.get("parsed") is not None
            count += 1
    return False


def step_parsed(report: dict, tool_name: str, index: int = 0):
    """Get the parsed result of the n-th step for a tool."""
    count = 0
    for step in report["steps"]:
        if step["tool"] == tool_name:
            if count == index:
                return step.get("parsed")
            count += 1
    return None


# ---------------------------------------------------------------------------
# Summary builder
# ---------------------------------------------------------------------------

KNOWN_LIMITATIONS = {
    "diff_pipeline_ok",
    "list_counters_ok",
    "fetch_counters_ok",
    "get_counter_summary_ok",
}


def build_summary(report: dict) -> dict:
    checks: dict[str, bool] = {}

    # -- Session management --
    checks["session_status_before_open_ok"] = step_ok(report, "session_status", 0)
    checks["session_status_after_open_ok"] = step_ok(report, "session_status", 1)
    checks["session_status_after_close_ok"] = step_ok(report, "session_status", 2)
    checks["close_capture_ok"] = step_ok(report, "close_capture", 0)

    # -- Capture metadata --
    checks["get_stats_ok"] = step_ok(report, "get_stats", 0)
    checks["get_log_ok"] = step_ok(report, "get_log", 0)
    checks["get_log_filtered_ok"] = step_ok(report, "get_log", 1)

    # -- Resource detail + pass --
    checks["get_resource_info_buffer_ok"] = step_ok(report, "get_resource_info", 0)
    checks["get_resource_info_texture_ok"] = step_ok(report, "get_resource_info", 1)
    checks["get_pass_info_ok"] = step_ok(report, "get_pass_info", 0)
    checks["get_pass_deps_ok"] = step_ok(report, "get_pass_deps", 0)

    # -- Export --
    export_buffer = step_parsed(report, "export_buffer", 0)
    export_buffer_path = export_buffer.get("path", "") if isinstance(export_buffer, dict) else ""
    checks["export_buffer_ok"] = (
        bool(export_buffer_path)
        and os.path.exists(export_buffer_path)
        and os.path.getsize(export_buffer_path) > 0
    )

    export_mesh = step_parsed(report, "export_mesh", 0)
    if isinstance(export_mesh, dict) and export_mesh.get("outputPath"):
        mesh_path = export_mesh["outputPath"]
        checks["export_mesh_ok"] = os.path.exists(mesh_path) and os.path.getsize(mesh_path) > 0
    elif isinstance(export_mesh, dict) and (export_mesh.get("vertexCount", 0) > 0 or export_mesh.get("obj")):
        checks["export_mesh_ok"] = True
    else:
        checks["export_mesh_ok"] = False

    export_snap = step_parsed(report, "export_snapshot", 0)
    snap_dir = report.get("snapshot_dir", "")
    checks["export_snapshot_ok"] = (
        isinstance(export_snap, dict)
        and bool(snap_dir)
        and os.path.isdir(snap_dir)
        and len(os.listdir(snap_dir)) > 0
    )

    # -- Shader edit chain --
    checks["shader_encodings_ok"] = (
        step_ok(report, "shader_encodings", 0)
        and isinstance(step_parsed(report, "shader_encodings", 0), dict)
    )

    build_result = step_parsed(report, "shader_build", 0)
    checks["shader_build_ok"] = (
        isinstance(build_result, dict) and build_result.get("shaderId") is not None
    )
    checks["shader_replace_ok"] = step_ok(report, "shader_replace", 0)
    checks["shader_restore_ok"] = step_ok(report, "shader_restore", 0)
    checks["shader_restore_all_ok"] = step_ok(report, "shader_restore_all", 0)

    # -- Assertions --
    assert_state = step_parsed(report, "assert_state", 0)
    checks["assert_state_ok"] = isinstance(assert_state, dict) and assert_state.get("pass") is True

    assert_image = step_parsed(report, "assert_image", 0)
    checks["assert_image_ok"] = isinstance(assert_image, dict) and assert_image.get("pass") is True

    # -- Diff extensions --
    checks["diff_stats_ok"] = step_ok(report, "diff_stats", 0)
    checks["diff_pipeline_ok"] = step_ok(report, "diff_pipeline", 0)

    # -- GPU counters --
    gpu_skipped = report.get("gpu_counters_skipped", False)
    checks["list_counters_ok"] = step_ok(report, "list_counters", 0) or gpu_skipped
    checks["fetch_counters_ok"] = step_ok(report, "fetch_counters", 0) or gpu_skipped
    checks["get_counter_summary_ok"] = step_ok(report, "get_counter_summary", 0) or gpu_skipped

    failures = [name for name, passed in checks.items() if not passed]
    hard_failures = [f for f in failures if f not in KNOWN_LIMITATIONS]

    return {
        "checks": checks,
        "failures": failures,
        "hard_failures": hard_failures,
        "known_limitations_failed": [f for f in failures if f in KNOWN_LIMITATIONS],
        "gpu_counters_skipped": gpu_skipped,
    }


# ---------------------------------------------------------------------------
# Main test runner
# ---------------------------------------------------------------------------

def run(args) -> int:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report: dict = {
        "metadata": {
            "server": args.server,
            "advancedExe": args.advanced_exe,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "steps": [],
        "captures": {},
        "stderr": [],
        "stdout_noise": [],
    }

    client = McpClient(args.server)
    try:
        client.start()
        report["initialize"] = client.initialize_response

        working_dir = str(Path(args.advanced_exe).parent)
        capture_a_base = str(output_dir / "capture_a.rdc")
        capture_b_base = str(output_dir / "capture_b.rdc")

        # ── Phase 1: Session status before any capture ────────────────────
        record_tool(client, report, "session_status", {})

        # ── Phase 2: Capture two frames + open ────────────────────────────
        capture_a = record_tool(
            client, report, "capture_frame",
            {"exePath": args.advanced_exe, "workingDir": working_dir,
             "delayFrames": 90, "outputPath": capture_a_base},
            timeout=180.0,
        )
        capture_b = record_tool(
            client, report, "capture_frame",
            {"exePath": args.advanced_exe, "workingDir": working_dir,
             "delayFrames": 90, "outputPath": capture_b_base},
            timeout=180.0,
        )

        capture_a_path = capture_a.get("path") if isinstance(capture_a, dict) else capture_a_base
        capture_b_path = capture_b.get("path") if isinstance(capture_b, dict) else capture_b_base
        report["captures"] = {
            "captureA": capture_a_path,
            "captureB": capture_b_path,
            "generatedA": latest_generated(capture_a_base),
            "generatedB": latest_generated(capture_b_base),
        }

        record_tool(client, report, "open_capture", {"path": capture_a_path})

        # session_status with capture open (index 1)
        record_tool(client, report, "session_status", {})

        # ── Phase 3: Capture metadata ─────────────────────────────────────
        record_tool(client, report, "get_stats", {})
        record_tool(client, report, "get_log", {})
        record_tool(client, report, "get_log", {"level": "HIGH"})

        # ── Phase 4: Resource detail + pass info ──────────────────────────
        list_draws = record_tool(client, report, "list_draws", {})
        draws = list_draws.get("draws", []) if isinstance(list_draws, dict) else []
        first_draw = draws[0]["eventId"] if len(draws) > 0 else None
        composite_draw = draws[2]["eventId"] if len(draws) > 2 else None

        list_res = record_tool(client, report, "list_resources", {})
        resources = list_res.get("resources", []) if isinstance(list_res, dict) else []

        # Find a buffer and a texture resource dynamically
        buffer_id = find_resource(resources, "Buffer")
        texture_id = find_resource(resources, "Texture")

        if buffer_id:
            record_tool(client, report, "get_resource_info", {"resourceId": buffer_id})
        else:
            report["steps"].append({"tool": "get_resource_info", "arguments": {}, "error": "no buffer resource found"})

        if texture_id:
            record_tool(client, report, "get_resource_info", {"resourceId": texture_id})
        else:
            report["steps"].append({"tool": "get_resource_info", "arguments": {}, "error": "no texture resource found"})

        record_tool(client, report, "list_passes", {})

        if first_draw is not None:
            record_tool(client, report, "get_pass_info", {"eventId": first_draw})
        else:
            report["steps"].append({"tool": "get_pass_info", "arguments": {}, "error": "no draw found"})

        record_tool(client, report, "get_pass_deps", {})

        # ── Phase 5: Export tools ─────────────────────────────────────────
        if buffer_id:
            record_tool(client, report, "export_buffer", {"resourceId": buffer_id})
        else:
            report["steps"].append({"tool": "export_buffer", "arguments": {}, "error": "no buffer resource"})

        if first_draw is not None:
            mesh_path = str(output_dir / f"export_mesh_eid{first_draw}.obj")
            record_tool(client, report, "export_mesh", {
                "eventId": first_draw, "format": "obj", "outputPath": mesh_path,
            })
        else:
            report["steps"].append({"tool": "export_mesh", "arguments": {}, "error": "no draw found"})

        if first_draw is not None:
            snap_dir = str(output_dir / f"export_snapshot_eid{first_draw}")
            report["snapshot_dir"] = snap_dir
            record_tool(client, report, "export_snapshot", {
                "eventId": first_draw, "outputDir": snap_dir,
            })
        else:
            report["snapshot_dir"] = ""
            report["steps"].append({"tool": "export_snapshot", "arguments": {}, "error": "no draw found"})

        # ── Phase 6: Shader edit chain ────────────────────────────────────
        encodings_result = record_tool(client, report, "shader_encodings", {})

        # Pick encoding: prefer "glsl", fallback to first available
        encoding = None
        if isinstance(encodings_result, dict):
            enc_list = encodings_result.get("encodings", [])
            if isinstance(enc_list, list):
                for e in enc_list:
                    name = e.get("name", e) if isinstance(e, dict) else str(e)
                    if "glsl" in name.lower():
                        encoding = name
                        break
                if encoding is None and enc_list:
                    encoding = enc_list[0].get("name", enc_list[0]) if isinstance(enc_list[0], dict) else str(enc_list[0])

        trivial_fs = (
            "#version 330 core\n"
            "in vec2 vTexCoord;\n"
            "in vec4 vTint;\n"
            "uniform sampler2D uBaseTexture;\n"
            "out vec4 fragColor;\n"
            "void main() {\n"
            "    fragColor = vec4(1.0, 0.0, 0.0, 1.0);\n"
            "}\n"
        )

        shader_id = None
        if encoding and first_draw is not None:
            build_result = record_tool(client, report, "shader_build", {
                "source": trivial_fs, "stage": "ps", "encoding": encoding, "entry": "main",
            })
            if isinstance(build_result, dict):
                shader_id = build_result.get("shaderId")

            if shader_id is not None:
                record_tool(client, report, "shader_replace", {
                    "eventId": first_draw, "stage": "ps", "shaderId": shader_id,
                })
                record_tool(client, report, "shader_restore", {
                    "eventId": first_draw, "stage": "ps",
                })
            else:
                report["steps"].append({"tool": "shader_replace", "arguments": {}, "error": "no shaderId from build"})
                report["steps"].append({"tool": "shader_restore", "arguments": {}, "error": "no shader replaced"})
        else:
            for tool in ("shader_build", "shader_replace", "shader_restore"):
                report["steps"].append({"tool": tool, "arguments": {}, "error": "no encoding or draw"})

        record_tool(client, report, "shader_restore_all", {})

        # ── Phase 7: Assertions ───────────────────────────────────────────
        # Export render target for assert_image (export at first_draw, use same file as both expected/actual)
        rt_png_path = None
        if first_draw is not None:
            record_tool(client, report, "goto_event", {"eventId": first_draw})
            rt_result = record_tool(client, report, "export_render_target", {"index": 0})
            if isinstance(rt_result, dict):
                rt_png_path = rt_result.get("path")

        if first_draw is not None:
            record_tool(client, report, "assert_state", {
                "eventId": first_draw,
                "path": "vertexShader.entryPoint",
                "expected": "main",
            })
        else:
            report["steps"].append({"tool": "assert_state", "arguments": {}, "error": "no draw found"})

        if rt_png_path and os.path.exists(rt_png_path):
            diff_img = str(output_dir / "assert_image_diff.png")
            record_tool(client, report, "assert_image", {
                "expectedPath": rt_png_path,
                "actualPath": rt_png_path,
                "threshold": 0,
                "diffOutputPath": diff_img,
            })
        else:
            report["steps"].append({"tool": "assert_image", "arguments": {}, "error": "no RT PNG available"})

        # ── Phase 8: Close + diff extensions ──────────────────────────────
        record_tool(client, report, "close_capture", {})

        # session_status after close (index 2)
        record_tool(client, report, "session_status", {})

        record_tool(client, report, "diff_open", {
            "captureA": capture_a_path, "captureB": capture_b_path,
        })
        record_tool(client, report, "diff_stats", {})
        record_tool(client, report, "diff_pipeline", {"marker": ""})
        record_tool(client, report, "diff_close", {})

        # ── Phase 9: GPU counters (graceful degradation) ──────────────────
        record_tool(client, report, "open_capture", {"path": capture_a_path})

        counters = record_tool(client, report, "list_counters", {})
        has_counters = (
            isinstance(counters, dict)
            and isinstance(counters.get("counters", []), list)
            and len(counters.get("counters", [])) > 0
        )
        if has_counters:
            counter_names = [
                c.get("name") for c in counters["counters"][:3]
                if isinstance(c, dict) and c.get("name")
            ]
            record_tool(client, report, "fetch_counters", {"counterNames": counter_names})
            record_tool(client, report, "get_counter_summary", {"limit": 5})
        else:
            report["gpu_counters_skipped"] = True

        record_tool(client, report, "close_capture", {})

        # ── Build summary ─────────────────────────────────────────────────
        report["summary"] = build_summary(report)

    finally:
        client.close()
        report["stderr"] = client.stderr_lines
        report["stdout_noise"] = client.stdout_noise
        report["returncode"] = client.proc.returncode if client.proc else None

    result_path = output_dir / "full_coverage_checks.json"
    with result_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    print(str(result_path))
    print(json.dumps(report.get("summary", {}), ensure_ascii=False, indent=2))

    hard_failures = report.get("summary", {}).get("hard_failures", ["unknown"])
    return 0 if not hard_failures else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run full-coverage renderdoc-mcp checks against the advanced OpenGL sample."
    )
    parser.add_argument("--server", default=DEFAULT_SERVER, help="Path to renderdoc-mcp.exe")
    parser.add_argument("--advanced-exe", default=DEFAULT_ADVANCED_EXE, help="Path to the advanced OpenGL test exe")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for captures and JSON results")
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
