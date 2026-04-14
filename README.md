# renderdoc-mcp Tests

[中文版本](README-CN.md)

This repository contains cross-platform test assets, sample programs, and test notes for validating `renderdoc-mcp` on Windows and macOS.

The current coverage is focused on OpenGL. The repository is intentionally named more broadly so additional backends such as Vulkan can be added later.

## Included

- `src/renderdoc_mcp_opengl_smoke.cpp`
  - minimal OpenGL smoke sample (Windows, WGL) used for baseline MCP capture and analysis checks
- `src/renderdoc_mcp_opengl_smoke_macos.mm`
  - macOS port of the smoke sample (Cocoa + NSOpenGLView, OpenGL 4.1 Core Profile) with RenderDoc in-app API self-capture support
- `src/renderdoc_mcp_opengl_advanced.cpp`
  - richer OpenGL sample covering offscreen FBO rendering, depth testing, multi-texture sampling, alpha blending, and uniform buffers
- `src/renderdoc_mcp_vulkan_advanced.cpp`
  - Vulkan advanced sample (Windows only)
- `CMakeLists.txt`
  - cross-platform build configuration with APPLE/WIN32 platform guards
- `renderdoc-mcp-test-report.md`
  - test report covering scenario coverage, findings, root-cause notes, and reinstall retest results

## Repository Layout

- `src/`
  - test sample sources used to generate reproducible captures
- `scripts/`
  - reusable stdio-driven regression scripts for renderdoc-mcp tool checks
  - `run_extended_mcp_checks.py` — extended tool coverage (Windows)
  - `run_full_coverage_checks.py` — full coverage of 40+ tools (Windows)
  - `run_vulkan_mcp_checks.py` — Vulkan-specific checks (Windows)
  - `run_macos_checks.py` — macOS platform checks (protocol, session, error handling)
- `renderdoc-mcp-test-report.md`
  - consolidated execution notes and regression results
- `build/`
  - local generated build output, ignored from git
- `artifacts/`
  - local captures and exported images, ignored from git

## Build

### Windows

```powershell
cmake -S . -B build
cmake --build build --config Release
```

Executables are emitted under `build/bin/Release/`.

### macOS

Requires Homebrew with CMake installed.

```bash
cmake -B build
cmake --build build
```

Executables are emitted under `build/bin/`.

## Running Tests

### Windows

```powershell
python scripts/run_extended_mcp_checks.py --server <path-to-renderdoc-mcp.exe> --advanced-exe <path-to-advanced.exe>
python scripts/run_full_coverage_checks.py --server <path-to-renderdoc-mcp.exe> --advanced-exe <path-to-advanced.exe>
```

### macOS

```bash
python3 scripts/run_macos_checks.py \
  --server ~/Developer/renderdoc-mcp/build/renderdoc-mcp \
  --smoke-exe ./build/bin/renderdoc_mcp_opengl_smoke \
  --renderdoc-lib-dir ~/Developer/renderdoc/build/lib
```

## Purpose

The goal of this repository is to provide reproducible local fixtures for testing and regression-checking `renderdoc-mcp` features such as:

- frame capture
- capture metadata inspection
- draw and pass enumeration
- pipeline and binding inspection
- shader reflection
- render target export
- pixel history and assertions
- resource and constant-buffer analysis

## Platform Support

| Feature | Windows | macOS (Apple Silicon) |
|---------|---------|----------------------|
| OpenGL smoke test | WGL + Core 3.3 | Cocoa + NSOpenGLView Core 4.1 |
| OpenGL advanced test | WGL + FBO/UBO/Blend | Not yet ported |
| Vulkan test | Win32 + Vulkan | Not supported |
| RenderDoc frame capture | Full support | Not available (see below) |
| MCP protocol tests | Full (59 tools) | Protocol + session + error handling |
| Capture-dependent tools | Full (57 tools) | Not testable without capture |

### macOS Capture Limitation

RenderDoc's CGL interposing (dyld `__interpose` section) does not intercept OpenGL calls on Apple Silicon where `GL_VERSION` reports `4.1 Metal`. macOS implements OpenGL as a translation layer over Metal, and RenderDoc's CGL hooks cannot intercept this Metal-backed OpenGL path. This means frame capture (`capture_frame` and in-app API `StartFrameCapture`/`EndFrameCapture`) does not produce valid `.rdc` files on macOS.
