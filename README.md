# renderdoc-mcp Tests

This repository contains local test assets, sample programs, and test notes for validating `renderdoc-mcp` on Windows.

The current coverage is focused on OpenGL. The repository is intentionally named more broadly so additional backends such as Vulkan can be added later.

## Included

- `src/renderdoc_mcp_opengl_smoke.cpp`
  - minimal OpenGL smoke sample used for baseline MCP capture and analysis checks
- `src/renderdoc_mcp_opengl_advanced.cpp`
  - richer OpenGL sample covering offscreen FBO rendering, depth testing, multi-texture sampling, alpha blending, and uniform buffers
- `CMakeLists.txt`
  - build configuration for the OpenGL samples
- `renderdoc-mcp-test-report.md`
  - test report capturing scenario coverage, findings, and retest notes

## Repository Layout

- `src/`
  - test sample sources used to generate reproducible captures
- `renderdoc-mcp-test-report.md`
  - consolidated execution notes and regression results
- `build/`
  - local generated build output, ignored from git
- `artifacts/`
  - local captures and exported images, ignored from git

## Build

```powershell
cmake -S . -B build
cmake --build build --config Release
```

Executables are emitted under `build/bin/Release/`.

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
