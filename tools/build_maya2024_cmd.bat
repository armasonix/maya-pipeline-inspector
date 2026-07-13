@echo off
setlocal EnableExtensions
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
cd /d D:\Workspace\portfolio\maya-pipeline-inspector
set "DEVKIT=C:\Program Files\Autodesk\Maya2024"
set "BUILD_DIR=native\build\maya2024"
set "CMAKE=C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
for /f "usebackq tokens=1,* delims==" %%A in (`findstr /r /c:"^__version__" src\pipeline_inspector\version.py`) do set "VERSION=%%B"
set "VERSION=%VERSION:"=%"
set "VERSION=%VERSION: =%"
"%CMAKE%" -S native -B "%BUILD_DIR%" -DMAYA_VERSION=2024 -DMAYA_DEVKIT_ROOT="%DEVKIT%" -DPIPELINE_INSPECTOR_PLUGIN_VERSION=%VERSION%
if errorlevel 1 exit /b 1
"%CMAKE%" --build "%BUILD_DIR%" --config Release
if errorlevel 1 exit /b 1
"%CMAKE%" --install "%BUILD_DIR%" --config Release
if errorlevel 1 exit /b 1
copy /Y "maya_module\plug-ins\2024\pipeline_inspector.mll" "maya_module\plug-ins\pipeline_inspector.mll"
echo Build OK: maya_module\plug-ins\pipeline_inspector.mll
