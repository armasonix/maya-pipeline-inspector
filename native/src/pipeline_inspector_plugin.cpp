// Thin Maya plug-in bootstrap — delegates UI to Python (ADR 0006).
#include <maya/MFnPlugin.h>
#include <maya/MGlobal.h>
#include <maya/MStatus.h>

#ifndef PIPELINE_INSPECTOR_PLUGIN_VERSION
#define PIPELINE_INSPECTOR_PLUGIN_VERSION "0.3.0"
#endif

#ifndef PIPELINE_INSPECTOR_PLUGIN_VENDOR
#define PIPELINE_INSPECTOR_PLUGIN_VENDOR "Pipeline Inspector"
#endif

namespace {

constexpr const char* kInstallUiCommand =
    "import maya.utils; "
    "maya.utils.executeDeferred("
    "\"import pipeline_inspector_bootstrap; "
    "pipeline_inspector_bootstrap.install_ui()\")";

constexpr const char* kUninstallUiCommand =
    "import pipeline_inspector_bootstrap; "
    "pipeline_inspector_bootstrap.uninstall_ui()";

MStatus runPython(const char* command) {
    MStatus status = MGlobal::executePythonCommand(command);
    if (!status) {
        MGlobal::displayError(
            "Pipeline Inspector native plug-in Python bootstrap failed.");
    }
    return status;
}

}  // namespace

MStatus initializePlugin(MObject obj) {
    MFnPlugin plugin(
        obj,
        PIPELINE_INSPECTOR_PLUGIN_VENDOR,
        PIPELINE_INSPECTOR_PLUGIN_VERSION,
        "Any");
    (void)plugin;
    return runPython(kInstallUiCommand);
}

MStatus uninitializePlugin(MObject obj) {
    MFnPlugin plugin(obj);
    (void)plugin;
    return runPython(kUninstallUiCommand);
}
