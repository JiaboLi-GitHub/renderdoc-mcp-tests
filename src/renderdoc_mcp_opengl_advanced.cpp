#include <windows.h>
#include <gl/GL.h>

#include <array>
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
#ifndef GL_DYNAMIC_DRAW
#define GL_DYNAMIC_DRAW 0x88E8
#endif
#ifndef GL_UNIFORM_BUFFER
#define GL_UNIFORM_BUFFER 0x8A11
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
#ifndef GL_TEXTURE1
#define GL_TEXTURE1 0x84C1
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
#ifndef GL_FRAMEBUFFER
#define GL_FRAMEBUFFER 0x8D40
#endif
#ifndef GL_COLOR_ATTACHMENT0
#define GL_COLOR_ATTACHMENT0 0x8CE0
#endif
#ifndef GL_DEPTH_STENCIL_ATTACHMENT
#define GL_DEPTH_STENCIL_ATTACHMENT 0x821A
#endif
#ifndef GL_RENDERBUFFER
#define GL_RENDERBUFFER 0x8D41
#endif
#ifndef GL_DEPTH24_STENCIL8
#define GL_DEPTH24_STENCIL8 0x88F0
#endif
#ifndef GL_FRAMEBUFFER_COMPLETE
#define GL_FRAMEBUFFER_COMPLETE 0x8CD5
#endif
#ifndef GL_INVALID_INDEX
#define GL_INVALID_INDEX 0xFFFFFFFFu
#endif
#ifndef GL_FALSE
#define GL_FALSE 0
#endif
#ifndef GL_TRUE
#define GL_TRUE 1
#endif
#ifndef GL_NEAREST
#define GL_NEAREST 0x2600
#endif
#ifndef GL_LINEAR
#define GL_LINEAR 0x2601
#endif
#ifndef GL_BLEND
#define GL_BLEND 0x0BE2
#endif
#ifndef GL_SRC_ALPHA
#define GL_SRC_ALPHA 0x0302
#endif
#ifndef GL_ONE_MINUS_SRC_ALPHA
#define GL_ONE_MINUS_SRC_ALPHA 0x0303
#endif
#ifndef GL_DEPTH_TEST
#define GL_DEPTH_TEST 0x0B71
#endif
#ifndef GL_LEQUAL
#define GL_LEQUAL 0x0203
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
using PFNGLBUFFERSUBDATAPROC = void(APIENTRY *)(GLenum, GLintptr, GLsizeiptr, const void *);
using PFNGLDELETEBUFFERSPROC = void(APIENTRY *)(GLsizei, const GLuint *);
using PFNGLBINDBUFFERBASEPROC = void(APIENTRY *)(GLenum, GLuint, GLuint);
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
using PFNGLGETUNIFORMBLOCKINDEXPROC = GLuint(APIENTRY *)(GLuint, const GLchar *);
using PFNGLUNIFORMBLOCKBINDINGPROC = void(APIENTRY *)(GLuint, GLuint, GLuint);
using PFNGLGENFRAMEBUFFERSPROC = void(APIENTRY *)(GLsizei, GLuint *);
using PFNGLBINDFRAMEBUFFERPROC = void(APIENTRY *)(GLenum, GLuint);
using PFNGLFRAMEBUFFERTEXTURE2DPROC = void(APIENTRY *)(GLenum, GLenum, GLenum, GLuint, GLint);
using PFNGLCHECKFRAMEBUFFERSTATUSPROC = GLenum(APIENTRY *)(GLenum);
using PFNGLDELETEFRAMEBUFFERSPROC = void(APIENTRY *)(GLsizei, const GLuint *);
using PFNGLGENRENDERBUFFERSPROC = void(APIENTRY *)(GLsizei, GLuint *);
using PFNGLBINDRENDERBUFFERPROC = void(APIENTRY *)(GLenum, GLuint);
using PFNGLRENDERBUFFERSTORAGEPROC = void(APIENTRY *)(GLenum, GLenum, GLsizei, GLsizei);
using PFNGLFRAMEBUFFERRENDERBUFFERPROC = void(APIENTRY *)(GLenum, GLenum, GLenum, GLuint);
using PFNGLDELETERENDERBUFFERSPROC = void(APIENTRY *)(GLsizei, const GLuint *);

static PFNGLGENBUFFERSPROC glGenBuffersFn = nullptr;
static PFNGLBINDBUFFERPROC glBindBufferFn = nullptr;
static PFNGLBUFFERDATAPROC glBufferDataFn = nullptr;
static PFNGLBUFFERSUBDATAPROC glBufferSubDataFn = nullptr;
static PFNGLDELETEBUFFERSPROC glDeleteBuffersFn = nullptr;
static PFNGLBINDBUFFERBASEPROC glBindBufferBaseFn = nullptr;
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
static PFNGLGETUNIFORMBLOCKINDEXPROC glGetUniformBlockIndexFn = nullptr;
static PFNGLUNIFORMBLOCKBINDINGPROC glUniformBlockBindingFn = nullptr;
static PFNGLGENFRAMEBUFFERSPROC glGenFramebuffersFn = nullptr;
static PFNGLBINDFRAMEBUFFERPROC glBindFramebufferFn = nullptr;
static PFNGLFRAMEBUFFERTEXTURE2DPROC glFramebufferTexture2DFn = nullptr;
static PFNGLCHECKFRAMEBUFFERSTATUSPROC glCheckFramebufferStatusFn = nullptr;
static PFNGLDELETEFRAMEBUFFERSPROC glDeleteFramebuffersFn = nullptr;
static PFNGLGENRENDERBUFFERSPROC glGenRenderbuffersFn = nullptr;
static PFNGLBINDRENDERBUFFERPROC glBindRenderbufferFn = nullptr;
static PFNGLRENDERBUFFERSTORAGEPROC glRenderbufferStorageFn = nullptr;
static PFNGLFRAMEBUFFERRENDERBUFFERPROC glFramebufferRenderbufferFn = nullptr;
static PFNGLDELETERENDERBUFFERSPROC glDeleteRenderbuffersFn = nullptr;

static const char *kWindowClassName = "RenderDocMcpOpenGLAdvancedWindow";

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
    LOAD_GL_FN(glBufferSubData);
    LOAD_GL_FN(glDeleteBuffers);
    LOAD_GL_FN(glBindBufferBase);
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
    LOAD_GL_FN(glGetUniformBlockIndex);
    LOAD_GL_FN(glUniformBlockBinding);
    LOAD_GL_FN(glGenFramebuffers);
    LOAD_GL_FN(glBindFramebuffer);
    LOAD_GL_FN(glFramebufferTexture2D);
    LOAD_GL_FN(glCheckFramebufferStatus);
    LOAD_GL_FN(glDeleteFramebuffers);
    LOAD_GL_FN(glGenRenderbuffers);
    LOAD_GL_FN(glBindRenderbuffer);
    LOAD_GL_FN(glRenderbufferStorage);
    LOAD_GL_FN(glFramebufferRenderbuffer);
    LOAD_GL_FN(glDeleteRenderbuffers);

#undef LOAD_GL_FN
    return true;
}

static std::string GetShaderLog(GLuint shader);
static std::string GetProgramLog(GLuint program);
static GLuint CompileShader(GLenum type, const char *source);
static GLuint LinkProgram(const char *vertexSource, const char *fragmentSource);

struct Mat4 {
    float m[16];
};

static Mat4 Identity();
static Mat4 Multiply(const Mat4 &a, const Mat4 &b);
static Mat4 Translation(float x, float y, float z);
static Mat4 Scale(float x, float y, float z);
static Mat4 RotationZ(float radians);

struct SceneUniformData {
    float mvp[16];
    float tint[4];
};

struct AdvancedRenderer {
    GLuint sceneProgram = 0;
    GLuint compositeProgram = 0;
    GLuint overlayProgram = 0;
    GLuint quadVao = 0;
    GLuint quadVbo = 0;
    GLuint overlayVao = 0;
    GLuint overlayVbo = 0;
    GLuint checkerTexture = 0;
    GLuint lutTexture = 0;
    GLuint overlayTexture = 0;
    GLuint sceneFbo = 0;
    GLuint sceneColorTexture = 0;
    GLuint sceneDepthStencil = 0;
    GLuint sceneUbo = 0;
    GLint compositeSceneLocation = -1;
    GLint compositeLutLocation = -1;
    GLint overlayTextureLocation = -1;
    int offscreenWidth = 512;
    int offscreenHeight = 512;

    bool Init();
    bool CreateGeometry();
    bool CreateTextures();
    bool CreateFramebuffer();
    bool CreateUniformBuffer();
    void UpdateSceneUbo(const Mat4 &mvp, const std::array<float, 4> &tint) const;
    void Render(int width, int height) const;
    void RenderOffscreenPass() const;
    void RenderCompositePass(int width, int height) const;
    void RenderBlendPass(int width, int height) const;
    void Shutdown();
    static GLuint CreateTexture2D(int width, int height, const unsigned char *pixels, GLint minFilter, GLint magFilter);
};

struct AppContext {
    HWND window = nullptr;
    HDC deviceContext = nullptr;
    HGLRC glContext = nullptr;
    AdvancedRenderer renderer;
};

static LRESULT CALLBACK WindowProc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam);
static bool CreateOpenGLWindow(AppContext &app);
static void DestroyOpenGLWindow(AppContext &app);

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
    const GLuint shader = glCreateShaderFn(type);
    glShaderSourceFn(shader, 1, &source, nullptr);
    glCompileShaderFn(shader);

    GLint success = GL_FALSE;
    glGetShaderivFn(shader, GL_COMPILE_STATUS, &success);
    if (success != GL_TRUE) {
        const std::string log = GetShaderLog(shader);
        std::printf("Shader compilation failed:\n%s\n", log.c_str());
        glDeleteShaderFn(shader);
        return 0;
    }

    return shader;
}

static GLuint LinkProgram(const char *vertexSource, const char *fragmentSource) {
    const GLuint vertexShader = CompileShader(GL_VERTEX_SHADER, vertexSource);
    const GLuint fragmentShader = CompileShader(GL_FRAGMENT_SHADER, fragmentSource);
    if (!vertexShader || !fragmentShader) {
        if (vertexShader) {
            glDeleteShaderFn(vertexShader);
        }
        if (fragmentShader) {
            glDeleteShaderFn(fragmentShader);
        }
        return 0;
    }

    const GLuint program = glCreateProgramFn();
    glAttachShaderFn(program, vertexShader);
    glAttachShaderFn(program, fragmentShader);
    glLinkProgramFn(program);

    GLint success = GL_FALSE;
    glGetProgramivFn(program, GL_LINK_STATUS, &success);
    glDeleteShaderFn(vertexShader);
    glDeleteShaderFn(fragmentShader);

    if (success != GL_TRUE) {
        const std::string log = GetProgramLog(program);
        std::printf("Program link failed:\n%s\n", log.c_str());
        glDeleteProgramFn(program);
        return 0;
    }

    return program;
}

static Mat4 Identity() {
    return Mat4{{1.0f, 0.0f, 0.0f, 0.0f,
                 0.0f, 1.0f, 0.0f, 0.0f,
                 0.0f, 0.0f, 1.0f, 0.0f,
                 0.0f, 0.0f, 0.0f, 1.0f}};
}

static Mat4 Multiply(const Mat4 &a, const Mat4 &b) {
    Mat4 out = {};
    for (int col = 0; col < 4; ++col) {
        for (int row = 0; row < 4; ++row) {
            out.m[col * 4 + row] =
                a.m[0 * 4 + row] * b.m[col * 4 + 0] +
                a.m[1 * 4 + row] * b.m[col * 4 + 1] +
                a.m[2 * 4 + row] * b.m[col * 4 + 2] +
                a.m[3 * 4 + row] * b.m[col * 4 + 3];
        }
    }
    return out;
}

static Mat4 Translation(float x, float y, float z) {
    Mat4 out = Identity();
    out.m[12] = x;
    out.m[13] = y;
    out.m[14] = z;
    return out;
}

static Mat4 Scale(float x, float y, float z) {
    Mat4 out = {};
    out.m[0] = x;
    out.m[5] = y;
    out.m[10] = z;
    out.m[15] = 1.0f;
    return out;
}

static Mat4 RotationZ(float radians) {
    const float c = std::cos(radians);
    const float s = std::sin(radians);
    return Mat4{{c, s, 0.0f, 0.0f,
                -s, c, 0.0f, 0.0f,
                 0.0f, 0.0f, 1.0f, 0.0f,
                 0.0f, 0.0f, 0.0f, 1.0f}};
}

bool AdvancedRenderer::Init() {
    if (!LoadModernGlFunctions()) {
        return false;
    }

    static const char *sceneVertexShader = R"(
#version 330 core
layout(location = 0) in vec3 aPosition;
layout(location = 1) in vec2 aTexCoord;
layout(std140) uniform SceneData {
    mat4 uMvp;
    vec4 uTint;
};
out vec2 vTexCoord;
out vec4 vTint;
void main() {
    vTexCoord = aTexCoord;
    vTint = uTint;
    gl_Position = uMvp * vec4(aPosition, 1.0);
}
)";

    static const char *sceneFragmentShader = R"(
#version 330 core
in vec2 vTexCoord;
in vec4 vTint;
uniform sampler2D uBaseTexture;
out vec4 fragColor;
void main() {
    vec4 texel = texture(uBaseTexture, vTexCoord);
    fragColor = texel * vTint;
}
)";

    static const char *compositeVertexShader = R"(
#version 330 core
layout(location = 0) in vec3 aPosition;
layout(location = 1) in vec2 aTexCoord;
out vec2 vTexCoord;
void main() {
    vTexCoord = aTexCoord;
    gl_Position = vec4(aPosition.xy, 0.0, 1.0);
}
)";

    static const char *compositeFragmentShader = R"(
#version 330 core
in vec2 vTexCoord;
uniform sampler2D uSceneTexture;
uniform sampler2D uLutTexture;
out vec4 fragColor;
void main() {
    vec4 scene = texture(uSceneTexture, vTexCoord);
    vec4 lut = texture(uLutTexture, fract(vTexCoord * 4.0));
    float accent = smoothstep(0.20, 0.95, vTexCoord.x) * 0.42;
    vec3 mixedColor = mix(scene.rgb, scene.rgb * (0.70 + lut.rgb * 0.55), accent);
    fragColor = vec4(mixedColor, 1.0);
}
)";

    static const char *overlayVertexShader = R"(
#version 330 core
layout(location = 0) in vec3 aPosition;
layout(location = 1) in vec2 aTexCoord;
out vec2 vTexCoord;
void main() {
    vTexCoord = aTexCoord;
    gl_Position = vec4(aPosition.xy, 0.0, 1.0);
}
)";

    static const char *overlayFragmentShader = R"(
#version 330 core
in vec2 vTexCoord;
uniform sampler2D uOverlayTexture;
out vec4 fragColor;
void main() {
    vec4 texel = texture(uOverlayTexture, vTexCoord);
    fragColor = vec4(texel.rgb, texel.a * 0.85);
}
)";

    sceneProgram = LinkProgram(sceneVertexShader, sceneFragmentShader);
    compositeProgram = LinkProgram(compositeVertexShader, compositeFragmentShader);
    overlayProgram = LinkProgram(overlayVertexShader, overlayFragmentShader);
    if (!sceneProgram || !compositeProgram || !overlayProgram) {
        return false;
    }

    const GLuint sceneBlockIndex = glGetUniformBlockIndexFn(sceneProgram, "SceneData");
    if (sceneBlockIndex == GL_INVALID_INDEX) {
        std::printf("SceneData uniform block was not found.\n");
        return false;
    }
    glUniformBlockBindingFn(sceneProgram, sceneBlockIndex, 0);

    compositeSceneLocation = glGetUniformLocationFn(compositeProgram, "uSceneTexture");
    compositeLutLocation = glGetUniformLocationFn(compositeProgram, "uLutTexture");
    overlayTextureLocation = glGetUniformLocationFn(overlayProgram, "uOverlayTexture");
    if (compositeSceneLocation < 0 || compositeLutLocation < 0 || overlayTextureLocation < 0) {
        std::printf("Sampler uniform lookup failed.\n");
        return false;
    }

    return CreateGeometry() && CreateTextures() && CreateFramebuffer() && CreateUniformBuffer();
}

bool AdvancedRenderer::CreateGeometry() {
    const std::array<float, 30> quadVertices = {
        -0.5f, -0.5f, 0.0f, 0.0f, 0.0f,
         0.5f, -0.5f, 0.0f, 1.0f, 0.0f,
         0.5f,  0.5f, 0.0f, 1.0f, 1.0f,
        -0.5f, -0.5f, 0.0f, 0.0f, 0.0f,
         0.5f,  0.5f, 0.0f, 1.0f, 1.0f,
        -0.5f,  0.5f, 0.0f, 0.0f, 1.0f,
    };

    const std::array<float, 30> overlayVertices = {
        -0.85f,  0.15f, 0.0f, 0.0f, 0.0f,
        -0.05f,  0.15f, 0.0f, 1.0f, 0.0f,
        -0.05f,  0.88f, 0.0f, 1.0f, 1.0f,
        -0.85f,  0.15f, 0.0f, 0.0f, 0.0f,
        -0.05f,  0.88f, 0.0f, 1.0f, 1.0f,
        -0.85f,  0.88f, 0.0f, 0.0f, 1.0f,
    };

    glGenVertexArraysFn(1, &quadVao);
    glBindVertexArrayFn(quadVao);
    glGenBuffersFn(1, &quadVbo);
    glBindBufferFn(GL_ARRAY_BUFFER, quadVbo);
    glBufferDataFn(GL_ARRAY_BUFFER, static_cast<GLsizeiptr>(quadVertices.size() * sizeof(float)),
                   quadVertices.data(), GL_STATIC_DRAW);
    glEnableVertexAttribArrayFn(0);
    glVertexAttribPointerFn(0, 3, GL_FLOAT, GL_FALSE, 5 * sizeof(float), reinterpret_cast<void *>(0));
    glEnableVertexAttribArrayFn(1);
    glVertexAttribPointerFn(1, 2, GL_FLOAT, GL_FALSE, 5 * sizeof(float), reinterpret_cast<void *>(3 * sizeof(float)));

    glGenVertexArraysFn(1, &overlayVao);
    glBindVertexArrayFn(overlayVao);
    glGenBuffersFn(1, &overlayVbo);
    glBindBufferFn(GL_ARRAY_BUFFER, overlayVbo);
    glBufferDataFn(GL_ARRAY_BUFFER, static_cast<GLsizeiptr>(overlayVertices.size() * sizeof(float)),
                   overlayVertices.data(), GL_STATIC_DRAW);
    glEnableVertexAttribArrayFn(0);
    glVertexAttribPointerFn(0, 3, GL_FLOAT, GL_FALSE, 5 * sizeof(float), reinterpret_cast<void *>(0));
    glEnableVertexAttribArrayFn(1);
    glVertexAttribPointerFn(1, 2, GL_FLOAT, GL_FALSE, 5 * sizeof(float), reinterpret_cast<void *>(3 * sizeof(float)));

    glBindVertexArrayFn(0);
    glBindBufferFn(GL_ARRAY_BUFFER, 0);
    return true;
}

GLuint AdvancedRenderer::CreateTexture2D(int width, int height, const unsigned char *pixels, GLint minFilter, GLint magFilter) {
    GLuint texture = 0;
    glGenTextures(1, &texture);
    glBindTexture(GL_TEXTURE_2D, texture);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, minFilter);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, magFilter);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, pixels);
    glBindTexture(GL_TEXTURE_2D, 0);
    return texture;
}

bool AdvancedRenderer::CreateTextures() {
    const std::array<unsigned char, 4 * 4 * 4> checkerPixels = {
        255,  88,  80, 255,   24,  24,  24, 255, 255, 230,  96, 255,   24,  24,  24, 255,
         24,  24,  24, 255,   88, 255, 160, 255,  24,  24,  24, 255,  96, 224, 255, 255,
        255, 230,  96, 255,   24,  24,  24, 255, 255, 140,  72, 255,   24,  24,  24, 255,
         24,  24,  24, 255,   96, 224, 255, 255,  24,  24,  24, 255, 255,  88, 160, 255,
    };

    const std::array<unsigned char, 4 * 4 * 4> lutPixels = {
         70, 210, 245, 255, 255,  98, 192, 255, 255, 230,  70, 255,  60,  60,  60, 255,
        255, 180,  70, 255,  80, 255, 140, 255,  70, 115, 255, 255,  28,  28,  28, 255,
         60,  60,  60, 255, 255, 230,  70, 255,  80, 255, 140, 255, 255,  98, 192, 255,
         28,  28,  28, 255,  70, 115, 255, 255, 255, 180,  70, 255,  70, 210, 245, 255,
    };

    const std::array<unsigned char, 4 * 4 * 4> overlayPixels = {
        255, 255, 255, 220,   0,   0,   0,   0, 255, 255, 255, 160,   0,   0,   0,   0,
          0,   0,   0,   0, 255, 255, 255, 200,   0,   0,   0,   0, 255, 255, 255, 120,
        255, 255, 255, 180,   0,   0,   0,   0, 255, 255, 255, 220,   0,   0,   0,   0,
          0,   0,   0,   0, 255, 255, 255, 130,   0,   0,   0,   0, 255, 255, 255, 200,
    };

    checkerTexture = CreateTexture2D(4, 4, checkerPixels.data(), GL_NEAREST, GL_NEAREST);
    lutTexture = CreateTexture2D(4, 4, lutPixels.data(), GL_NEAREST, GL_NEAREST);
    overlayTexture = CreateTexture2D(4, 4, overlayPixels.data(), GL_NEAREST, GL_NEAREST);
    return checkerTexture != 0 && lutTexture != 0 && overlayTexture != 0;
}

bool AdvancedRenderer::CreateFramebuffer() {
    glGenTextures(1, &sceneColorTexture);
    glBindTexture(GL_TEXTURE_2D, sceneColorTexture);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, offscreenWidth, offscreenHeight, 0, GL_RGBA, GL_UNSIGNED_BYTE, nullptr);

    glGenRenderbuffersFn(1, &sceneDepthStencil);
    glBindRenderbufferFn(GL_RENDERBUFFER, sceneDepthStencil);
    glRenderbufferStorageFn(GL_RENDERBUFFER, GL_DEPTH24_STENCIL8, offscreenWidth, offscreenHeight);

    glGenFramebuffersFn(1, &sceneFbo);
    glBindFramebufferFn(GL_FRAMEBUFFER, sceneFbo);
    glFramebufferTexture2DFn(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, sceneColorTexture, 0);
    glFramebufferRenderbufferFn(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, sceneDepthStencil);
    const GLenum status = glCheckFramebufferStatusFn(GL_FRAMEBUFFER);
    glBindFramebufferFn(GL_FRAMEBUFFER, 0);
    glBindRenderbufferFn(GL_RENDERBUFFER, 0);
    glBindTexture(GL_TEXTURE_2D, 0);

    if (status != GL_FRAMEBUFFER_COMPLETE) {
        std::printf("Framebuffer was incomplete: 0x%04X\n", status);
        return false;
    }

    return true;
}

bool AdvancedRenderer::CreateUniformBuffer() {
    glGenBuffersFn(1, &sceneUbo);
    glBindBufferFn(GL_UNIFORM_BUFFER, sceneUbo);
    glBufferDataFn(GL_UNIFORM_BUFFER, sizeof(SceneUniformData), nullptr, GL_DYNAMIC_DRAW);
    glBindBufferBaseFn(GL_UNIFORM_BUFFER, 0, sceneUbo);
    glBindBufferFn(GL_UNIFORM_BUFFER, 0);
    return sceneUbo != 0;
}

void AdvancedRenderer::UpdateSceneUbo(const Mat4 &mvp, const std::array<float, 4> &tint) const {
    SceneUniformData data = {};
    std::memcpy(data.mvp, mvp.m, sizeof(data.mvp));
    std::memcpy(data.tint, tint.data(), sizeof(data.tint));
    glBindBufferFn(GL_UNIFORM_BUFFER, sceneUbo);
    glBufferSubDataFn(GL_UNIFORM_BUFFER, 0, sizeof(SceneUniformData), &data);
    glBindBufferFn(GL_UNIFORM_BUFFER, 0);
}

void AdvancedRenderer::Render(int width, int height) const {
    RenderOffscreenPass();
    RenderCompositePass(width, height);
    RenderBlendPass(width, height);
}

void AdvancedRenderer::RenderOffscreenPass() const {
    glBindFramebufferFn(GL_FRAMEBUFFER, sceneFbo);
    glViewport(0, 0, offscreenWidth, offscreenHeight);
    glEnable(GL_DEPTH_TEST);
    glDepthFunc(GL_LEQUAL);
    glDisable(GL_BLEND);
    glClearColor(0.07f, 0.11f, 0.09f, 1.0f);
    glClearDepth(1.0);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    glUseProgramFn(sceneProgram);
    glBindVertexArrayFn(quadVao);
    glActiveTextureFn(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, checkerTexture);
    glBindBufferBaseFn(GL_UNIFORM_BUFFER, 0, sceneUbo);
    glUniform1iFn(glGetUniformLocationFn(sceneProgram, "uBaseTexture"), 0);

    const Mat4 backMatrix = Multiply(Translation(-0.08f, -0.02f, 0.45f),
                                     Multiply(RotationZ(-0.18f), Scale(1.38f, 0.95f, 1.0f)));
    UpdateSceneUbo(backMatrix, {1.00f, 0.92f, 0.86f, 1.0f});
    glDrawArrays(GL_TRIANGLES, 0, 6);

    const Mat4 frontMatrix = Multiply(Translation(0.20f, 0.12f, 0.12f),
                                      Multiply(RotationZ(0.42f), Scale(0.82f, 0.82f, 1.0f)));
    UpdateSceneUbo(frontMatrix, {0.74f, 0.98f, 1.00f, 1.0f});
    glDrawArrays(GL_TRIANGLES, 0, 6);

    glBindTexture(GL_TEXTURE_2D, 0);
    glBindVertexArrayFn(0);
    glUseProgramFn(0);
    glBindFramebufferFn(GL_FRAMEBUFFER, 0);
}

void AdvancedRenderer::RenderCompositePass(int width, int height) const {
    glViewport(0, 0, width, height);
    glDisable(GL_DEPTH_TEST);
    glDisable(GL_BLEND);
    glClearColor(0.08f, 0.10f, 0.18f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);

    glUseProgramFn(compositeProgram);
    glBindVertexArrayFn(quadVao);
    glActiveTextureFn(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, sceneColorTexture);
    glUniform1iFn(compositeSceneLocation, 0);
    glActiveTextureFn(GL_TEXTURE1);
    glBindTexture(GL_TEXTURE_2D, lutTexture);
    glUniform1iFn(compositeLutLocation, 1);
    glDrawArrays(GL_TRIANGLES, 0, 6);

    glActiveTextureFn(GL_TEXTURE1);
    glBindTexture(GL_TEXTURE_2D, 0);
    glActiveTextureFn(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, 0);
    glBindVertexArrayFn(0);
    glUseProgramFn(0);
}

void AdvancedRenderer::RenderBlendPass(int width, int height) const {
    glViewport(0, 0, width, height);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glUseProgramFn(overlayProgram);
    glBindVertexArrayFn(overlayVao);
    glActiveTextureFn(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, overlayTexture);
    glUniform1iFn(overlayTextureLocation, 0);
    glDrawArrays(GL_TRIANGLES, 0, 6);
    glBindTexture(GL_TEXTURE_2D, 0);
    glBindVertexArrayFn(0);
    glUseProgramFn(0);
    glDisable(GL_BLEND);
}

void AdvancedRenderer::Shutdown() {
    if (sceneUbo) {
        glDeleteBuffersFn(1, &sceneUbo);
        sceneUbo = 0;
    }
    if (quadVbo) {
        glDeleteBuffersFn(1, &quadVbo);
        quadVbo = 0;
    }
    if (overlayVbo) {
        glDeleteBuffersFn(1, &overlayVbo);
        overlayVbo = 0;
    }
    if (quadVao) {
        glDeleteVertexArraysFn(1, &quadVao);
        quadVao = 0;
    }
    if (overlayVao) {
        glDeleteVertexArraysFn(1, &overlayVao);
        overlayVao = 0;
    }
    if (sceneProgram) {
        glDeleteProgramFn(sceneProgram);
        sceneProgram = 0;
    }
    if (compositeProgram) {
        glDeleteProgramFn(compositeProgram);
        compositeProgram = 0;
    }
    if (overlayProgram) {
        glDeleteProgramFn(overlayProgram);
        overlayProgram = 0;
    }
    if (checkerTexture) {
        glDeleteTextures(1, &checkerTexture);
        checkerTexture = 0;
    }
    if (lutTexture) {
        glDeleteTextures(1, &lutTexture);
        lutTexture = 0;
    }
    if (overlayTexture) {
        glDeleteTextures(1, &overlayTexture);
        overlayTexture = 0;
    }
    if (sceneColorTexture) {
        glDeleteTextures(1, &sceneColorTexture);
        sceneColorTexture = 0;
    }
    if (sceneDepthStencil) {
        glDeleteRenderbuffersFn(1, &sceneDepthStencil);
        sceneDepthStencil = 0;
    }
    if (sceneFbo) {
        glDeleteFramebuffersFn(1, &sceneFbo);
        sceneFbo = 0;
    }
}

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

    app.window = CreateWindowExA(0, kWindowClassName, "RenderDoc MCP OpenGL Advanced Test",
                                 WS_OVERLAPPEDWINDOW | WS_VISIBLE, CW_USEDEFAULT, CW_USEDEFAULT, 1024, 720, nullptr,
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
            return true;
        }
    }

    app.glContext = legacyContext;
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
    std::printf("Renderer path=advanced-fbo-depth-blend\n");

    if (!app.renderer.Init()) {
        std::printf("Advanced renderer initialization failed.\n");
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
        app.renderer.Render(width, height);
        SwapBuffers(app.deviceContext);
        Sleep(16);
        ++frameCount;
    }

    app.renderer.Shutdown();
    DestroyOpenGLWindow(app);
    std::printf("Completed %d frames.\n", frameCount);
    return 0;
}
