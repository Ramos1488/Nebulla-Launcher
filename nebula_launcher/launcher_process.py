"""Builds the java command line for a version json + instance, and runs it."""
from __future__ import annotations
import os
import subprocess
from pathlib import Path
from typing import Callable, Optional

from . import config, mojang_api
from .instance import Instance
from .auth import Account


def _classpath(vjson: dict, version_id: str) -> str:
    parts = []
    for lib in vjson.get("libraries", []):
        if not mojang_api.library_is_active(lib):
            continue
        artifact = mojang_api.resolve_download_artifact(lib)
        if artifact:
            parts.append(str(config.LIBRARIES_DIR / artifact["path"]))
    parts.append(str(config.VERSIONS_DIR / version_id / f"{version_id}.jar"))
    sep = ";" if config.CURRENT_OS == "windows" else ":"
    return sep.join(parts)


def _substitute(template: str, values: dict[str, str]) -> str:
    for k, v in values.items():
        template = template.replace("${" + k + "}", v)
    return template


def build_launch_command(instance: Instance, vjson: dict, account: Account) -> list[str]:
    version_id = instance.version_id
    natives_dir = config.NATIVES_CACHE_DIR / version_id
    classpath = _classpath(vjson, version_id)
    asset_index_id = vjson.get("assetIndex", {}).get("id", version_id)

    values = {
        "auth_player_name": account.username,
        "version_name": version_id,
        "game_directory": str(instance.minecraft_dir),
        "assets_root": str(config.ASSETS_DIR),
        "assets_index_name": asset_index_id,
        "auth_uuid": account.uuid,
        "auth_access_token": account.access_token or "0",
        "clientid": "nebula-launcher",
        "auth_xuid": account.uuid,
        "user_type": "msa" if account.kind == "microsoft" else "legacy",
        "version_type": vjson.get("type", "release"),
        "natives_directory": str(natives_dir),
        "launcher_name": config.APP_NAME,
        "launcher_version": config.APP_VERSION,
        "classpath": classpath,
        "user_properties": "{}",
    }

    settings = instance.settings
    cmd = [settings.java_path]
    cmd += [f"-Xms{settings.min_ram_mb}M", f"-Xmx{settings.max_ram_mb}M"]
    if settings.jvm_args.strip():
        cmd += settings.jvm_args.strip().split()

    # JVM arguments (modern versions describe these explicitly; older ones don't)
    args_section = vjson.get("arguments", {})
    jvm_args = args_section.get("jvm")
    if jvm_args:
        for a in jvm_args:
            if isinstance(a, str):
                cmd.append(_substitute(a, values))
            elif mojang_api.rules_allow(a.get("rules")):
                val = a["value"]
                vals = val if isinstance(val, list) else [val]
                cmd += [_substitute(v, values) for v in vals]
    else:
        # legacy versions: minimal manual equivalent
        cmd += [
            f"-Djava.library.path={natives_dir}",
            "-cp", classpath,
        ]

    cmd.append(vjson.get("mainClass", "net.minecraft.client.main.Main"))

    game_args = args_section.get("game")
    if game_args:
        for a in game_args:
            if isinstance(a, str):
                cmd.append(_substitute(a, values))
            elif mojang_api.rules_allow(a.get("rules")):
                val = a["value"]
                vals = val if isinstance(val, list) else [val]
                cmd += [_substitute(v, values) for v in vals]
    else:
        legacy = vjson.get("minecraftArguments", "")
        if legacy:
            cmd += [_substitute(tok, values) for tok in legacy.split()]

    return cmd


def launch(instance: Instance, vjson: dict, account: Account,
           on_output: Optional[Callable[[str], None]] = None) -> subprocess.Popen:
    cmd = build_launch_command(instance, vjson, account)
    instance.minecraft_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        cmd,
        cwd=str(instance.minecraft_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=os.environ.copy(),
    )
    return proc
