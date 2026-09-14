# Nebula Launcher

A lightweight, open-source Minecraft launcher inspired by PolyMC's look and workflow:
instance-based, multi-version, offline + Microsoft account support.

## Features
- Supports **all** official Minecraft versions (release, snapshot, old_alpha, old_beta)
  pulled live from Mojang's version manifest.
- Instance-based: every install lives in its own isolated folder (own saves, mods,
  resource packs, options) — exactly like PolyMC/MultiMC/Prism.
- PolyMC-style UI: instance grid on the left, console/log view, dark theme.
- Automatic download of client jar, libraries (with OS/arch rule resolution),
  natives extraction and asset objects.
- Offline ("cracked") play and Microsoft OAuth device-code login.
- Per-instance settings: RAM allocation, Java path, extra JVM args, window size.

## Requirements
- Python 3.10+
- Java (any recent JDK/JRE; the launcher will ask for a path if it can't find one)

## Install & run
```bash
pip install -r requirements.txt
python -m nebula_launcher.main
```

## Microsoft account login
Microsoft auth uses the standard OAuth2 device-code flow. To use your *own* account
tier (instead of the shared demo client id baked in), create a free Azure app
registration and put its client id in `nebula_launcher/config.py` →
`MS_CLIENT_ID`. Instructions: https://wiki.vg/Microsoft_Authentication_Scheme

## Mod loaders
Vanilla versions are fully supported out of the box. Forge/Fabric/Quilt installers
are not implemented yet — instances currently launch vanilla only. This is the
natural next thing to add (see `nebula_launcher/mojang_api.py` for where the
version-json pipeline lives; a loader installer would inject its own version json
the same way vanilla ones are downloaded).

## Publishing releases via GitHub Actions
This repo ships `.github/workflows/build.yml`. It builds a standalone binary
for Windows, macOS and Linux with PyInstaller and attaches them to a GitHub
Release automatically.

1. Create a new repo on GitHub and push this project:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Nebula Launcher"
   git branch -M main
   git remote add origin https://github.com/<you>/nebula-launcher.git
   git push -u origin main
   ```
2. Push a version tag to trigger a build + release:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```
3. Check the **Actions** tab — three jobs build in parallel (Windows/macOS/Linux),
   then a `release` job collects the zips and publishes a GitHub Release with
   `NebulaLauncher-windows.zip`, `NebulaLauncher-macos.zip`, `NebulaLauncher-linux.zip`.
4. You can also trigger a build without tagging via **Actions → Build & Release →
   Run workflow** (`workflow_dispatch`) — useful for testing before your first release.

Licensed under **GPL-3.0** (see `LICENSE`) — same license PolyMC/Prism Launcher use.

## Project layout
```
nebula_launcher/
  config.py            paths & constants
  mojang_api.py         version manifest + version json + download URLs
  downloader.py         concurrent file downloader with progress callback
  instance.py            Instance model + InstanceManager (create/list/delete)
  auth.py                 offline profile + Microsoft device-code auth
  launcher_process.py    builds the java command line and launches the game
  ui/
    theme.py              PolyMC-like dark stylesheet
    main_window.py         main window: instance grid + toolbar
    instance_widget.py     single instance tile
    add_instance_dialog.py "new instance" dialog (version picker)
    settings_dialog.py     per-instance settings
    console_window.py      live game log window
```
