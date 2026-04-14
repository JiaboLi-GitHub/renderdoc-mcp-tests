// renderdoc_mcp_opengl_smoke_macos.mm
// macOS port of the OpenGL smoke test for renderdoc-mcp.
// Uses Cocoa + NSOpenGLView with OpenGL 4.1 Core Profile.
// Renders: colored triangle + textured checkerboard quad (2 draw calls).
// Auto-exits after 120 frames.
//
// If RENDERDOC_LIB_PATH env is set, loads librenderdoc.dylib and uses the
// in-application API to capture a single frame. The capture is saved to the
// path in RENDERDOC_CAPTURE_PATH (or /tmp/renderdoc_smoke_capture).

#import <Cocoa/Cocoa.h>
#include <OpenGL/gl3.h>
#include <OpenGL/OpenGL.h>
#include <dlfcn.h>

#include <array>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

// Minimal RenderDoc in-app API types (from renderdoc_app.h)
typedef void *RENDERDOC_DevicePointer;
typedef void *RENDERDOC_WindowHandle;
typedef void (*pRENDERDOC_SetCaptureFilePathTemplate)(const char *);
typedef void (*pRENDERDOC_StartFrameCapture)(RENDERDOC_DevicePointer, RENDERDOC_WindowHandle);
typedef uint32_t (*pRENDERDOC_EndFrameCapture)(RENDERDOC_DevicePointer, RENDERDOC_WindowHandle);
typedef void (*pRENDERDOC_GetAPIVersion)(int *, int *, int *);

struct RENDERDOC_API_1_0_0 {
    pRENDERDOC_GetAPIVersion GetAPIVersion;
    void *pad[10];
    pRENDERDOC_SetCaptureFilePathTemplate SetCaptureFilePathTemplate;
    void *pad2[4];
    pRENDERDOC_StartFrameCapture StartFrameCapture;
    void *pad3;
    pRENDERDOC_EndFrameCapture EndFrameCapture;
};

typedef int (*pRENDERDOC_GetAPI)(int version, void **outAPIPointers);

static RENDERDOC_API_1_0_0 *rdocAPI = nullptr;
static int gCaptureFrame = -1;  // frame number to capture (-1 = no capture)
static std::string gCapturePath;

#pragma clang diagnostic ignored "-Wdeprecated-declarations"

// ---------------------------------------------------------------------------
// Shader utilities
// ---------------------------------------------------------------------------

static std::string GetShaderLog(GLuint shader) {
    GLint length = 0;
    glGetShaderiv(shader, GL_INFO_LOG_LENGTH, &length);
    if (length <= 1) return {};
    std::vector<char> buf(static_cast<size_t>(length), '\0');
    GLsizei written = 0;
    glGetShaderInfoLog(shader, length, &written, buf.data());
    return std::string(buf.data(), buf.data() + written);
}

static std::string GetProgramLog(GLuint program) {
    GLint length = 0;
    glGetProgramiv(program, GL_INFO_LOG_LENGTH, &length);
    if (length <= 1) return {};
    std::vector<char> buf(static_cast<size_t>(length), '\0');
    GLsizei written = 0;
    glGetProgramInfoLog(program, length, &written, buf.data());
    return std::string(buf.data(), buf.data() + written);
}

static GLuint CompileShader(GLenum type, const char *source) {
    GLuint shader = glCreateShader(type);
    glShaderSource(shader, 1, &source, nullptr);
    glCompileShader(shader);
    GLint success = GL_FALSE;
    glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
    if (success != GL_TRUE) {
        std::printf("Shader compilation failed:\n%s\n", GetShaderLog(shader).c_str());
        glDeleteShader(shader);
        return 0;
    }
    return shader;
}

static GLuint LinkProgram(const char *vertSrc, const char *fragSrc) {
    GLuint vs = CompileShader(GL_VERTEX_SHADER, vertSrc);
    GLuint fs = CompileShader(GL_FRAGMENT_SHADER, fragSrc);
    if (!vs || !fs) {
        if (vs) glDeleteShader(vs);
        if (fs) glDeleteShader(fs);
        return 0;
    }
    GLuint prog = glCreateProgram();
    glAttachShader(prog, vs);
    glAttachShader(prog, fs);
    glLinkProgram(prog);
    GLint success = GL_FALSE;
    glGetProgramiv(prog, GL_LINK_STATUS, &success);
    glDeleteShader(vs);
    glDeleteShader(fs);
    if (success != GL_TRUE) {
        std::printf("Program link failed:\n%s\n", GetProgramLog(prog).c_str());
        glDeleteProgram(prog);
        return 0;
    }
    return prog;
}

// ---------------------------------------------------------------------------
// Renderer (modern shader-based only — macOS core profile has no legacy GL)
// ---------------------------------------------------------------------------

struct ModernRenderer {
    GLuint solidProgram = 0, texturedProgram = 0;
    GLuint solidVao = 0, solidVbo = 0;
    GLuint texturedVao = 0, texturedVbo = 0;
    GLuint checkerTexture = 0;
    GLint texturedSamplerLoc = -1;

    bool Init() {
        static const char *solidVS = R"(
#version 330 core
layout(location = 0) in vec2 aPosition;
layout(location = 1) in vec3 aColor;
out vec3 vColor;
void main() { vColor = aColor; gl_Position = vec4(aPosition, 0.0, 1.0); }
)";
        static const char *solidFS = R"(
#version 330 core
in vec3 vColor;
out vec4 fragColor;
void main() { fragColor = vec4(vColor, 1.0); }
)";
        static const char *texVS = R"(
#version 330 core
layout(location = 0) in vec2 aPosition;
layout(location = 1) in vec2 aTexCoord;
out vec2 vTexCoord;
void main() { vTexCoord = aTexCoord; gl_Position = vec4(aPosition, 0.0, 1.0); }
)";
        static const char *texFS = R"(
#version 330 core
in vec2 vTexCoord;
uniform sampler2D uTexture;
out vec4 fragColor;
void main() { fragColor = texture(uTexture, vTexCoord); }
)";
        solidProgram = LinkProgram(solidVS, solidFS);
        texturedProgram = LinkProgram(texVS, texFS);
        if (!solidProgram || !texturedProgram) return false;

        // Solid triangle (pos2 + color3)
        const std::array<float, 15> solidVerts = {
            -0.85f, -0.55f, 1.0f, 0.2f, 0.2f,
            -0.15f, -0.55f, 0.2f, 1.0f, 0.3f,
            -0.50f,  0.30f, 0.2f, 0.4f, 1.0f,
        };
        glGenVertexArrays(1, &solidVao);
        glBindVertexArray(solidVao);
        glGenBuffers(1, &solidVbo);
        glBindBuffer(GL_ARRAY_BUFFER, solidVbo);
        glBufferData(GL_ARRAY_BUFFER, sizeof(solidVerts), solidVerts.data(), GL_STATIC_DRAW);
        glEnableVertexAttribArray(0);
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 5 * sizeof(float), (void *)0);
        glEnableVertexAttribArray(1);
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 5 * sizeof(float), (void *)(2 * sizeof(float)));

        // Textured quad (pos2 + uv2)
        const std::array<float, 24> texVerts = {
             0.10f, -0.60f, 0.0f, 0.0f,
             0.80f, -0.60f, 1.0f, 0.0f,
             0.80f,  0.20f, 1.0f, 1.0f,
             0.10f, -0.60f, 0.0f, 0.0f,
             0.80f,  0.20f, 1.0f, 1.0f,
             0.10f,  0.20f, 0.0f, 1.0f,
        };
        glGenVertexArrays(1, &texturedVao);
        glBindVertexArray(texturedVao);
        glGenBuffers(1, &texturedVbo);
        glBindBuffer(GL_ARRAY_BUFFER, texturedVbo);
        glBufferData(GL_ARRAY_BUFFER, sizeof(texVerts), texVerts.data(), GL_STATIC_DRAW);
        glEnableVertexAttribArray(0);
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4 * sizeof(float), (void *)0);
        glEnableVertexAttribArray(1);
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4 * sizeof(float), (void *)(2 * sizeof(float)));

        glBindVertexArray(0);
        glBindBuffer(GL_ARRAY_BUFFER, 0);

        // 4x4 checkerboard texture
        const std::array<unsigned char, 64> pixels = {
            255,64,64,255, 32,32,32,255, 255,255,64,255, 32,32,32,255,
            32,32,32,255, 255,160,64,255, 32,32,32,255, 64,224,255,255,
            255,255,64,255, 32,32,32,255, 64,255,128,255, 32,32,32,255,
            32,32,32,255, 64,224,255,255, 32,32,32,255, 255,64,160,255,
        };
        glGenTextures(1, &checkerTexture);
        glBindTexture(GL_TEXTURE_2D, checkerTexture);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, 4, 4, 0, GL_RGBA, GL_UNSIGNED_BYTE, pixels.data());
        glBindTexture(GL_TEXTURE_2D, 0);

        texturedSamplerLoc = glGetUniformLocation(texturedProgram, "uTexture");
        return texturedSamplerLoc >= 0;
    }

    void Render(int w, int h) const {
        glViewport(0, 0, w, h);
        glClearColor(0.08f, 0.10f, 0.18f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);

        glUseProgram(solidProgram);
        glBindVertexArray(solidVao);
        glDrawArrays(GL_TRIANGLES, 0, 3);

        glUseProgram(texturedProgram);
        glActiveTexture(GL_TEXTURE0);
        glBindTexture(GL_TEXTURE_2D, checkerTexture);
        glUniform1i(texturedSamplerLoc, 0);
        glBindVertexArray(texturedVao);
        glDrawArrays(GL_TRIANGLES, 0, 6);

        glBindVertexArray(0);
        glUseProgram(0);
    }

    void Shutdown() {
        if (checkerTexture) { glDeleteTextures(1, &checkerTexture); checkerTexture = 0; }
        if (solidVbo) { glDeleteBuffers(1, &solidVbo); solidVbo = 0; }
        if (texturedVbo) { glDeleteBuffers(1, &texturedVbo); texturedVbo = 0; }
        if (solidVao) { glDeleteVertexArrays(1, &solidVao); solidVao = 0; }
        if (texturedVao) { glDeleteVertexArrays(1, &texturedVao); texturedVao = 0; }
        if (solidProgram) { glDeleteProgram(solidProgram); solidProgram = 0; }
        if (texturedProgram) { glDeleteProgram(texturedProgram); texturedProgram = 0; }
    }
};

// ---------------------------------------------------------------------------
// Application delegate
// ---------------------------------------------------------------------------

static ModernRenderer gRenderer;
static int gFrameCount = 0;
static const int kMaxFrames = 120;

@interface SmokeAppDelegate : NSObject <NSApplicationDelegate>
@property (strong) NSWindow *window;
@property (strong) NSOpenGLView *glView;
@property (strong) NSTimer *frameTimer;
@end

@implementation SmokeAppDelegate

- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    (void)notification;

    NSRect frame = NSMakeRect(100, 100, 960, 640);
    self.window = [[NSWindow alloc]
        initWithContentRect:frame
                  styleMask:(NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskResizable)
                    backing:NSBackingStoreBuffered
                      defer:NO];
    [self.window setTitle:@"RenderDoc MCP OpenGL Smoke Test (macOS)"];

    NSOpenGLPixelFormatAttribute attrs[] = {
        NSOpenGLPFAOpenGLProfile, NSOpenGLProfileVersion3_2Core,
        NSOpenGLPFAColorSize, 24,
        NSOpenGLPFADepthSize, 24,
        NSOpenGLPFADoubleBuffer,
        NSOpenGLPFAAccelerated,
        0
    };
    NSOpenGLPixelFormat *pf = [[NSOpenGLPixelFormat alloc] initWithAttributes:attrs];
    if (!pf) {
        std::printf("Failed to create NSOpenGLPixelFormat\n");
        [NSApp terminate:nil];
        return;
    }

    self.glView = [[NSOpenGLView alloc] initWithFrame:frame pixelFormat:pf];
    [self.window setContentView:self.glView];
    [self.window makeKeyAndOrderFront:nil];

    [[self.glView openGLContext] makeCurrentContext];

    const char *version = (const char *)glGetString(GL_VERSION);
    const char *renderer = (const char *)glGetString(GL_RENDERER);
    std::printf("GL_VERSION=%s\n", version ? version : "<unknown>");
    std::printf("GL_RENDERER=%s\n", renderer ? renderer : "<unknown>");
    std::printf("Renderer path=modern-shader\n");

    if (!gRenderer.Init()) {
        std::printf("Renderer initialization failed.\n");
        [NSApp terminate:nil];
        return;
    }

    self.frameTimer = [NSTimer scheduledTimerWithTimeInterval:1.0 / 60.0
                                                      target:self
                                                    selector:@selector(renderFrame:)
                                                    userInfo:nil
                                                     repeats:YES];
}

- (void)renderFrame:(NSTimer *)timer {
    (void)timer;
    [[self.glView openGLContext] makeCurrentContext];

    // Start capture on the designated frame
    if (rdocAPI && gFrameCount == gCaptureFrame) {
        std::printf("Starting capture at frame %d\n", gFrameCount);
        // Pass the NSOpenGLContext's CGLContextObj as the device pointer
        CGLContextObj cglCtx = [[self.glView openGLContext] CGLContextObj];
        std::printf("  CGL context: %p\n", (void*)cglCtx);
        rdocAPI->StartFrameCapture((RENDERDOC_DevicePointer)cglCtx, nullptr);
    }

    NSRect bounds = [self.glView bounds];
    NSRect backing = [self.glView convertRectToBacking:bounds];
    int w = (int)backing.size.width;
    int h = (int)backing.size.height;

    gRenderer.Render(w, h);
    [[self.glView openGLContext] flushBuffer];

    // End capture after the frame
    if (rdocAPI && gFrameCount == gCaptureFrame) {
        CGLContextObj cglCtx = [[self.glView openGLContext] CGLContextObj];
        uint32_t result = rdocAPI->EndFrameCapture((RENDERDOC_DevicePointer)cglCtx, nullptr);
        std::printf("EndFrameCapture result: %u (1=success)\n", result);
    }

    gFrameCount++;
    if (gFrameCount >= kMaxFrames) {
        [self.frameTimer invalidate];
        self.frameTimer = nil;
        gRenderer.Shutdown();
        std::printf("Completed %d frames.\n", gFrameCount);
        [NSApp terminate:nil];
    }
}

- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender {
    (void)sender;
    return YES;
}

@end

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

static void initRenderDoc() {
    const char *libPath = std::getenv("RENDERDOC_LIB_PATH");
    if (!libPath) return;

    void *handle = dlopen(libPath, RTLD_NOW | RTLD_NOLOAD);
    if (!handle) handle = dlopen(libPath, RTLD_NOW);
    if (!handle) {
        std::printf("Failed to load RenderDoc: %s\n", dlerror());
        return;
    }

    auto getAPI = (pRENDERDOC_GetAPI)dlsym(handle, "RENDERDOC_GetAPI");
    if (!getAPI) {
        std::printf("RENDERDOC_GetAPI not found\n");
        return;
    }

    int ret = getAPI(10000, (void **)&rdocAPI);  // eRENDERDOC_API_Version_1_0_0
    if (ret != 1 || !rdocAPI) {
        std::printf("RENDERDOC_GetAPI failed\n");
        rdocAPI = nullptr;
        return;
    }

    int major, minor, patch;
    rdocAPI->GetAPIVersion(&major, &minor, &patch);
    std::printf("RenderDoc API %d.%d.%d loaded\n", major, minor, patch);

    const char *capPath = std::getenv("RENDERDOC_CAPTURE_PATH");
    gCapturePath = capPath ? capPath : "/tmp/renderdoc_smoke_capture";
    rdocAPI->SetCaptureFilePathTemplate(gCapturePath.c_str());

    const char *captureFrameStr = std::getenv("RENDERDOC_CAPTURE_FRAME");
    gCaptureFrame = captureFrameStr ? std::atoi(captureFrameStr) : 30;

    std::printf("Will capture frame %d to %s\n", gCaptureFrame, gCapturePath.c_str());
}

int main(int argc, const char *argv[]) {
    (void)argc;
    (void)argv;
    @autoreleasepool {
        initRenderDoc();
        NSApplication *app = [NSApplication sharedApplication];
        [app setActivationPolicy:NSApplicationActivationPolicyRegular];
        SmokeAppDelegate *delegate = [[SmokeAppDelegate alloc] init];
        [app setDelegate:delegate];
        [app run];
    }
    return 0;
}
