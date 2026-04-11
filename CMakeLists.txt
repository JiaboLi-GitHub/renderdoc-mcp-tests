cmake_minimum_required(VERSION 3.20)

project(renderdoc_mcp_opengl_smoke LANGUAGES CXX)

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
