"""Instance = one isolated Minecraft install (own version, mods, saves, config)."""
from __future__ import annotations
import json
import re
import shutil
import zipfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from . import config, mojang_api, downloader

INSTANCE_CFG_NAME = "instance.json"


@dataclass
class InstanceSettings:
    min_ram_mb: int = 1024
    max_ram_mb: int = 2048
    java_path: str = "java"
    jvm_args: str = ""
    window_width: int = 854
    window_height: int = 480


@dataclass
class Instance:
    name: str
    version_id: str
    icon: str = "nebula"
    settings: InstanceSettings = field(default_factory=InstanceSettings)

    @property
    def folder(self) -> Path:
        safe = re.sub(r"[^\w\-. ]", "_", self.name)
        return config.INSTANCES_DIR / safe

    @property
    def minecraft_dir(self) -> Path:
        return self.folder / "minecraft"

    def save(self) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        self.minecraft_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "name": self.name,
            "version_id": self.version_id,
            "icon": self.icon,
            "settings": asdict(self.settings),
        }
        (self.folder / INSTANCE_CFG_NAME).write_text(json.dumps(data, indent=2), encoding="utf-8")

    @staticmethod
    def load(folder: Path) -> "Instance":
        data = json.loads((folder / INSTANCE_CFG_NAME).read_text(encoding="utf-8"))
        return Instance(
            name=data["name"],
            version_id=data["version_id"],
            icon=data.get("icon", "nebula"),
            settings=InstanceSettings(**data.get("settings", {})),
        )


class InstanceManager:
    def list_instances(self) -> list[Instance]:
        result = []
        if not config.INSTANCES_DIR.exists():
            return result
        for folder in sorted(config.INSTANCES_DIR.iterdir()):
            cfg = folder / INSTANCE_CFG_NAME
            if cfg.exists():
                try:
                    result.append(Instance.load(folder))
                except Exception:
                    continue
        return result

    def create_instance(self, name: str, version_id: str) -> Instance:
        inst = Instance(name=name, version_id=version_id)
        inst.save()
        return inst

    def delete_instance(self, inst: Instance) -> None:
        if inst.folder.exists():
            shutil.rmtree(inst.folder)


# --------------------------------------------------------------------------
# Version preparation: download version json, client jar, libraries, assets
# --------------------------------------------------------------------------

def ensure_version_ready(version_id: str, progress=None) -> dict:
    """Download everything needed to launch `version_id` if not already cached.
    Returns the parsed version json (with inherited data merged in, if any)."""
    version_dir = config.VERSIONS_DIR / version_id
    version_dir.mkdir(parents=True, exist_ok=True)
    version_json_path = version_dir / f"{version_id}.json"

    if version_json_path.exists():
        vjson = json.loads(version_json_path.read_text(encoding="utf-8"))
    else:
        versions = mojang_api.fetch_version_list()
        match = next((v for v in versions if v.id == version_id), None)
        if not match:
            raise ValueError(f"Unknown version: {version_id}")
        vjson = mojang_api.fetch_version_json(match)
        version_json_path.write_text(json.dumps(vjson), encoding="utf-8")

    # inheritsFrom (used by some loader jsons; harmless for vanilla)
    if "inheritsFrom" in vjson:
        parent = ensure_version_ready(vjson["inheritsFrom"], progress)
        merged = dict(parent)
        merged.update({k: v for k, v in vjson.items() if k != "inheritsFrom"})
        vjson = merged

    jobs: list[tuple[str, Path, Optional[str]]] = []

    # client jar
    client_jar = version_dir / f"{version_id}.jar"
    client_info = vjson.get("downloads", {}).get("client")
    if client_info and not client_jar.exists():
        jobs.append((client_info["url"], client_jar, client_info.get("sha1")))

    # libraries + natives
    natives_zip_jobs: list[tuple[Path, Path]] = []  # (zip_path, extract_dir)
    natives_dir = config.NATIVES_CACHE_DIR / version_id
    for lib in vjson.get("libraries", []):
        if not mojang_api.library_is_active(lib):
            continue
        artifact = mojang_api.resolve_download_artifact(lib)
        if artifact:
            dest = config.LIBRARIES_DIR / artifact["path"]
            if not dest.exists():
                jobs.append((artifact["url"], dest, artifact.get("sha1")))
        native_artifact = mojang_api.resolve_natives_artifact(lib)
        if native_artifact:
            dest = config.LIBRARIES_DIR / native_artifact["path"]
            if not dest.exists():
                jobs.append((native_artifact["url"], dest, native_artifact.get("sha1")))
            natives_zip_jobs.append((dest, natives_dir))

    # asset index + objects
    asset_index = vjson.get("assetIndex")
    if asset_index:
        idx_path = config.ASSETS_DIR / "indexes" / f"{asset_index['id']}.json"
        if not idx_path.exists():
            jobs.append((asset_index["url"], idx_path, asset_index.get("sha1")))

    if progress:
        progress(0, 1, "Resolving asset index...")

    downloader.download_many(jobs, progress=progress)

    # now that the asset index is guaranteed local, queue the actual objects
    if asset_index:
        idx_path = config.ASSETS_DIR / "indexes" / f"{asset_index['id']}.json"
        idx = json.loads(idx_path.read_text(encoding="utf-8"))
        obj_jobs: list[tuple[str, Path, Optional[str]]] = []
        for obj in idx.get("objects", {}).values():
            h = obj["hash"]
            dest = config.ASSETS_DIR / "objects" / h[:2] / h
            if not dest.exists():
                url = f"{config.RESOURCES_BASE_URL}/{h[:2]}/{h}"
                obj_jobs.append((url, dest, h))
        downloader.download_many(obj_jobs, progress=progress)

    # extract natives
    natives_dir.mkdir(parents=True, exist_ok=True)
    for zip_path, extract_dir in natives_zip_jobs:
        try:
            with zipfile.ZipFile(zip_path) as zf:
                for member in zf.namelist():
                    if member.startswith("META-INF"):
                        continue
                    zf.extract(member, extract_dir)
        except zipfile.BadZipFile:
            continue

    return vjson
