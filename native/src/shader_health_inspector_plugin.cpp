// Thin Maya plug-in bootstrap — delegates UI to Python (ADR 0006).
#include <maya/MFnPlugin.h>
#include <maya/MGlobal.h>
#include <maya/MStatus.h>

#ifndef SHADER_HEALTH_PLUGIN_VERSION
#define SHADER_HEALTH_PLUGIN_VERSION "0.3.0"
#endif

#ifndef SHADER_HEALTH_PLUGIN_VENDOR
#define SHADER_HEALTH_PLUGIN_VENDOR "Shader Health Inspector"
#endif

namespace {

constexpr const char* kInstallUiCommand =
    "import maya.utils; "
    "maya.utils.executeDeferred("
    "\"import shader_health_inspector_bootstrap; "
    "shader_health_inspector_bootstrap.install_ui()\")";

constexpr const char* kUninstallUiCommand =
    "import shader_health_inspector_bootstrap; "
    "shader_health_inspector_bootstrap.uninstall_ui()";

MStatus runPython(const char* command) {
    MStatus status = MGlobal::executePythonCommand(command);
    if (!status) {
        MGlobal::displayError(
            "Shader Health Inspector native plug-in Python bootstrap failed.");
    }
    return status;
}

}  // namespace

MStatus initializePlugin(MObject obj) {
    MFnPlugin plugin(
        obj,
        SHADER_HEALTH_PLUGIN_VENDOR,
        SHADER_HEALTH_PLUGIN_VERSION,
        "Any");
    (void)plugin;
    return runPython(kInstallUiCommand);
}

MStatus uninitializePlugin(MObject obj) {
    MFnPlugin plugin(obj);
    (void)plugin;
    return runPython(kUninstallUiCommand);
}
