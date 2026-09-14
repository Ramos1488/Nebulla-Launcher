"""Talks to Mojang's piston-meta APIs: version list + per-version manifest."""
from __future__ import annotations
import json
import requests
from dataclasses import dataclass
from typing import Optional

from . import config


@dataclass
class VersionInfo:
    id: str
    type: str  # release / snapshot / old_beta / old_alpha
    url: str
    release_time: str


def fetch_version_list() -> list[VersionInfo]:
    """Return every Minecraft version Mojang currently publishes, newest first."""
    r = requests.get(config.VERSION_MANIFEST_URL, timeout=20)
    r.raise_for_status()
    data = r.json()
    return [
        VersionInfo(id=v["id"], type=v["type"], url=v["url"], release_time=v["releaseTime"])
        for v in data["versions"]
    ]


def fetch_version_json(version: VersionInfo) -> dict:
    r = requests.get(version.url, timeout=20)
    r.raise_for_status()
    return r.json()


def rule_applies(rule: dict) -> bool:
    """Evaluate one entry of a library/argument 'rules' list for the current OS."""
    action = rule.get("action", "allow")
    os_rule = rule.get("os")
    matches = True
    if os_rule:
        name = os_rule.get("name")
        arch = os_rule.get("arch")
        if name and name != config.CURRENT_OS:
            matches = False
        if arch and arch != config.CURRENT_ARCH:
            matches = False
    allowed = matches if action == "allow" else not matches
    return allowed


def rules_allow(rules: Optional[list[dict]]) -> bool:
    if not rules:
        return True
    allowed = False
    for rule in rules:
        if rule_applies(rule):
            allowed = rule.get("action", "allow") == "allow"
        else:
            # rule doesn't match this OS -> doesn't affect the decision unless
            # it's the only rule with an explicit disallow for everyone else
            continue
    return allowed


def library_is_active(lib: dict) -> bool:
    return rules_allow(lib.get("rules"))


def library_natives_classifier(lib: dict) -> Optional[str]:
    """Return the classifier key (e.g. 'natives-windows') this lib needs on this OS, if any."""
    natives = lib.get("natives")
    if not natives:
        return None
    classifier = natives.get(config.CURRENT_OS)
    if not classifier:
        return None
    return classifier.replace("${arch}", "64" if config.CURRENT_ARCH == "x64" else "32")


def resolve_download_artifact(lib: dict) -> Optional[dict]:
    """Return the 'artifact' download dict for the main jar of a library, if present."""
    downloads = lib.get("downloads", {})
    return downloads.get("artifact")


def resolve_natives_artifact(lib: dict) -> Optional[dict]:
    classifier = library_natives_classifier(lib)
    if not classifier:
        return None
    downloads = lib.get("downloads", {})
    classifiers = downloads.get("classifiers", {})
    return classifiers.get(classifier)
