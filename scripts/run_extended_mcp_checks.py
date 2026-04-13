#!/usr/bin/env python3
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
DEFAULT_OUTPUT_DIR = r"D:\renderdoc\test\artifacts\extended"


class McpClient:
    def __init__(self, server_path: str):
        self.server_path = server_path
        self.proc = None
        self.stdout_q = queue.Queue()
        self.stderr_q = queue.Queue()
        self.stderr_lines = []
        self.stdout_noise = []
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
                "clientInfo": {"name": "extended-mcp-checks", "version": "1.0"},
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


def first_color_target(pass_attachments: dict | None) -> str | None:
    if not isinstance(pass_attachments, dict):
        return None
    targets = pass_attachments.get("colorTargets")
    if isinstance(targets, list) and targets:
        return targets[0].get("resourceId")
    return None


def render_target_size(pipeline_state: dict | None) -> tuple[int, int]:
    if not isinstance(pipeline_state, dict):
        return (0, 0)
    render_targets = pipeline_state.get("renderTargets")
    if isinstance(render_targets, list) and render_targets:
        width = int(render_targets[0].get("width", 0))
        height = int(render_targets[0].get("height", 0))
        return (width, height)
    viewports = pipeline_state.get("viewports")
    if isinstance(viewports, list) and viewports:
        width = int(viewports[0].get("width", 0))
        height = int(viewports[0].get("height", 0))
        return (width, height)
    return (0, 0)


def build_summary(report: dict) -> dict:
    summary = {
        "checks": {},
        "captures": {},
        "events": {},
        "resources": {},
        "diff": {},
        "failures": [],
    }

    results = {}
    for step in report["steps"]:
        results.setdefault(step["tool"], []).append(step)

    captures = report.get("captures", {})
    summary["captures"] = captures

    list_events = results.get("list_events", [{}])[0].get("parsed", {})
    list_draws = results.get("list_draws", [{}])[0].get("parsed", {})
    draw_info = results.get("get_draw_info", [{}])[0].get("parsed", {})
    list_shaders = results.get("list_shaders", [{}])[0].get("parsed", {})
    search_shaders = results.get("search_shaders", [{}])[0].get("parsed", {})
    tex_stats = results.get("get_texture_stats", [{}])[0].get("parsed", {})
    resource_usage = results.get("get_resource_usage", [{}])[0].get("parsed", {})
    export_texture = results.get("export_texture", [{}])[0].get("parsed", {})
    diff_summary = results.get("diff_summary", [{}])[0].get("parsed", {})
    diff_draws = results.get("diff_draws", [{}])[0].get("parsed", {})
    diff_resources = results.get("diff_resources", [{}])[0].get("parsed", {})
    diff_fb = results.get("diff_framebuffer", [{}])[0].get("parsed", {})

    shader_steps = results.get("get_shader", [])
    debug_vertex = results.get("debug_vertex", [{}])[0]
    debug_pixel_steps = results.get("debug_pixel", [])

    summary["events"]["count"] = list_events.get("count")
    summary["events"]["draw_count"] = list_draws.get("count")
    summary["events"]["draw_event_ids"] = [
        item.get("eventId") for item in list_draws.get("draws", [])
    ] if isinstance(list_draws, dict) else []

    summary["resources"]["scene_color_resource"] = report.get("scene_color_resource")
    summary["resources"]["export_texture_path"] = export_texture.get("path") if isinstance(export_texture, dict) else None
    summary["resources"]["texture_usage_entries"] = len(resource_usage.get("entries", [])) if isinstance(resource_usage, dict) else None
    summary["resources"]["shader_count"] = list_shaders.get("count") if isinstance(list_shaders, dict) else None
    summary["resources"]["search_main_count"] = search_shaders.get("count") if isinstance(search_shaders, dict) else None

    summary["diff"]["identical"] = diff_summary.get("identical") if isinstance(diff_summary, dict) else None
    summary["diff"]["divergedAt"] = diff_summary.get("divergedAt") if isinstance(diff_summary, dict) else None
    summary["diff"]["draws"] = diff_draws if isinstance(diff_draws, dict) else None
    summary["diff"]["resources"] = diff_resources if isinstance(diff_resources, dict) else None
    summary["diff"]["framebuffer"] = diff_fb if isinstance(diff_fb, dict) else None

    checks = summary["checks"]
    checks["list_events_shape_ok"] = (
        isinstance(list_events, dict)
        and isinstance(list_events.get("events"), list)
        and list_events.get("count") == len(list_events.get("events", []))
    )
    checks["list_draws_ok"] = (
        isinstance(list_draws, dict)
        and isinstance(list_draws.get("draws"), list)
        and list_draws.get("count") == len(list_draws.get("draws", []))
        and list_draws.get("count", 0) >= 4
    )
    checks["get_draw_info_ok"] = (
        isinstance(draw_info, dict)
        and draw_info.get("eventId") in summary["events"]["draw_event_ids"]
    )

    checks["shader_reflect_ok"] = False
    checks["shader_disasm_ok"] = False
    for step in shader_steps:
        parsed = step.get("parsed")
        if not isinstance(parsed, dict):
            continue
        if "entryPoint" in parsed and ("resources" in parsed or "constantBlocks" in parsed):
            checks["shader_reflect_ok"] = True
        if "disassembly" in parsed and parsed.get("disassembly"):
            checks["shader_disasm_ok"] = True

    checks["list_shaders_ok"] = isinstance(list_shaders, dict) and list_shaders.get("count", 0) > 0
    checks["search_shaders_ok"] = isinstance(search_shaders, dict) and search_shaders.get("count", 0) > 0
    checks["texture_stats_ok"] = (
        isinstance(tex_stats, dict)
        and "min" in tex_stats
        and "max" in tex_stats
    )
    checks["resource_usage_ok"] = (
        isinstance(resource_usage, dict)
        and isinstance(resource_usage.get("entries"), list)
        and len(resource_usage.get("entries", [])) > 0
    )
    checks["export_texture_ok"] = (
        isinstance(export_texture, dict)
        and export_texture.get("path")
        and os.path.exists(export_texture["path"])
        and os.path.getsize(export_texture["path"]) > 0
    )
    checks["debug_vertex_ok"] = (
        isinstance(debug_vertex.get("parsed"), dict)
        and debug_vertex["parsed"].get("stage") == "vs"
        and "outputs" in debug_vertex["parsed"]
    )

    checks["debug_pixel_composite_ok"] = False
    checks["debug_pixel_overlay_ok"] = False
    if len(debug_pixel_steps) >= 1:
        parsed = debug_pixel_steps[0].get("parsed")
        checks["debug_pixel_composite_ok"] = isinstance(parsed, dict) and "outputs" in parsed
    if len(debug_pixel_steps) >= 2:
        parsed = debug_pixel_steps[1].get("parsed")
        checks["debug_pixel_overlay_ok"] = isinstance(parsed, dict) and "outputs" in parsed

    checks["diff_summary_ok"] = isinstance(diff_summary, dict) and diff_summary.get("identical") is True
    checks["diff_draws_ok"] = (
        isinstance(diff_draws, dict)
        and diff_draws.get("modified") == 0
        and diff_draws.get("added") == 0
        and diff_draws.get("deleted") == 0
    )
    checks["diff_resources_ok"] = (
        isinstance(diff_resources, dict)
        and diff_resources.get("modified") == 0
        and diff_resources.get("added") == 0
        and diff_resources.get("deleted") == 0
    )
    checks["diff_framebuffer_ok"] = isinstance(diff_fb, dict) and diff_fb.get("diffPixels") == 0

    summary["failures"] = [name for name, passed in checks.items() if not passed]
    return summary


def run(args) -> int:
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = {
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
        capture_a_base = str(output_dir / "advanced_extended_a.rdc")
        capture_b_base = str(output_dir / "advanced_extended_b.rdc")

        capture_a = record_tool(
            client,
            report,
            "capture_frame",
            {
                "exePath": args.advanced_exe,
                "workingDir": working_dir,
                "delayFrames": 90,
                "outputPath": capture_a_base,
            },
            timeout=180.0,
        )
        capture_b = record_tool(
            client,
            report,
            "capture_frame",
            {
                "exePath": args.advanced_exe,
                "workingDir": working_dir,
                "delayFrames": 90,
                "outputPath": capture_b_base,
            },
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
        record_tool(client, report, "get_capture_info", {})
        list_events = record_tool(client, report, "list_events", {})
        list_draws = record_tool(client, report, "list_draws", {})

        draws = list_draws.get("draws", []) if isinstance(list_draws, dict) else []
        first_draw = draws[0]["eventId"] if len(draws) > 0 else None
        composite_draw = draws[2]["eventId"] if len(draws) > 2 else None
        overlay_draw = draws[3]["eventId"] if len(draws) > 3 else None

        if first_draw is not None:
            record_tool(client, report, "get_draw_info", {"eventId": first_draw})
            pass_attachments = record_tool(client, report, "get_pass_attachments", {"eventId": first_draw})
            report["scene_color_resource"] = first_color_target(pass_attachments)
            record_tool(client, report, "get_shader", {"eventId": first_draw, "stage": "vs", "mode": "reflect"})
            record_tool(client, report, "get_shader", {"eventId": first_draw, "stage": "vs", "mode": "disasm"})
            record_tool(client, report, "debug_vertex", {"eventId": first_draw, "vertexId": 0})

        if composite_draw is not None:
            pipeline_state = record_tool(client, report, "get_pipeline_state", {"eventId": composite_draw})
            width, height = render_target_size(pipeline_state)
            center_x = max(1, width // 2)
            center_y = max(1, height // 2)
            report["debug_pixel_composite_xy"] = [center_x, center_y]
            record_tool(client, report, "get_shader", {"eventId": composite_draw, "stage": "ps", "mode": "reflect"})
            record_tool(client, report, "debug_pixel", {"eventId": composite_draw, "x": center_x, "y": center_y})

            if overlay_draw is not None:
                overlay_x = max(1, int(width * 0.20))
                overlay_y = max(1, int(height * 0.25))
                report["debug_pixel_overlay_xy"] = [overlay_x, overlay_y]
                record_tool(client, report, "debug_pixel", {"eventId": overlay_draw, "x": overlay_x, "y": overlay_y})

        record_tool(client, report, "list_shaders", {})
        record_tool(client, report, "search_shaders", {"pattern": "main"})

        scene_color_resource = report.get("scene_color_resource")
        if scene_color_resource:
            record_tool(client, report, "get_texture_stats", {"resourceId": scene_color_resource})
            record_tool(client, report, "get_resource_usage", {"resourceId": scene_color_resource})
            record_tool(client, report, "export_texture", {"resourceId": scene_color_resource})

        record_tool(client, report, "diff_open", {"captureA": capture_a_path, "captureB": capture_b_path})
        diff_image = str(output_dir / "advanced_extended_diff.png")
        record_tool(client, report, "diff_summary", {})
        record_tool(client, report, "diff_draws", {})
        record_tool(client, report, "diff_resources", {})
        record_tool(client, report, "diff_framebuffer", {"diffOutput": diff_image})
        record_tool(client, report, "diff_close", {})

        report["summary"] = build_summary(report)

    finally:
        client.close()
        report["stderr"] = client.stderr_lines
        report["stdout_noise"] = client.stdout_noise
        report["returncode"] = client.proc.returncode if client.proc else None

    result_path = output_dir / "extended_mcp_checks.json"
    with result_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    print(str(result_path))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if not report["summary"]["failures"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run extended renderdoc-mcp checks against the advanced OpenGL sample.")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="Path to renderdoc-mcp.exe")
    parser.add_argument("--advanced-exe", default=DEFAULT_ADVANCED_EXE, help="Path to the advanced OpenGL test exe")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for captures and JSON results")
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
