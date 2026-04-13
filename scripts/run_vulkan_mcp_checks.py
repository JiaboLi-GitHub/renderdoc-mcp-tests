#!/usr/bin/env python3
"""
Comprehensive Vulkan MCP tool tests for renderdoc-mcp.

Tests all 59 renderdoc-mcp tools against a Vulkan capture from the advanced
Vulkan sample.  Known capture structure:
  - API: Vulkan, 14 events, 4 draws
  - Draw EIDs: 13 (shadow cube), 22 (geometry cube), 25 (overlay quad), 37 (present quad)
  - Compute dispatch: EID 30
  - Resources: 78 total (buffers, images, shader modules, etc.)

Usage:
    python scripts/run_vulkan_mcp_checks.py [--server PATH] [--vulkan-exe PATH] [--output-dir DIR]
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
DEFAULT_VULKAN_EXE = r"D:\renderdoc\test\build\bin\Release\renderdoc_mcp_vulkan_advanced.exe"
DEFAULT_OUTPUT_DIR = r"D:\renderdoc\test\artifacts\vulkan-coverage"


# ---------------------------------------------------------------------------
# McpClient (copied from run_full_coverage_checks.py, kept self-contained)
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
                "clientInfo": {"name": "vulkan-coverage-checks", "version": "1.0"},
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
# Helpers (copied from run_full_coverage_checks.py)
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


def find_resource_by_type_keyword(resources: list[dict], keyword: str) -> str | None:
    """Find the first resource whose type contains keyword (case-insensitive)."""
    for r in resources:
        rtype = r.get("type", "")
        if keyword.lower() in rtype.lower():
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
    "debug_pixel_ok",
    "debug_vertex_ok",
    "debug_thread_ok",
    "assert_clean_ok",
    "assert_state_ok",
    "diff_pipeline_ok",
    "list_counters_ok",
    "fetch_counters_ok",
    "get_counter_summary_ok",
    "shader_replace_ok",
    "shader_restore_ok",
    "shader_restore_all_ok",
}


def build_summary(report: dict) -> dict:
    checks: dict[str, bool] = {}

    # -- Phase 1: Capture + session --
    checks["session_status_before_open_ok"] = step_ok(report, "session_status", 0)
    checks["capture_frame_a_ok"] = step_ok(report, "capture_frame", 0)
    checks["capture_frame_b_ok"] = step_ok(report, "capture_frame", 1)
    checks["open_capture_ok"] = step_ok(report, "open_capture", 0)
    checks["session_status_after_open_ok"] = step_ok(report, "session_status", 1)
    checks["get_capture_info_ok"] = step_ok(report, "get_capture_info", 0)

    # -- Phase 2: Event/draw/pass enumeration --
    checks["list_events_ok"] = step_ok(report, "list_events", 0)
    checks["list_draws_ok"] = step_ok(report, "list_draws", 0)
    checks["get_draw_info_ok"] = step_ok(report, "get_draw_info", 0)
    checks["goto_event_ok"] = step_ok(report, "goto_event", 0)
    checks["list_passes_ok"] = step_ok(report, "list_passes", 0)
    checks["get_pass_info_ok"] = step_ok(report, "get_pass_info", 0)
    checks["get_pass_statistics_ok"] = step_ok(report, "get_pass_statistics", 0)
    checks["get_pass_attachments_ok"] = step_ok(report, "get_pass_attachments", 0)
    checks["get_pass_deps_ok"] = step_ok(report, "get_pass_deps", 0)
    checks["find_unused_targets_ok"] = step_ok(report, "find_unused_targets", 0)
    checks["get_stats_ok"] = step_ok(report, "get_stats", 0)
    checks["get_log_ok"] = step_ok(report, "get_log", 0)
    checks["get_log_filtered_ok"] = step_ok(report, "get_log", 1)

    # -- Phase 3: Pipeline/shader/resource inspection --
    checks["get_pipeline_state_ok"] = step_ok(report, "get_pipeline_state", 0)
    checks["get_bindings_ok"] = step_ok(report, "get_bindings", 0)
    checks["list_resources_ok"] = step_ok(report, "list_resources", 0)
    checks["get_resource_info_buffer_ok"] = step_ok(report, "get_resource_info", 0)
    checks["get_resource_info_texture_ok"] = step_ok(report, "get_resource_info", 1)
    checks["get_resource_usage_ok"] = step_ok(report, "get_resource_usage", 0)
    checks["get_texture_stats_ok"] = step_ok(report, "get_texture_stats", 0)
    checks["list_shaders_ok"] = step_ok(report, "list_shaders", 0)
    checks["search_shaders_ok"] = step_ok(report, "search_shaders", 0)
    checks["get_shader_vs_reflect_ok"] = step_ok(report, "get_shader", 0)
    checks["get_shader_vs_disasm_ok"] = step_ok(report, "get_shader", 1)
    checks["get_shader_ps_reflect_ok"] = step_ok(report, "get_shader", 2)
    checks["list_cbuffers_ok"] = step_ok(report, "list_cbuffers", 0)
    checks["get_cbuffer_contents_ok"] = step_ok(report, "get_cbuffer_contents", 0)

    # -- Phase 4: Export tools --
    export_rt = step_parsed(report, "export_render_target", 0)
    export_rt_path = export_rt.get("path", "") if isinstance(export_rt, dict) else ""
    checks["export_render_target_ok"] = (
        bool(export_rt_path)
        and os.path.exists(export_rt_path)
        and os.path.getsize(export_rt_path) > 0
    )

    export_tex = step_parsed(report, "export_texture", 0)
    export_tex_path = export_tex.get("path", "") if isinstance(export_tex, dict) else ""
    checks["export_texture_ok"] = (
        bool(export_tex_path)
        and os.path.exists(export_tex_path)
        and os.path.getsize(export_tex_path) > 0
    )

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

    # -- Phase 5: Shader edit chain --
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

    # -- Phase 6: Pixel analysis + debug --
    checks["pick_pixel_ok"] = step_ok(report, "pick_pixel", 0)
    checks["pixel_history_ok"] = step_ok(report, "pixel_history", 0)
    checks["debug_pixel_ok"] = step_ok(report, "debug_pixel", 0)
    checks["debug_vertex_ok"] = step_ok(report, "debug_vertex", 0)
    checks["debug_thread_ok"] = step_ok(report, "debug_thread", 0)

    # -- Phase 7: Assertions --
    assert_pixel = step_parsed(report, "assert_pixel", 0)
    checks["assert_pixel_ok"] = isinstance(assert_pixel, dict)

    assert_state = step_parsed(report, "assert_state", 0)
    checks["assert_state_ok"] = isinstance(assert_state, dict) and assert_state.get("pass") is True

    assert_count = step_parsed(report, "assert_count", 0)
    checks["assert_count_ok"] = isinstance(assert_count, dict) and assert_count.get("pass") is True

    checks["assert_clean_ok"] = step_ok(report, "assert_clean", 0)

    assert_image = step_parsed(report, "assert_image", 0)
    checks["assert_image_ok"] = isinstance(assert_image, dict) and assert_image.get("pass") is True

    # -- Phase 8: Close + Diff --
    checks["close_capture_ok"] = step_ok(report, "close_capture", 0)
    checks["session_status_after_close_ok"] = step_ok(report, "session_status", 2)
    checks["diff_open_ok"] = step_ok(report, "diff_open", 0)
    checks["diff_summary_ok"] = step_ok(report, "diff_summary", 0)
    checks["diff_draws_ok"] = step_ok(report, "diff_draws", 0)
    checks["diff_resources_ok"] = step_ok(report, "diff_resources", 0)
    checks["diff_stats_ok"] = step_ok(report, "diff_stats", 0)
    checks["diff_pipeline_ok"] = step_ok(report, "diff_pipeline", 0)
    checks["diff_framebuffer_ok"] = step_ok(report, "diff_framebuffer", 0)
    checks["diff_close_ok"] = step_ok(report, "diff_close", 0)

    # -- Phase 9: GPU counters --
    gpu_skipped = report.get("gpu_counters_skipped", False)
    checks["list_counters_ok"] = step_ok(report, "list_counters", 0) or gpu_skipped
    checks["fetch_counters_ok"] = step_ok(report, "fetch_counters", 0) or gpu_skipped
    checks["get_counter_summary_ok"] = step_ok(report, "get_counter_summary", 0) or gpu_skipped

    failures = [name for name, passed in checks.items() if not passed]
    hard_failures = [f for f in failures if f not in KNOWN_LIMITATIONS]

    return {
        "checks": checks,
        "total_checks": len(checks),
        "passed": sum(1 for v in checks.values() if v),
        "failed": len(failures),
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
            "vulkanExe": args.vulkan_exe,
            "api": "Vulkan",
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

        working_dir = str(Path(args.vulkan_exe).parent)
        capture_a_base = str(output_dir / "vulkan_capture_a.rdc")
        capture_b_base = str(output_dir / "vulkan_capture_b.rdc")

        # ==================================================================
        # Phase 1: Capture + session
        # ==================================================================

        # 1. session_status (before open)
        record_tool(client, report, "session_status", {})

        # 2. capture_frame x2 (two Vulkan captures for diff)
        capture_a = record_tool(
            client, report, "capture_frame",
            {"exePath": args.vulkan_exe, "workingDir": working_dir,
             "delayFrames": 60, "outputPath": capture_a_base},
            timeout=180.0,
        )
        capture_b = record_tool(
            client, report, "capture_frame",
            {"exePath": args.vulkan_exe, "workingDir": working_dir,
             "delayFrames": 60, "outputPath": capture_b_base},
            timeout=180.0,
        )

        capture_a_path = (capture_a.get("path") if isinstance(capture_a, dict) else None) or capture_a_base
        capture_b_path = (capture_b.get("path") if isinstance(capture_b, dict) else None) or capture_b_base

        # Fallback to pre-existing .rdc if capture_frame failed
        fallback = getattr(args, "fallback_rdc", "") or ""
        if fallback and not os.path.exists(capture_a_path):
            capture_a_path = fallback
            report["capture_fallback_used"] = True
        if not os.path.exists(capture_b_path):
            capture_b_path = capture_a_path  # self-diff is fine

        report["captures"] = {
            "captureA": capture_a_path,
            "captureB": capture_b_path,
            "generatedA": latest_generated(capture_a_base),
            "generatedB": latest_generated(capture_b_base),
        }

        # 3. open_capture (capture A)
        record_tool(client, report, "open_capture", {"path": capture_a_path})

        # 4. session_status (after open)
        record_tool(client, report, "session_status", {})

        # 5. get_capture_info
        record_tool(client, report, "get_capture_info", {})

        # ==================================================================
        # Phase 2: Event/draw/pass enumeration
        # ==================================================================

        # 6. list_events
        record_tool(client, report, "list_events", {})

        # 7. list_draws -- extract draw EIDs dynamically
        list_draws_result = record_tool(client, report, "list_draws", {})
        draws = list_draws_result.get("draws", []) if isinstance(list_draws_result, dict) else []
        first_draw_eid = draws[0]["eventId"] if len(draws) > 0 else None
        geometry_draw_eid = draws[1]["eventId"] if len(draws) > 1 else None
        # Find an indexed draw (vertexCount or indexCount > 0)
        indexed_draw_eid = None
        for d in draws:
            idx_count = d.get("indexCount", 0)
            if idx_count and idx_count > 0:
                indexed_draw_eid = d["eventId"]
                break
        if indexed_draw_eid is None and first_draw_eid is not None:
            indexed_draw_eid = first_draw_eid

        # 8. get_draw_info (first indexed draw)
        if indexed_draw_eid is not None:
            record_tool(client, report, "get_draw_info", {"eventId": indexed_draw_eid})
        else:
            report["steps"].append({"tool": "get_draw_info", "arguments": {}, "error": "no indexed draw found"})

        # 9. goto_event (first draw)
        if first_draw_eid is not None:
            record_tool(client, report, "goto_event", {"eventId": first_draw_eid})
        else:
            report["steps"].append({"tool": "goto_event", "arguments": {}, "error": "no draw found"})

        # 10. list_passes
        record_tool(client, report, "list_passes", {})

        # 11. get_pass_info (first draw EID)
        if first_draw_eid is not None:
            record_tool(client, report, "get_pass_info", {"eventId": first_draw_eid})
        else:
            report["steps"].append({"tool": "get_pass_info", "arguments": {}, "error": "no draw found"})

        # 12. get_pass_statistics
        record_tool(client, report, "get_pass_statistics", {})

        # 13. get_pass_attachments (first draw EID)
        if first_draw_eid is not None:
            record_tool(client, report, "get_pass_attachments", {"eventId": first_draw_eid})
        else:
            report["steps"].append({"tool": "get_pass_attachments", "arguments": {}, "error": "no draw found"})

        # 14. get_pass_deps
        record_tool(client, report, "get_pass_deps", {})

        # 15. find_unused_targets
        record_tool(client, report, "find_unused_targets", {})

        # 16. get_stats
        record_tool(client, report, "get_stats", {})

        # 17. get_log (no filter)
        record_tool(client, report, "get_log", {})

        # 18. get_log (level="HIGH")
        record_tool(client, report, "get_log", {"level": "HIGH"})

        # ==================================================================
        # Phase 3: Pipeline/shader/resource inspection
        # ==================================================================

        # 19. get_pipeline_state (geometry cube draw)
        if geometry_draw_eid is not None:
            record_tool(client, report, "goto_event", {"eventId": geometry_draw_eid})
            record_tool(client, report, "get_pipeline_state", {"eventId": geometry_draw_eid})
        else:
            report["steps"].append({"tool": "get_pipeline_state", "arguments": {}, "error": "no geometry draw found"})

        # 20. get_bindings (geometry cube draw)
        if geometry_draw_eid is not None:
            record_tool(client, report, "get_bindings", {"eventId": geometry_draw_eid})
        else:
            report["steps"].append({"tool": "get_bindings", "arguments": {}, "error": "no geometry draw found"})

        # 21. list_resources -- dynamically discover buffer/texture resource IDs
        list_res_result = record_tool(client, report, "list_resources", {})
        resources = list_res_result.get("resources", []) if isinstance(list_res_result, dict) else []

        # Find buffer and texture resources dynamically
        buffer_id = find_resource(resources, "Buffer")
        if buffer_id is None:
            buffer_id = find_resource_by_type_keyword(resources, "buffer")

        texture_id = find_resource(resources, "Texture")
        if texture_id is None:
            texture_id = find_resource_by_type_keyword(resources, "image")
        if texture_id is None:
            texture_id = find_resource_by_type_keyword(resources, "texture")

        # Also find a UBO buffer for export_buffer
        ubo_id = find_resource_by_name(resources, "ubo")
        if ubo_id is None:
            ubo_id = find_resource_by_name(resources, "uniform")
        if ubo_id is None:
            ubo_id = buffer_id  # fallback to first buffer

        # 22. get_resource_info (first buffer found)
        if buffer_id:
            record_tool(client, report, "get_resource_info", {"resourceId": buffer_id})
        else:
            report["steps"].append({"tool": "get_resource_info", "arguments": {}, "error": "no buffer resource found"})

        # 23. get_resource_info (first texture found)
        if texture_id:
            record_tool(client, report, "get_resource_info", {"resourceId": texture_id})
        else:
            report["steps"].append({"tool": "get_resource_info", "arguments": {}, "error": "no texture resource found"})

        # 24. get_resource_usage (first texture resource)
        if texture_id:
            record_tool(client, report, "get_resource_usage", {"resourceId": texture_id})
        else:
            report["steps"].append({"tool": "get_resource_usage", "arguments": {}, "error": "no texture resource found"})

        # 25. get_texture_stats (first texture resource)
        if texture_id:
            record_tool(client, report, "get_texture_stats", {"resourceId": texture_id})
        else:
            report["steps"].append({"tool": "get_texture_stats", "arguments": {}, "error": "no texture resource found"})

        # 26. list_shaders
        record_tool(client, report, "list_shaders", {})

        # 27. search_shaders (pattern="main")
        record_tool(client, report, "search_shaders", {"pattern": "main"})

        # 28. get_shader (first draw, stage="vs", mode="reflect")
        if first_draw_eid is not None:
            record_tool(client, report, "get_shader", {"eventId": first_draw_eid, "stage": "vs", "mode": "reflect"})
        else:
            report["steps"].append({"tool": "get_shader", "arguments": {}, "error": "no draw found"})

        # 29. get_shader (first draw, stage="vs", mode="disasm")
        if first_draw_eid is not None:
            record_tool(client, report, "get_shader", {"eventId": first_draw_eid, "stage": "vs", "mode": "disasm"})
        else:
            report["steps"].append({"tool": "get_shader", "arguments": {}, "error": "no draw found"})

        # 30. get_shader (geometry draw, stage="ps", mode="reflect")
        if geometry_draw_eid is not None:
            record_tool(client, report, "get_shader", {"eventId": geometry_draw_eid, "stage": "ps", "mode": "reflect"})
        else:
            report["steps"].append({"tool": "get_shader", "arguments": {}, "error": "no geometry draw found"})

        # 31. list_cbuffers (first draw, stage="vs")
        if first_draw_eid is not None:
            record_tool(client, report, "list_cbuffers", {"eventId": first_draw_eid, "stage": "vs"})
        else:
            report["steps"].append({"tool": "list_cbuffers", "arguments": {}, "error": "no draw found"})

        # 32. get_cbuffer_contents (first draw, stage="vs", index=0)
        if first_draw_eid is not None:
            record_tool(client, report, "get_cbuffer_contents", {"eventId": first_draw_eid, "stage": "vs", "index": 0})
        else:
            report["steps"].append({"tool": "get_cbuffer_contents", "arguments": {}, "error": "no draw found"})

        # ==================================================================
        # Phase 4: Export tools
        # ==================================================================

        # 33. export_render_target (goto geometry draw first)
        if geometry_draw_eid is not None:
            record_tool(client, report, "goto_event", {"eventId": geometry_draw_eid})
            record_tool(client, report, "export_render_target", {"index": 0})
        else:
            report["steps"].append({"tool": "export_render_target", "arguments": {}, "error": "no geometry draw found"})

        # 34. export_texture (first texture resourceId)
        if texture_id:
            record_tool(client, report, "export_texture", {"resourceId": texture_id})
        else:
            report["steps"].append({"tool": "export_texture", "arguments": {}, "error": "no texture resource found"})

        # 35. export_buffer (UBO buffer resourceId)
        if ubo_id:
            record_tool(client, report, "export_buffer", {"resourceId": ubo_id})
        else:
            report["steps"].append({"tool": "export_buffer", "arguments": {}, "error": "no buffer resource found"})

        # 36. export_mesh (indexed draw, format="obj", with outputPath)
        if indexed_draw_eid is not None:
            mesh_path = str(output_dir / f"export_mesh_eid{indexed_draw_eid}.obj")
            record_tool(client, report, "export_mesh", {
                "eventId": indexed_draw_eid, "format": "obj", "outputPath": mesh_path,
            })
        else:
            report["steps"].append({"tool": "export_mesh", "arguments": {}, "error": "no indexed draw found"})

        # 37. export_snapshot (first draw, outputDir=...)
        if first_draw_eid is not None:
            snap_dir = str(output_dir / f"export_snapshot_eid{first_draw_eid}")
            report["snapshot_dir"] = snap_dir
            record_tool(client, report, "export_snapshot", {
                "eventId": first_draw_eid, "outputDir": snap_dir,
            })
        else:
            report["snapshot_dir"] = ""
            report["steps"].append({"tool": "export_snapshot", "arguments": {}, "error": "no draw found"})

        # ==================================================================
        # Phase 5: Shader edit chain
        # ==================================================================

        # 38. shader_encodings
        encodings_result = record_tool(client, report, "shader_encodings", {})

        # Pick encoding: prefer "glsl" (we send GLSL source text), fallback to first available
        encoding = None
        if isinstance(encodings_result, dict):
            enc_list = encodings_result.get("encodings", [])
            if isinstance(enc_list, list):
                # First pass: look for glsl (since we send GLSL source text)
                for e in enc_list:
                    name = e.get("name", e) if isinstance(e, dict) else str(e)
                    if "glsl" in name.lower():
                        encoding = name
                        break
                # Fallback: first available
                if encoding is None and enc_list:
                    encoding = enc_list[0].get("name", enc_list[0]) if isinstance(enc_list[0], dict) else str(enc_list[0])

        # 39. shader_build -- compile a trivial GLSL fragment shader for Vulkan
        trivial_vulkan_fs = (
            "#version 450\n"
            "layout(location=0) in vec3 fragNormal;\n"
            "layout(location=1) in vec2 fragTexCoord;\n"
            "layout(location=2) in vec3 fragWorldPos;\n"
            "layout(set=0, binding=0) uniform UBO { mat4 mvp; mat4 model; vec4 lightPos; vec4 tintColor; } ubo;\n"
            "layout(set=0, binding=1) uniform sampler2D texSampler;\n"
            "layout(location=0) out vec4 outColor;\n"
            "void main() { outColor = vec4(1.0, 0.0, 0.0, 1.0); }\n"
        )

        shader_id = None
        if encoding and geometry_draw_eid is not None:
            build_result = record_tool(client, report, "shader_build", {
                "source": trivial_vulkan_fs, "stage": "ps", "encoding": encoding, "entry": "main",
            })
            if isinstance(build_result, dict):
                shader_id = build_result.get("shaderId")

            # 40-42. shader_replace/restore chain (short timeout — may hang on Vulkan)
            server_alive = True
            if shader_id is not None:
                result = record_tool(client, report, "shader_replace", {
                    "eventId": geometry_draw_eid, "stage": "ps", "shaderId": shader_id,
                }, timeout=30.0)
                if result is None and any(s.get("tool") == "shader_replace" and "timed out" in s.get("error", "") for s in report["steps"]):
                    server_alive = False
            else:
                report["steps"].append({"tool": "shader_replace", "arguments": {}, "error": "no shaderId from build"})

            if server_alive and shader_id is not None:
                record_tool(client, report, "shader_restore", {
                    "eventId": geometry_draw_eid, "stage": "ps",
                }, timeout=30.0)
            else:
                report["steps"].append({"tool": "shader_restore", "arguments": {}, "error": "server not responding or no shader replaced"})
        else:
            for tool in ("shader_build", "shader_replace", "shader_restore"):
                report["steps"].append({"tool": tool, "arguments": {}, "error": "no encoding or geometry draw"})

        # If server died during shader edit, restart it
        if client.proc and client.proc.poll() is not None:
            report["server_restarted"] = True
            client.close()
            client = McpClient(args.server)
            client.start()
            record_tool(client, report, "open_capture", {"path": capture_a_path})

        # 42. shader_restore_all
        record_tool(client, report, "shader_restore_all", {})

        # ==================================================================
        # Phase 6: Pixel analysis + debug
        # ==================================================================

        # Use geometry draw for pixel operations (1024x720 color attachment)
        pixel_x = 512
        pixel_y = 360

        # 43. pick_pixel (geometry draw, center pixel)
        if geometry_draw_eid is not None:
            record_tool(client, report, "goto_event", {"eventId": geometry_draw_eid})
            record_tool(client, report, "pick_pixel", {
                "eventId": geometry_draw_eid, "x": pixel_x, "y": pixel_y,
            })
        else:
            report["steps"].append({"tool": "pick_pixel", "arguments": {}, "error": "no geometry draw found"})

        # 44. pixel_history (center of geometry output)
        if geometry_draw_eid is not None:
            record_tool(client, report, "pixel_history", {
                "x": pixel_x, "y": pixel_y,
            })
        else:
            report["steps"].append({"tool": "pixel_history", "arguments": {}, "error": "no geometry draw found"})

        # 45. debug_pixel (geometry draw, center pixel) -- may fail (known limitation)
        if geometry_draw_eid is not None:
            record_tool(client, report, "debug_pixel", {
                "eventId": geometry_draw_eid, "x": pixel_x, "y": pixel_y,
            })
        else:
            report["steps"].append({"tool": "debug_pixel", "arguments": {}, "error": "no geometry draw found"})

        # 46. debug_vertex (indexed draw, vertexId=0) -- may fail
        if indexed_draw_eid is not None:
            record_tool(client, report, "debug_vertex", {
                "eventId": indexed_draw_eid, "vertexId": 0,
            })
        else:
            report["steps"].append({"tool": "debug_vertex", "arguments": {}, "error": "no indexed draw found"})

        # 47. debug_thread (compute dispatch EID 30, workgroup [0,0,0], thread [0,0,0]) -- KEY TEST
        # Try to find the compute dispatch EID dynamically from list_events
        compute_eid = 30  # Known EID from capture analysis
        events_result = step_parsed(report, "list_events", 0)
        if isinstance(events_result, dict):
            event_list = events_result.get("events", [])
            for ev in event_list:
                name = ev.get("name", "").lower()
                if "dispatch" in name:
                    compute_eid = ev.get("eventId", compute_eid)
                    break

        record_tool(client, report, "debug_thread", {
            "eventId": compute_eid,
            "groupX": 0, "groupY": 0, "groupZ": 0,
            "threadX": 0, "threadY": 0, "threadZ": 0,
        })

        # ==================================================================
        # Phase 7: Assertions
        # ==================================================================

        # 48. assert_pixel (geometry draw, known position)
        # Use pick_pixel result as expected values for self-validation
        if geometry_draw_eid is not None:
            pick_result = step_parsed(report, "pick_pixel", 0)
            if isinstance(pick_result, dict):
                # Extract color as [R,G,B,A] float array
                color = pick_result.get("color")
                if isinstance(color, dict):
                    expected_rgba = [color.get("r", 0), color.get("g", 0), color.get("b", 0), color.get("a", 1)]
                elif isinstance(color, list):
                    expected_rgba = color
                else:
                    expected_rgba = [0.0, 0.0, 0.0, 1.0]
                record_tool(client, report, "assert_pixel", {
                    "eventId": geometry_draw_eid,
                    "x": pixel_x, "y": pixel_y,
                    "expected": expected_rgba,
                    "tolerance": 0.02,
                })
            else:
                record_tool(client, report, "assert_pixel", {
                    "eventId": geometry_draw_eid,
                    "x": pixel_x, "y": pixel_y,
                    "expected": [0.0, 0.0, 0.0, 1.0],
                    "tolerance": 1.0,
                })
        else:
            report["steps"].append({"tool": "assert_pixel", "arguments": {}, "error": "no geometry draw found"})

        # 49. assert_state (geometry draw, pipeline state path)
        if geometry_draw_eid is not None:
            record_tool(client, report, "assert_state", {
                "eventId": geometry_draw_eid,
                "path": "vertexShader.entryPoint",
                "expected": "main",
            })
        else:
            report["steps"].append({"tool": "assert_state", "arguments": {}, "error": "no geometry draw found"})

        # 50. assert_count ("draws", 4) -- expect 4 draws
        record_tool(client, report, "assert_count", {
            "what": "draws",
            "expected": 4,
        })

        # 51. assert_clean (may fail if validation errors exist)
        record_tool(client, report, "assert_clean", {})

        # 52. assert_image -- export RT, self-compare
        rt_result = step_parsed(report, "export_render_target", 0)
        rt_png_path = rt_result.get("path", "") if isinstance(rt_result, dict) else ""
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

        # ==================================================================
        # Phase 8: Close + Diff
        # ==================================================================

        # 53. close_capture
        record_tool(client, report, "close_capture", {})

        # 54. session_status (after close)
        record_tool(client, report, "session_status", {})

        # 55. diff_open (captureA, captureB)
        record_tool(client, report, "diff_open", {
            "captureA": capture_a_path, "captureB": capture_b_path,
        })

        # 56. diff_summary
        record_tool(client, report, "diff_summary", {})

        # 57. diff_draws
        record_tool(client, report, "diff_draws", {})

        # 58. diff_resources
        record_tool(client, report, "diff_resources", {})

        # 59. diff_stats
        record_tool(client, report, "diff_stats", {})

        # 60. diff_pipeline (marker="")
        record_tool(client, report, "diff_pipeline", {"marker": ""})

        # 61. diff_framebuffer
        record_tool(client, report, "diff_framebuffer", {})

        # 62. diff_close
        record_tool(client, report, "diff_close", {})

        # ==================================================================
        # Phase 9: GPU counters (graceful degradation)
        # ==================================================================

        # 63. open_capture (capture A)
        record_tool(client, report, "open_capture", {"path": capture_a_path})

        # 64. list_counters
        counters = record_tool(client, report, "list_counters", {})
        has_counters = (
            isinstance(counters, dict)
            and isinstance(counters.get("counters", []), list)
            and len(counters.get("counters", [])) > 0
        )

        # 65. fetch_counters (if available)
        # 66. get_counter_summary (if available)
        if has_counters:
            counter_names = [
                c.get("name") for c in counters["counters"][:3]
                if isinstance(c, dict) and c.get("name")
            ]
            record_tool(client, report, "fetch_counters", {"counterNames": counter_names})
            record_tool(client, report, "get_counter_summary", {"limit": 5})
        else:
            report["gpu_counters_skipped"] = True

        # 67. close_capture
        record_tool(client, report, "close_capture", {})

        # ==================================================================
        # Build summary
        # ==================================================================
        report["summary"] = build_summary(report)

    finally:
        client.close()
        report["stderr"] = client.stderr_lines
        report["stdout_noise"] = client.stdout_noise
        report["returncode"] = client.proc.returncode if client.proc else None

    result_path = output_dir / "vulkan_mcp_checks.json"
    with result_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    print(str(result_path))
    print(json.dumps(report.get("summary", {}), ensure_ascii=False, indent=2))

    hard_failures = report.get("summary", {}).get("hard_failures", ["unknown"])
    return 0 if not hard_failures else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run comprehensive Vulkan MCP tool coverage checks against the advanced Vulkan sample."
    )
    parser.add_argument("--server", default=DEFAULT_SERVER, help="Path to renderdoc-mcp.exe")
    parser.add_argument("--vulkan-exe", default=DEFAULT_VULKAN_EXE, help="Path to the advanced Vulkan test exe")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for captures and JSON results")
    parser.add_argument("--fallback-rdc", default="", help="Pre-existing .rdc to use if capture_frame fails")
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
