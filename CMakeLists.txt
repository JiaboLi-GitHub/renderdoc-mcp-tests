cmake_minimum_required(VERSION 3.20)

if(APPLE)
    project(renderdoc_mcp_tests LANGUAGES CXX OBJCXX)
else()
    project(renderdoc_mcp_tests LANGUAGES CXX)
endif()

if(APPLE)
    # --- macOS targets (Objective-C++) ---
    add_executable(renderdoc_mcp_opengl_smoke
        src/renderdoc_mcp_opengl_smoke_macos.mm
    )

    foreach(target_name IN ITEMS renderdoc_mcp_opengl_smoke)
        target_compile_features(${target_name} PRIVATE cxx_std_17)
        target_compile_options(${target_name} PRIVATE
            -Wall -Wextra -Wpedantic
            -Wno-deprecated-declarations
        )
        target_link_libraries(${target_name} PRIVATE
            "-framework OpenGL"
            "-framework Cocoa"
        )
    endforeach()

    set_target_properties(renderdoc_mcp_opengl_smoke PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
    )

elseif(WIN32)
    # --- Windows targets (existing code) ---
    add_executable(renderdoc_mcp_opengl_smoke
        src/renderdoc_mcp_opengl_smoke.cpp
    )

    add_executable(renderdoc_mcp_opengl_advanced
        src/renderdoc_mcp_opengl_advanced.cpp
    )

    foreach(target_name IN ITEMS renderdoc_mcp_opengl_smoke renderdoc_mcp_opengl_advanced)
        target_compile_features(${target_name} PRIVATE cxx_std_17)
        target_compile_definitions(${target_name} PRIVATE
            NOMINMAX
            WIN32_LEAN_AND_MEAN
            _CRT_SECURE_NO_WARNINGS
        )
        target_link_libraries(${target_name} PRIVATE opengl32)
    endforeach()

    if(MSVC)
        target_compile_options(renderdoc_mcp_opengl_smoke PRIVATE /W4 /EHsc /utf-8)
        target_compile_options(renderdoc_mcp_opengl_advanced PRIVATE /W4 /EHsc /utf-8)
    else()
        target_compile_options(renderdoc_mcp_opengl_smoke PRIVATE -Wall -Wextra -Wpedantic)
        target_compile_options(renderdoc_mcp_opengl_advanced PRIVATE -Wall -Wextra -Wpedantic)
    endif()

    set_target_properties(renderdoc_mcp_opengl_smoke renderdoc_mcp_opengl_advanced PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
    )

    # --- Vulkan targets (Windows only) ---
    find_package(Vulkan QUIET)

    if(Vulkan_FOUND)
        add_executable(renderdoc_mcp_vulkan_advanced
            src/renderdoc_mcp_vulkan_advanced.cpp
        )
        target_compile_features(renderdoc_mcp_vulkan_advanced PRIVATE cxx_std_17)
        target_compile_definitions(renderdoc_mcp_vulkan_advanced PRIVATE
            NOMINMAX
            WIN32_LEAN_AND_MEAN
            _CRT_SECURE_NO_WARNINGS
            VK_USE_PLATFORM_WIN32_KHR
        )
        target_link_libraries(renderdoc_mcp_vulkan_advanced PRIVATE Vulkan::Vulkan)

        if(MSVC)
            target_compile_options(renderdoc_mcp_vulkan_advanced PRIVATE /W4 /EHsc /utf-8)
        else()
            target_compile_options(renderdoc_mcp_vulkan_advanced PRIVATE -Wall -Wextra -Wpedantic)
        endif()

        set_target_properties(renderdoc_mcp_vulkan_advanced PROPERTIES
            RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
        )
    else()
        message(STATUS "Vulkan SDK not found -- skipping Vulkan targets")
    endif()
endif()
