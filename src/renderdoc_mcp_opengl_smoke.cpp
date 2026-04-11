#include <windows.h>
#include <gl/GL.h>

#include <array>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

using GLchar = char;
using GLintptr = ptrdiff_t;
using GLsizeiptr = ptrdiff_t;

#ifndef GL_ARRAY_BUFFER
#define GL_ARRAY_BUFFER 0x8892
#endif
#ifndef GL_STATIC_DRAW
#define GL_STATIC_DRAW 0x88E4
#endif
#ifndef GL_FRAGMENT_SHADER
#define GL_FRAGMENT_SHADER 0x8B30
#endif
#ifndef GL_VERTEX_SHADER
#define GL_VERTEX_SHADER 0x8B31
#endif
#ifndef GL_COMPILE_STATUS
#define GL_COMPILE_STATUS 0x8B81
#endif
#ifndef GL_LINK_STATUS
#define GL_LINK_STATUS 0x8B82
#endif
#ifndef GL_INFO_LOG_LENGTH
#define GL_INFO_LOG_LENGTH 0x8B84
#endif
#ifndef GL_TEXTURE0
#define GL_TEXTURE0 0x84C0
#endif
#ifndef GL_CLAMP_TO_EDGE
#define GL_CLAMP_TO_EDGE 0x812F
#endif
#ifndef GL_TEXTURE_WRAP_S
#define GL_TEXTURE_WRAP_S 0x2802
#endif
#ifndef GL_TEXTURE_WRAP_T
#define GL_TEXTURE_WRAP_T 0x2803
#endif
#ifndef GL_TEXTURE_MIN_FILTER
#define GL_TEXTURE_MIN_FILTER 0x2801
#endif
#ifndef GL_TEXTURE_MAG_FILTER
#define GL_TEXTURE_MAG_FILTER 0x2800
#endif
#ifndef GL_RGBA8
#define GL_RGBA8 0x8058
#endif
#ifndef GL_BGRA
#define GL_BGRA 0x80E1
#endif
#ifndef GL_FALSE
#define GL_FALSE 0
#endif
#ifndef GL_TRUE
#define GL_TRUE 1
#endif
#ifndef WGL_CONTEXT_MAJOR_VERSION_ARB
#define WGL_CONTEXT_MAJOR_VERSION_ARB 0x2091
#endif
#ifndef WGL_CONTEXT_MINOR_VERSION_ARB
#define WGL_CONTEXT_MINOR_VERSION_ARB 0x2092
#endif
#ifndef WGL_CONTEXT_PROFILE_MASK_ARB
#define WGL_CONTEXT_PROFILE_MASK_ARB 0x9126
#endif
#ifndef WGL_CONTEXT_CORE_PROFILE_BIT_ARB
#define WGL_CONTEXT_CORE_PROFILE_BIT_ARB 0x00000001
#endif

using PFNWGLCREATECONTEXTATTRIBSARBPROC = HGLRC(WINAPI *)(HDC, HGLRC, const int *);
using PFNGLGENBUFFERSPROC = void(APIENTRY *)(GLsizei, GLuint *);
using PFNGLBINDBUFFERPROC = void(APIENTRY *)(GLenum, GLuint);
using PFNGLBUFFERDATAPROC = void(APIENTRY *)(GLenum, GLsizeiptr, const void *, GLenum);
using PFNGLDELETEBUFFERSPROC = void(APIENTRY *)(GLsizei, const GLuint *);
using PFNGLGENVERTEXARRAYSPROC = void(APIENTRY *)(GLsizei, GLuint *);
using PFNGLBINDVERTEXARRAYPROC = void(APIENTRY *)(GLuint);
using PFNGLDELETEVERTEXARRAYSPROC = void(APIENTRY *)(GLsizei, const GLuint *);
using PFNGLVERTEXATTRIBPOINTERPROC = void(APIENTRY *)(GLuint, GLint, GLenum, GLboolean, GLsizei, const void *);
using PFNGLENABLEVERTEXATTRIBARRAYPROC = void(APIENTRY *)(GLuint);
using PFNGLCREATESHADERPROC = GLuint(APIENTRY *)(GLenum);
using PFNGLSHADERSOURCEPROC = void(APIENTRY *)(GLuint, GLsizei, const GLchar *const *, const GLint *);
using PFNGLCOMPILESHADERPROC = void(APIENTRY *)(GLuint);
using PFNGLGETSHADERIVPROC = void(APIENTRY *)(GLuint, GLenum, GLint *);
using PFNGLGETSHADERINFOLOGPROC = void(APIENTRY *)(GLuint, GLsizei, GLsizei *, GLchar *);
using PFNGLDELETESHADERPROC = void(APIENTRY *)(GLuint);
using PFNGLCREATEPROGRAMPROC = GLuint(APIENTRY *)(void);
using PFNGLATTACHSHADERPROC = void(APIENTRY *)(GLuint, GLuint);
using PFNGLLINKPROGRAMPROC = void(APIENTRY *)(GLuint);
using PFNGLGETPROGRAMIVPROC = void(APIENTRY *)(GLuint, GLenum, GLint *);
using PFNGLGETPROGRAMINFOLOGPROC = void(APIENTRY *)(GLuint, GLsizei, GLsizei *, GLchar *);
using PFNGLUSEPROGRAMPROC = void(APIENTRY *)(GLuint);
using PFNGLDELETEPROGRAMPROC = void(APIENTRY *)(GLuint);
using PFNGLACTIVETEXTUREPROC = void(APIENTRY *)(GLenum);
using PFNGLGETUNIFORMLOCATIONPROC = GLint(APIENTRY *)(GLuint, const GLchar *);
using PFNGLUNIFORM1IPROC = void(APIENTRY *)(GLint, GLint);

static PFNGLGENBUFFERSPROC glGenBuffersFn = nullptr;
static PFNGLBINDBUFFERPROC glBindBufferFn = nullptr;
static PFNGLBUFFERDATAPROC glBufferDataFn = nullptr;
static PFNGLDELETEBUFFERSPROC glDeleteBuffersFn = nullptr;
static PFNGLGENVERTEXARRAYSPROC glGenVertexArraysFn = nullptr;
static PFNGLBINDVERTEXARRAYPROC glBindVertexArrayFn = nullptr;
static PFNGLDELETEVERTEXARRAYSPROC glDeleteVertexArraysFn = nullptr;
static PFNGLVERTEXATTRIBPOINTERPROC glVertexAttribPointerFn = nullptr;
static PFNGLENABLEVERTEXATTRIBARRAYPROC glEnableVertexAttribArrayFn = nullptr;
static PFNGLCREATESHADERPROC glCreateShaderFn = nullptr;
static PFNGLSHADERSOURCEPROC glShaderSourceFn = nullptr;
static PFNGLCOMPILESHADERPROC glCompileShaderFn = nullptr;
static PFNGLGETSHADERIVPROC glGetShaderivFn = nullptr;
static PFNGLGETSHADERINFOLOGPROC glGetShaderInfoLogFn = nullptr;
static PFNGLDELETESHADERPROC glDeleteShaderFn = nullptr;
static PFNGLCREATEPROGRAMPROC glCreateProgramFn = nullptr;
static PFNGLATTACHSHADERPROC glAttachShaderFn = nullptr;
static PFNGLLINKPROGRAMPROC glLinkProgramFn = nullptr;
static PFNGLGETPROGRAMIVPROC glGetProgramivFn = nullptr;
static PFNGLGETPROGRAMINFOLOGPROC glGetProgramInfoLogFn = nullptr;
static PFNGLUSEPROGRAMPROC glUseProgramFn = nullptr;
static PFNGLDELETEPROGRAMPROC glDeleteProgramFn = nullptr;
static PFNGLACTIVETEXTUREPROC glActiveTextureFn = nullptr;
static PFNGLGETUNIFORMLOCATIONPROC glGetUniformLocationFn = nullptr;
static PFNGLUNIFORM1IPROC glUniform1iFn = nullptr;

static const char *kWindowClassName = "RenderDocMcpOpenGLSmokeWindow";

static void *GetOpenGLProcAddress(const char *name) {
    void *proc = reinterpret_cast<void *>(wglGetProcAddress(name));
    if (proc == nullptr || proc == reinterpret_cast<void *>(0x1) || proc == reinterpret_cast<void *>(0x2) ||
        proc == reinterpret_cast<void *>(0x3) || proc == reinterpret_cast<void *>(-1)) {
        static HMODULE module = GetModuleHandleA("opengl32.dll");
        proc = reinterpret_cast<void *>(GetProcAddress(module, name));
    }
    return proc;
}

static bool LoadModernGlFunctions() {
#define LOAD_GL_FN(name)                                                                                              \
    name##Fn = reinterpret_cast<decltype(name##Fn)>(GetOpenGLProcAddress(#name));                                    \
    if (!name##Fn) {                                                                                                  \
        std::printf("Missing GL function: %s\n", #name);                                                              \
        return false;                                                                                                 \
    }

    LOAD_GL_FN(glGenBuffers);
    LOAD_GL_FN(glBindBuffer);
    LOAD_GL_FN(glBufferData);
    LOAD_GL_FN(glDeleteBuffers);
    LOAD_GL_FN(glGenVertexArrays);
    LOAD_GL_FN(glBindVertexArray);
    LOAD_GL_FN(glDeleteVertexArrays);
    LOAD_GL_FN(glVertexAttribPointer);
    LOAD_GL_FN(glEnableVertexAttribArray);
    LOAD_GL_FN(glCreateShader);
    LOAD_GL_FN(glShaderSource);
    LOAD_GL_FN(glCompileShader);
    LOAD_GL_FN(glGetShaderiv);
    LOAD_GL_FN(glGetShaderInfoLog);
    LOAD_GL_FN(glDeleteShader);
    LOAD_GL_FN(glCreateProgram);
    LOAD_GL_FN(glAttachShader);
    LOAD_GL_FN(glLinkProgram);
    LOAD_GL_FN(glGetProgramiv);
    LOAD_GL_FN(glGetProgramInfoLog);
    LOAD_GL_FN(glUseProgram);
    LOAD_GL_FN(glDeleteProgram);
    LOAD_GL_FN(glActiveTexture);
    LOAD_GL_FN(glGetUniformLocation);
    LOAD_GL_FN(glUniform1i);

#undef LOAD_GL_FN
    return true;
}

static std::string GetShaderLog(GLuint shader) {
    GLint length = 0;
    glGetShaderivFn(shader, GL_INFO_LOG_LENGTH, &length);
    if (length <= 1) {
        return {};
    }

    std::vector<char> buffer(static_cast<size_t>(length), '\0');
    GLsizei written = 0;
    glGetShaderInfoLogFn(shader, length, &written, buffer.data());
    return std::string(buffer.data(), buffer.data() + written);
}

static std::string GetProgramLog(GLuint program) {
    GLint length = 0;
    glGetProgramivFn(program, GL_INFO_LOG_LENGTH, &length);
    if (length <= 1) {
        return {};
    }

    std::vector<char> buffer(static_cast<size_t>(length), '\0');
    GLsizei written = 0;
    glGetProgramInfoLogFn(program, length, &written, buffer.data());
    return std::string(buffer.data(), buffer.data() + written);
}

static GLuint CompileShader(GLenum type, const char *source) {
    GLuint shader = glCreateShaderFn(type);
    glShaderSourceFn(shader, 1, &source, nullptr);
    glCompileShaderFn(shader);

    GLint success = GL_FALSE;
    glGetShaderivFn(shader, GL_COMPILE_STATUS, &success);
    if (success != GL_TRUE) {
        std::string log = GetShaderLog(shader);
        std::printf("Shader compilation failed:\n%s\n", log.c_str());
        glDeleteShaderFn(shader);
        return 0;
    }

    return shader;
}

static GLuint LinkProgram(const char *vertexSource, const char *fragmentSource) {
    GLuint vertexShader = CompileShader(GL_VERTEX_SHADER, vertexSource);
    GLuint fragmentShader = CompileShader(GL_FRAGMENT_SHADER, fragmentSource);
    if (!vertexShader || !fragmentShader) {
        if (vertexShader) {
            glDeleteShaderFn(vertexShader);
        }
        if (fragmentShader) {
            glDeleteShaderFn(fragmentShader);
        }
        return 0;
    }

    GLuint program = glCreateProgramFn();
    glAttachShaderFn(program, vertexShader);
    glAttachShaderFn(program, fragmentShader);
    glLinkProgramFn(program);

    GLint success = GL_FALSE;
    glGetProgramivFn(program, GL_LINK_STATUS, &success);
    glDeleteShaderFn(vertexShader);
    glDeleteShaderFn(fragmentShader);

    if (success != GL_TRUE) {
        std::string log = GetProgramLog(program);
        std::printf("Program link failed:\n%s\n", log.c_str());
        glDeleteProgramFn(program);
        return 0;
    }

    return program;
}

struct ModernRenderer {
    GLuint solidProgram = 0;
    GLuint texturedProgram = 0;
    GLuint solidVao = 0;
    GLuint solidVbo = 0;
    GLuint texturedVao = 0;
    GLuint texturedVbo = 0;
    GLuint checkerTexture = 0;
    GLint texturedSamplerLocation = -1;

    bool Init() {
        if (!LoadModernGlFunctions()) {
            return false;
        }

        static const char *solidVertexShader = R"(
#version 330 core
layout(location = 0) in vec2 aPosition;
layout(location = 1) in vec3 aColor;
out vec3 vColor;
void main() {
    vColor = aColor;
    gl_Position = vec4(aPosition, 0.0, 1.0);
}
)";

        static const char *solidFragmentShader = R"(
#version 330 core
in vec3 vColor;
out vec4 fragColor;
void main() {
    fragColor = vec4(vColor, 1.0);
}
)";

        static const char *texturedVertexShader = R"(
#version 330 core
layout(location = 0) in vec2 aPosition;
layout(location = 1) in vec2 aTexCoord;
out vec2 vTexCoord;
void main() {
    vTexCoord = aTexCoord;
    gl_Position = vec4(aPosition, 0.0, 1.0);
}
)";

        static const char *texturedFragmentShader = R"(
#version 330 core
in vec2 vTexCoord;
uniform sampler2D uTexture;
out vec4 fragColor;
void main() {
    fragColor = texture(uTexture, vTexCoord);
}
)";

        solidProgram = LinkProgram(solidVertexShader, solidFragmentShader);
        texturedProgram = LinkProgram(texturedVertexShader, texturedFragmentShader);
        if (!solidProgram || !texturedProgram) {
            return false;
        }

        const std::array<float, 15> solidVertices = {
            -0.85f, -0.55f, 1.0f, 0.2f, 0.2f,
            -0.15f, -0.55f, 0.2f, 1.0f, 0.3f,
            -0.50f,  0.30f, 0.2f, 0.4f, 1.0f,
        };

        const std::array<float, 24> texturedVertices = {
             0.10f, -0.60f, 0.0f, 0.0f,
             0.80f, -0.60f, 1.0f, 0.0f,
             0.80f,  0.20f, 1.0f, 1.0f,

             0.10f, -0.60f, 0.0f, 0.0f,
             0.80f,  0.20f, 1.0f, 1.0f,
             0.10f,  0.20f, 0.0f, 1.0f,
        };

        glGenVertexArraysFn(1, &solidVao);
        glBindVertexArrayFn(solidVao);
        glGenBuffersFn(1, &solidVbo);
        glBindBufferFn(GL_ARRAY_BUFFER, solidVbo);
        glBufferDataFn(GL_ARRAY_BUFFER, static_cast<GLsizeiptr>(solidVertices.size() * sizeof(float)),
                       solidVertices.data(), GL_STATIC_DRAW);
        glEnableVertexAttribArrayFn(0);
        glVertexAttribPointerFn(0, 2, GL_FLOAT, GL_FALSE, 5 * sizeof(float), reinterpret_cast<void *>(0));
        glEnableVertexAttribArrayFn(1);
        glVertexAttribPointerFn(1, 3, GL_FLOAT, GL_FALSE, 5 * sizeof(float), reinterpret_cast<void *>(2 * sizeof(float)));

        glGenVertexArraysFn(1, &texturedVao);
        glBindVertexArrayFn(texturedVao);
        glGenBuffersFn(1, &texturedVbo);
        glBindBufferFn(GL_ARRAY_BUFFER, texturedVbo);
        glBufferDataFn(GL_ARRAY_BUFFER, static_cast<GLsizeiptr>(texturedVertices.size() * sizeof(float)),
                       texturedVertices.data(), GL_STATIC_DRAW);
        glEnableVertexAttribArrayFn(0);
        glVertexAttribPointerFn(0, 2, GL_FLOAT, GL_FALSE, 4 * sizeof(float), reinterpret_cast<void *>(0));
        glEnableVertexAttribArrayFn(1);
        glVertexAttribPointerFn(1, 2, GL_FLOAT, GL_FALSE, 4 * sizeof(float), reinterpret_cast<void *>(2 * sizeof(float)));

        glBindVertexArrayFn(0);
        glBindBufferFn(GL_ARRAY_BUFFER, 0);

        const std::array<unsigned char, 4 * 4 * 4> pixels = {
            255,  64,  64, 255,   32,  32,  32, 255,  255, 255,  64, 255,   32,  32,  32, 255,
             32,  32,  32, 255,  255, 160,  64, 255,   32,  32,  32, 255,   64, 224, 255, 255,
            255, 255,  64, 255,   32,  32,  32, 255,   64, 255, 128, 255,   32,  32,  32, 255,
             32,  32,  32, 255,   64, 224, 255, 255,   32,  32,  32, 255,  255,  64, 160, 255,
        };

        glGenTextures(1, &checkerTexture);
        glBindTexture(GL_TEXTURE_2D, checkerTexture);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, 4, 4, 0, GL_RGBA, GL_UNSIGNED_BYTE, pixels.data());
        glBindTexture(GL_TEXTURE_2D, 0);

        texturedSamplerLocation = glGetUniformLocationFn(texturedProgram, "uTexture");
        return texturedSamplerLocation >= 0;
    }

    void Render(int width, int height) const {
        glViewport(0, 0, width, height);
        glClearColor(0.08f, 0.10f, 0.18f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);

        glUseProgramFn(solidProgram);
        glBindVertexArrayFn(solidVao);
        glDrawArrays(GL_TRIANGLES, 0, 3);

        glUseProgramFn(texturedProgram);
        glActiveTextureFn(GL_TEXTURE0);
        glBindTexture(GL_TEXTURE_2D, checkerTexture);
        glUniform1iFn(texturedSamplerLocation, 0);
        glBindVertexArrayFn(texturedVao);
        glDrawArrays(GL_TRIANGLES, 0, 6);

        glBindVertexArrayFn(0);
        glUseProgramFn(0);
    }

    void Shutdown() {
        if (checkerTexture) {
            glDeleteTextures(1, &checkerTexture);
            checkerTexture = 0;
        }
        if (solidVbo) {
            glDeleteBuffersFn(1, &solidVbo);
            solidVbo = 0;
        }
        if (texturedVbo) {
            glDeleteBuffersFn(1, &texturedVbo);
            texturedVbo = 0;
        }
        if (solidVao) {
            glDeleteVertexArraysFn(1, &solidVao);
            solidVao = 0;
        }
        if (texturedVao) {
            glDeleteVertexArraysFn(1, &texturedVao);
            texturedVao = 0;
        }
        if (solidProgram) {
            glDeleteProgramFn(solidProgram);
            solidProgram = 0;
        }
        if (texturedProgram) {
            glDeleteProgramFn(texturedProgram);
            texturedProgram = 0;
        }
    }
};

struct LegacyRenderer {
    GLuint checkerTexture = 0;

    bool Init() {
        const std::array<unsigned char, 4 * 4 * 4> pixels = {
            255,  80,  80, 255,   32,  32,  32, 255,  255, 255,  80, 255,   32,  32,  32, 255,
             32,  32,  32, 255,  255, 176,  80, 255,   32,  32,  32, 255,   80, 224, 255, 255,
            255, 255,  80, 255,   32,  32,  32, 255,   80, 255, 128, 255,   32,  32,  32, 255,
             32,  32,  32, 255,   80, 224, 255, 255,   32,  32,  32, 255,  255,  80, 160, 255,
        };

        glGenTextures(1, &checkerTexture);
        glBindTexture(GL_TEXTURE_2D, checkerTexture);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 4, 4, 0, GL_RGBA, GL_UNSIGNED_BYTE, pixels.data());
        glBindTexture(GL_TEXTURE_2D, 0);
        return true;
    }

    void Render(int width, int height) const {
        glViewport(0, 0, width, height);
        glClearColor(0.15f, 0.12f, 0.16f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);

        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();

        glDisable(GL_TEXTURE_2D);
        glBegin(GL_TRIANGLES);
        glColor3f(1.0f, 0.25f, 0.25f);
        glVertex2f(-0.85f, -0.55f);
        glColor3f(0.25f, 1.0f, 0.30f);
        glVertex2f(-0.15f, -0.55f);
        glColor3f(0.25f, 0.45f, 1.0f);
        glVertex2f(-0.50f, 0.30f);
        glEnd();

        glEnable(GL_TEXTURE_2D);
        glBindTexture(GL_TEXTURE_2D, checkerTexture);
        glColor3f(1.0f, 1.0f, 1.0f);
        glBegin(GL_TRIANGLES);
        glTexCoord2f(0.0f, 0.0f);
        glVertex2f(0.10f, -0.60f);
        glTexCoord2f(1.0f, 0.0f);
        glVertex2f(0.80f, -0.60f);
        glTexCoord2f(1.0f, 1.0f);
        glVertex2f(0.80f, 0.20f);

        glTexCoord2f(0.0f, 0.0f);
        glVertex2f(0.10f, -0.60f);
        glTexCoord2f(1.0f, 1.0f);
        glVertex2f(0.80f, 0.20f);
        glTexCoord2f(0.0f, 1.0f);
        glVertex2f(0.10f, 0.20f);
        glEnd();

        glBindTexture(GL_TEXTURE_2D, 0);
    }

    void Shutdown() {
        if (checkerTexture) {
            glDeleteTextures(1, &checkerTexture);
            checkerTexture = 0;
        }
    }
};

struct AppContext {
    HWND window = nullptr;
    HDC deviceContext = nullptr;
    HGLRC glContext = nullptr;
    bool modern = false;
    ModernRenderer modernRenderer;
    LegacyRenderer legacyRenderer;
};

static LRESULT CALLBACK WindowProc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam) {
    switch (msg) {
    case WM_CLOSE:
        DestroyWindow(hwnd);
        return 0;
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    default:
        return DefWindowProcA(hwnd, msg, wparam, lparam);
    }
}

static bool CreateOpenGLWindow(AppContext &app) {
    WNDCLASSA wc = {};
    wc.style = CS_OWNDC;
    wc.lpfnWndProc = WindowProc;
    wc.hInstance = GetModuleHandleA(nullptr);
    wc.lpszClassName = kWindowClassName;

    if (!RegisterClassA(&wc)) {
        const DWORD error = GetLastError();
        if (error != ERROR_CLASS_ALREADY_EXISTS) {
            std::printf("RegisterClassA failed: %lu\n", error);
            return false;
        }
    }

    app.window = CreateWindowExA(0, kWindowClassName, "RenderDoc MCP OpenGL Smoke Test",
                                 WS_OVERLAPPEDWINDOW | WS_VISIBLE, CW_USEDEFAULT, CW_USEDEFAULT, 960, 640, nullptr,
                                 nullptr, wc.hInstance, nullptr);
    if (!app.window) {
        std::printf("CreateWindowExA failed: %lu\n", GetLastError());
        return false;
    }

    app.deviceContext = GetDC(app.window);
    if (!app.deviceContext) {
        std::printf("GetDC failed: %lu\n", GetLastError());
        return false;
    }

    PIXELFORMATDESCRIPTOR pfd = {};
    pfd.nSize = sizeof(pfd);
    pfd.nVersion = 1;
    pfd.dwFlags = PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER;
    pfd.iPixelType = PFD_TYPE_RGBA;
    pfd.cColorBits = 32;
    pfd.cDepthBits = 24;
    pfd.iLayerType = PFD_MAIN_PLANE;

    const int pixelFormat = ChoosePixelFormat(app.deviceContext, &pfd);
    if (pixelFormat == 0) {
        std::printf("ChoosePixelFormat failed: %lu\n", GetLastError());
        return false;
    }

    if (!SetPixelFormat(app.deviceContext, pixelFormat, &pfd)) {
        std::printf("SetPixelFormat failed: %lu\n", GetLastError());
        return false;
    }

    HGLRC legacyContext = wglCreateContext(app.deviceContext);
    if (!legacyContext) {
        std::printf("wglCreateContext failed: %lu\n", GetLastError());
        return false;
    }

    if (!wglMakeCurrent(app.deviceContext, legacyContext)) {
        std::printf("wglMakeCurrent failed: %lu\n", GetLastError());
        wglDeleteContext(legacyContext);
        return false;
    }

    auto createContextAttribs = reinterpret_cast<PFNWGLCREATECONTEXTATTRIBSARBPROC>(
        GetOpenGLProcAddress("wglCreateContextAttribsARB"));
    if (createContextAttribs) {
        const int attribs[] = {
            WGL_CONTEXT_MAJOR_VERSION_ARB, 3,
            WGL_CONTEXT_MINOR_VERSION_ARB, 3,
            WGL_CONTEXT_PROFILE_MASK_ARB, WGL_CONTEXT_CORE_PROFILE_BIT_ARB,
            0
        };
        HGLRC modernContext = createContextAttribs(app.deviceContext, nullptr, attribs);
        if (modernContext) {
            wglMakeCurrent(nullptr, nullptr);
            wglDeleteContext(legacyContext);
            if (!wglMakeCurrent(app.deviceContext, modernContext)) {
                std::printf("Failed to activate modern OpenGL context.\n");
                wglDeleteContext(modernContext);
                return false;
            }
            app.glContext = modernContext;
            app.modern = true;
            return true;
        }
    }

    app.glContext = legacyContext;
    app.modern = false;
    return true;
}

static void DestroyOpenGLWindow(AppContext &app) {
    if (app.glContext) {
        wglMakeCurrent(nullptr, nullptr);
        wglDeleteContext(app.glContext);
        app.glContext = nullptr;
    }

    if (app.deviceContext && app.window) {
        ReleaseDC(app.window, app.deviceContext);
        app.deviceContext = nullptr;
    }

    if (app.window) {
        DestroyWindow(app.window);
        app.window = nullptr;
    }
}

int main() {
    AppContext app;
    if (!CreateOpenGLWindow(app)) {
        DestroyOpenGLWindow(app);
        return 1;
    }

    const char *version = reinterpret_cast<const char *>(glGetString(GL_VERSION));
    const char *renderer = reinterpret_cast<const char *>(glGetString(GL_RENDERER));
    std::printf("GL_VERSION=%s\n", version ? version : "<unknown>");
    std::printf("GL_RENDERER=%s\n", renderer ? renderer : "<unknown>");
    std::printf("Renderer path=%s\n", app.modern ? "modern-shader" : "legacy-fixed-function");

    bool initOk = app.modern ? app.modernRenderer.Init() : app.legacyRenderer.Init();
    if (!initOk) {
        std::printf("Renderer initialization failed.\n");
        DestroyOpenGLWindow(app);
        return 2;
    }

    ShowWindow(app.window, SW_SHOW);
    UpdateWindow(app.window);

    MSG message = {};
    bool running = true;
    int frameCount = 0;
    const int maxFrames = 240;

    while (running && frameCount < maxFrames) {
        while (PeekMessageA(&message, nullptr, 0, 0, PM_REMOVE)) {
            if (message.message == WM_QUIT) {
                running = false;
                break;
            }
            TranslateMessage(&message);
            DispatchMessageA(&message);
        }

        if (!running) {
            break;
        }

        RECT rect = {};
        GetClientRect(app.window, &rect);
        const int width = rect.right - rect.left;
        const int height = rect.bottom - rect.top;

        if (app.modern) {
            app.modernRenderer.Render(width, height);
        } else {
            app.legacyRenderer.Render(width, height);
        }

        SwapBuffers(app.deviceContext);
        Sleep(16);
        ++frameCount;
    }

    if (app.modern) {
        app.modernRenderer.Shutdown();
    } else {
        app.legacyRenderer.Shutdown();
    }

    DestroyOpenGLWindow(app);
    std::printf("Completed %d frames.\n", frameCount);
    return 0;
}
