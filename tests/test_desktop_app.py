"""DocuVault Desktop Application Integration and Verification Tests."""
import json
import os
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DESKTOP_DIR = PROJECT_ROOT / "desktop"


def test_desktop_directory_structure():
    """Verify all required desktop application files exist."""
    required_files = [
        DESKTOP_DIR / "package.json",
        DESKTOP_DIR / "main.js",
        DESKTOP_DIR / "preload.js",
        DESKTOP_DIR / "index.html",
        DESKTOP_DIR / "renderer.js",
        DESKTOP_DIR / "styles" / "desktop.css",
        DESKTOP_DIR / "assets" / "icon.svg",
        PROJECT_ROOT / "package.json",
        PROJECT_ROOT / "run_desktop.sh",
    ]
    for file_path in required_files:
        assert file_path.exists(), f"Missing required desktop file: {file_path}"


def test_desktop_package_json():
    """Verify desktop package.json manifests and Electron dependencies."""
    pkg_path = DESKTOP_DIR / "package.json"
    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg = json.load(f)

    assert pkg["name"] == "docuvault-desktop"
    assert "electron" in pkg.get("devDependencies", {})
    assert "start" in pkg.get("scripts", {})
    assert pkg["main"] == "main.js"


def test_root_package_json():
    """Verify root package.json has desktop commands."""
    pkg_path = PROJECT_ROOT / "package.json"
    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg = json.load(f)

    assert "desktop" in pkg.get("scripts", {})
    assert "desktop:dev" in pkg.get("scripts", {})
    assert "server" in pkg.get("scripts", {})


def test_desktop_javascript_syntax():
    """Validate JS files have valid syntax using Node syntax checker."""
    js_files = [
        DESKTOP_DIR / "main.js",
        DESKTOP_DIR / "preload.js",
        DESKTOP_DIR / "renderer.js",
    ]
    for js_file in js_files:
        res = subprocess.run(
            ["node", "-c", str(js_file)],
            capture_output=True,
            text=True
        )
        assert res.returncode == 0, f"JS Syntax error in {js_file.name}: {res.stderr}"


def test_desktop_launcher_script_executable():
    """Verify run_desktop.sh is marked executable and has valid bash syntax."""
    launcher = PROJECT_ROOT / "run_desktop.sh"
    assert os.access(launcher, os.X_OK), "run_desktop.sh is not executable"
    res = subprocess.run(["bash", "-n", str(launcher)], capture_output=True, text=True)
    assert res.returncode == 0, f"Bash syntax error in run_desktop.sh: {res.stderr}"


def test_preload_script_apis():
    """Verify preload.js exposes all necessary docuvaultNative native APIs."""
    preload_content = (DESKTOP_DIR / "preload.js").read_text(encoding="utf-8")
    expected_apis = [
        "isDesktop",
        "openFileDialog",
        "computeFileHash",
        "saveFileDialog",
        "getBackendStatus",
        "restartBackend",
        "getAppInfo",
        "openExternal",
        "onBackendStatusChanged",
        "onMenuAction"
    ]
    for api in expected_apis:
        assert api in preload_content, f"Preload bridge missing native API: {api}"


def test_main_process_ipc_channels():
    """Verify main.js handles all essential IPC channels for backend and crypto."""
    main_content = (DESKTOP_DIR / "main.js").read_text(encoding="utf-8")
    expected_channels = [
        "dialog:open-file",
        "file:compute-hash",
        "dialog:save-file",
        "backend:get-status",
        "backend:restart",
        "app:get-info",
        "shell:open-external"
    ]
    for ch in expected_channels:
        assert ch in main_content, f"main.js missing IPC handler for channel: {ch}"
