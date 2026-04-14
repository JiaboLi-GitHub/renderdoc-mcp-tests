# renderdoc-mcp 测试仓库

[English Version](README.md)

这个仓库用于存放在 Windows 和 macOS 上验证 `renderdoc-mcp` 的跨平台测试资源、示例程序和测试记录。

当前内容主要覆盖 OpenGL。仓库名称保持更通用，是为了后续继续加入 Vulkan 等其他图形后端的测试。

## 包含内容

- `src/renderdoc_mcp_opengl_smoke.cpp`
  - 最小 OpenGL 冒烟样例（Windows，WGL），用于基础的抓帧和分析链路验证
- `src/renderdoc_mcp_opengl_smoke_macos.mm`
  - macOS 移植版冒烟样例（Cocoa + NSOpenGLView，OpenGL 4.1 Core Profile），支持 RenderDoc 应用内 API 自捕获
- `src/renderdoc_mcp_opengl_advanced.cpp`
  - 更复杂的 OpenGL 样例，覆盖离屏 FBO、深度测试、多纹理采样、alpha blending 和 uniform buffer
- `src/renderdoc_mcp_vulkan_advanced.cpp`
  - Vulkan 高级测试样例（仅限 Windows）
- `CMakeLists.txt`
  - 跨平台构建配置，包含 APPLE/WIN32 平台分支
- `renderdoc-mcp-test-report.md`
  - 记录测试范围、问题发现、根因说明和重装回归结论的测试报告

## 仓库结构

- `src/`
  - 用于生成可复现 capture 的测试样例源码
- `scripts/`
  - 可复用的 `renderdoc-mcp` stdio 回归测试脚本
  - `run_extended_mcp_checks.py` — 扩展工具覆盖（Windows）
  - `run_full_coverage_checks.py` — 40+ 工具全覆盖（Windows）
  - `run_vulkan_mcp_checks.py` — Vulkan 专项检查（Windows）
  - `run_macos_checks.py` — macOS 平台检查（协议、会话、错误处理）
- `renderdoc-mcp-test-report.md`
  - 汇总执行记录和回归结果
- `build/`
  - 本地生成的构建输出，已加入 git 忽略
- `artifacts/`
  - 本地抓帧文件和导出结果，已加入 git 忽略

## 构建方式

### Windows

```powershell
cmake -S . -B build
cmake --build build --config Release
```

生成的可执行文件位于 `build/bin/Release/`。

### macOS

需要通过 Homebrew 安装 CMake。

```bash
cmake -B build
cmake --build build
```

生成的可执行文件位于 `build/bin/`。

## 运行测试

### Windows

```powershell
python scripts/run_extended_mcp_checks.py --server <renderdoc-mcp.exe路径> --advanced-exe <advanced测试程序路径>
python scripts/run_full_coverage_checks.py --server <renderdoc-mcp.exe路径> --advanced-exe <advanced测试程序路径>
```

### macOS

```bash
python3 scripts/run_macos_checks.py \
  --server ~/Developer/renderdoc-mcp/build/renderdoc-mcp \
  --smoke-exe ./build/bin/renderdoc_mcp_opengl_smoke \
  --renderdoc-lib-dir ~/Developer/renderdoc/build/lib
```

## 目标

这个仓库的目标是为 `renderdoc-mcp` 提供一组可复现的本地测试夹具，用于验证和回归检查以下能力：

- 帧捕获（frame capture）
- 捕获元数据检查（capture metadata inspection）
- 绘制调用和 Pass 枚举（draw and pass enumeration）
- 管线和绑定检查（pipeline and binding inspection）
- Shader 反射（shader reflection）
- 渲染目标导出（render target export）
- 像素历史和断言（pixel history and assertions）
- 资源和常量缓冲区分析（resource and constant-buffer analysis）

## 平台支持

| 功能 | Windows | macOS (Apple Silicon) |
|------|---------|----------------------|
| OpenGL 冒烟测试 | WGL + Core 3.3 | Cocoa + NSOpenGLView Core 4.1 |
| OpenGL 高级测试 | WGL + FBO/UBO/Blend | 尚未移植 |
| Vulkan 测试 | Win32 + Vulkan | 不支持 |
| RenderDoc 帧捕获 | 完全支持 | 不可用（见下方说明） |
| MCP 协议测试 | 全部（59 个工具） | 协议 + 会话 + 错误处理 |
| 依赖捕获的工具 | 全部（57 个工具） | 无捕获文件，无法测试 |

### macOS 捕获限制

RenderDoc 的 CGL 钩子（dyld `__interpose` 段）无法拦截 Apple Silicon 上的 OpenGL 调用。macOS 上 `GL_VERSION` 报告 `4.1 Metal`，即 OpenGL 通过 Metal 翻译层实现。RenderDoc 的 CGL 钩子无法拦截这种 Metal 后端的 OpenGL 路径，因此帧捕获（`capture_frame` 和应用内 API `StartFrameCapture`/`EndFrameCapture`）无法在 macOS 上生成有效的 `.rdc` 文件。
