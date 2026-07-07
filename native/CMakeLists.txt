# Shader Health Inspector — native Maya plugin (thin C++ bootstrap)
#
# Builds shader_health_inspector.mll / .so / .bundle per Maya year.
# See docs/adr/0006-native-mll-plugin-strategy.md

cmake_minimum_required(VERSION 3.20)
project(shader_health_inspector_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT DEFINED MAYA_VERSION)
  message(FATAL_ERROR "Set -DMAYA_VERSION=2024|2025|2026")
endif()

set(SHADER_HEALTH_PLUGIN_VERSION "0.3.0" CACHE STRING "Plug-in version (sync with pyproject.toml)")
set(SHADER_HEALTH_PLUGIN_NAME "shader_health_inspector")

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
find_package(MayaDevkit REQUIRED)

get_filename_component(REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)
set(
  SHADER_HEALTH_PLUGIN_INSTALL_DIR
  "${REPO_ROOT}/maya_module/plug-ins/${MAYA_VERSION}"
  CACHE PATH "Install folder for the built plug-in binary"
)

add_library(
  ${SHADER_HEALTH_PLUGIN_NAME}
  SHARED
  src/shader_health_inspector_plugin.cpp
)

target_include_directories(
  ${SHADER_HEALTH_PLUGIN_NAME}
  PRIVATE
  ${MAYA_DEVKIT_INCLUDE_DIR}
)

target_link_libraries(
  ${SHADER_HEALTH_PLUGIN_NAME}
  PRIVATE
  ${MAYA_DEVKIT_LIBRARIES}
)

target_compile_definitions(
  ${SHADER_HEALTH_PLUGIN_NAME}
  PRIVATE
  SHADER_HEALTH_PLUGIN_VERSION="${SHADER_HEALTH_PLUGIN_VERSION}"
  SHADER_HEALTH_PLUGIN_VENDOR="Shader Health Inspector"
)

set_target_properties(
  ${SHADER_HEALTH_PLUGIN_NAME}
  PROPERTIES
  PREFIX ""
  OUTPUT_NAME "${SHADER_HEALTH_PLUGIN_NAME}"
)

if(WIN32)
  set_target_properties(${SHADER_HEALTH_PLUGIN_NAME} PROPERTIES SUFFIX ".mll")
elseif(APPLE)
  set_target_properties(
    ${SHADER_HEALTH_PLUGIN_NAME}
    PROPERTIES
    SUFFIX ".bundle"
    BUNDLE TRUE
  )
else()
  set_target_properties(${SHADER_HEALTH_PLUGIN_NAME} PROPERTIES SUFFIX ".so")
endif()

if(MSVC)
  target_compile_options(${SHADER_HEALTH_PLUGIN_NAME} PRIVATE /W3 /MD)
endif()

install(
  TARGETS ${SHADER_HEALTH_PLUGIN_NAME}
  LIBRARY DESTINATION "${SHADER_HEALTH_PLUGIN_INSTALL_DIR}"
  RUNTIME DESTINATION "${SHADER_HEALTH_PLUGIN_INSTALL_DIR}"
)

message(STATUS "Maya version: ${MAYA_VERSION}")
message(STATUS "Devkit root: ${MAYA_DEVKIT_ROOT}")
message(STATUS "Install dir: ${SHADER_HEALTH_PLUGIN_INSTALL_DIR}")
