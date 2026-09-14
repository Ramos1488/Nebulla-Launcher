"""Global paths and constants for Nebula Launcher."""
from pathlib import Path
import platform
import sys

APP_NAME = "Nebula Launcher"
APP_VERSION = "0.1.0"

# --- Root data directory -------------------------------------------------
if sys.platform.startswith("win"):
    _base = Path.home() / "AppData" / "Roaming"
elif sys.platform == "darwin":
    _base = Path.home() / "Library" / "Application Support"
else:
    _base = Path.home() / ".local" / "share"

DATA_DIR = _base / "NebulaLauncher"
INSTANCES_DIR = DATA_DIR / "instances"
ASSETS_DIR = DATA_DIR / "assets"
LIBRARIES_DIR = DATA_DIR / "libraries"
VERSIONS_DIR = DATA_DIR / "versions"
NATIVES_CACHE_DIR = DATA_DIR / "natives"
ACCOUNTS_FILE = DATA_DIR / "accounts.json"

for d in (DATA_DIR, INSTANCES_DIR, ASSETS_DIR, LIBRARIES_DIR, VERSIONS_DIR, NATIVES_CACHE_DIR):
    d.mkdir(parents=True, exist_ok=True)

# --- Mojang / Microsoft endpoints ----------------------------------------
VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
RESOURCES_BASE_URL = "https://resources.download.minecraft.net"

MS_DEVICE_CODE_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode"
MS_TOKEN_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
XBL_AUTH_URL = "https://user.auth.xboxlive.com/user/authenticate"
XSTS_AUTH_URL = "https://xsts.auth.xboxlive.com/xsts/authorize"
MC_LOGIN_URL = "https://api.minecraftservices.com/authentication/login_with_xbox"
MC_PROFILE_URL = "https://api.minecraftservices.com/minecraft/profile"
MC_ENTITLEMENTS_URL = "https://api.minecraftservices.com/entitlements/mcstore"

# Public "demo" client id — good enough to test the device-code flow, but for
# real-world reliability register your own Azure app (see README) and put its
# id here instead.
MS_CLIENT_ID = "00000000-0000-0000-0000-000000000000"

# --- OS detection for library rule resolution -----------------------------
def current_os_name() -> str:
    s = platform.system().lower()
    if s.startswith("win"):
        return "windows"
    if s == "darwin":
        return "osx"
    return "linux"

CURRENT_OS = current_os_name()
CURRENT_ARCH = "x86" if platform.architecture()[0] == "32bit" else "x64"
