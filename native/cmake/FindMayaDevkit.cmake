#[=======================================================================[.rst:
FindMayaDevkit
--------------

Locates an Autodesk Maya devkit for building a native plug-in.

Inputs
^^^^^^

Cache / environment:

- ``MAYA_DEVKIT_ROOT`` — devkit root (``include/``, ``lib/``)
- ``MAYA_LOCATION`` — fallback when ``MAYA_DEVKIT_ROOT`` is unset

Outputs
^^^^^^^

- ``MAYA_DEVKIT_FOUND``
- ``MAYA_DEVKIT_ROOT``
- ``MAYA_DEVKIT_INCLUDE_DIR``
- ``MAYA_DEVKIT_LIBRARY_DIR``
- ``MAYA_DEVKIT_LIBRARIES`` — ``OpenMaya`` and ``Foundation``
#]=======================================================================]

if(NOT MAYA_DEVKIT_ROOT)
  if(DEFINED ENV{MAYA_DEVKIT_ROOT} AND NOT "$ENV{MAYA_DEVKIT_ROOT}" STREQUAL "")
    set(MAYA_DEVKIT_ROOT "$ENV{MAYA_DEVKIT_ROOT}")
  elseif(DEFINED ENV{MAYA_LOCATION} AND NOT "$ENV{MAYA_LOCATION}" STREQUAL "")
    set(MAYA_DEVKIT_ROOT "$ENV{MAYA_LOCATION}")
  endif()
endif()

if(NOT MAYA_DEVKIT_ROOT)
  set(MAYA_DEVKIT_FOUND FALSE)
  set(MayaDevkit_FOUND FALSE)
  message(FATAL_ERROR "MAYA_DEVKIT_ROOT or MAYA_LOCATION is required to build the native plug-in.")
endif()

set(MAYA_DEVKIT_INCLUDE_DIR "${MAYA_DEVKIT_ROOT}/include")
set(MAYA_DEVKIT_LIBRARY_DIR "${MAYA_DEVKIT_ROOT}/lib")

if(NOT EXISTS "${MAYA_DEVKIT_INCLUDE_DIR}/maya/MFnPlugin.h")
  message(
    FATAL_ERROR
    "Maya devkit headers not found at ${MAYA_DEVKIT_INCLUDE_DIR} (check MAYA_DEVKIT_ROOT)."
  )
endif()

find_library(
  MAYA_OpenMaya_LIBRARY
  NAMES OpenMaya
  PATHS "${MAYA_DEVKIT_LIBRARY_DIR}"
  NO_DEFAULT_PATH
)
find_library(
  MAYA_Foundation_LIBRARY
  NAMES Foundation
  PATHS "${MAYA_DEVKIT_LIBRARY_DIR}"
  NO_DEFAULT_PATH
)

if(NOT MAYA_OpenMaya_LIBRARY OR NOT MAYA_Foundation_LIBRARY)
  message(
    FATAL_ERROR
    "Maya devkit libraries not found under ${MAYA_DEVKIT_LIBRARY_DIR}."
  )
endif()

set(MAYA_DEVKIT_LIBRARIES "${MAYA_OpenMaya_LIBRARY}" "${MAYA_Foundation_LIBRARY}")
set(MAYA_DEVKIT_FOUND TRUE)
set(MayaDevkit_FOUND TRUE)

mark_as_advanced(
  MAYA_DEVKIT_ROOT
  MAYA_DEVKIT_INCLUDE_DIR
  MAYA_DEVKIT_LIBRARY_DIR
  MAYA_OpenMaya_LIBRARY
  MAYA_Foundation_LIBRARY
)
