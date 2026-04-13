# renderdoc-mcp 测试仓库

[English Version](README.md)

这个仓库用于存放在 Windows 上验证 `renderdoc-mcp` 的本地测试资源、示例程序和测试记录。

当前内容主要覆盖 OpenGL。仓库名称保持更通用，是为了后续继续加入 Vulkan 等其他图形后端的测试。

## 包含内容

- `src/renderdoc_mcp_opengl_smoke.cpp`
  - 最小 OpenGL 冒烟样例，用于基础的抓帧和分析链路验证
- `src/renderdoc_mcp_opengl_advanced.cpp`
  - 更复杂的 OpenGL 样例，覆盖离屏 FBO、深度测试、多纹理采样、alpha blending 和 uniform buffer
- `CMakeLists.txt`
  - OpenGL 测试样例的构建配置
- `renderdoc-mcp-test-report.md`
  - 记录测试范围、发现结果和回归验证结论的测试报告

## 仓库结构

- `src/`
  - 用于生成可复现 capture 的测试样例源码
- `renderdoc-mcp-test-report.md`
  - 汇总执行记录和回归结果
- `build/`
  - 本地生成的构建输出，已加入 git 忽略
- `artifacts/`
  - 本地抓帧文件和导出结果，已加入 git 忽略

## 构建方式

```powershell
cmake -S . -B build
cmake --build build --config Release
```

生成的可执行文件位于 `build/bin/Release/`。

## 目标

这个仓库的目标是为 `renderdoc-mcp` 提供一组可复现的本地测试夹具，用于验证和回归检查以下能力：

- frame capture
- capture metadata inspection
- draw and pass enumeration
- pipeline and binding inspection
- shader reflection
- render target export
- pixel history and assertions
- resource and constant-buffer analysis
