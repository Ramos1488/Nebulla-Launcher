"""Offline ('cracked') accounts + Microsoft OAuth device-code login chain."""
from __future__ import annotations
import json
import time
import uuid
import requests
from dataclasses import dataclass, asdict
from typing import Callable, Optional

from . import config


@dataclass
class Account:
    kind: str          # "offline" or "microsoft"
    username: str
    uuid: str
    access_token: str = ""
    refresh_token: str = ""
    expires_at: float = 0.0


def offline_account(username: str) -> Account:
    # Deterministic offline UUID, same scheme vanilla launchers use for cracked play.
    offline_uuid = uuid.uuid3(uuid.NAMESPACE_DNS, f"OfflinePlayer:{username}")
    return Account(kind="offline", username=username, uuid=str(offline_uuid))


def load_accounts() -> list[Account]:
    if not config.ACCOUNTS_FILE.exists():
        return []
    data = json.loads(config.ACCOUNTS_FILE.read_text(encoding="utf-8"))
    return [Account(**a) for a in data]


def save_accounts(accounts: list[Account]) -> None:
    config.ACCOUNTS_FILE.write_text(
        json.dumps([asdict(a) for a in accounts], indent=2), encoding="utf-8"
    )


def add_account(account: Account) -> None:
    accounts = [a for a in load_accounts() if a.uuid != account.uuid]
    accounts.append(account)
    save_accounts(accounts)


# --------------------------------------------------------------------------
# Microsoft device-code flow -> Xbox Live -> XSTS -> Minecraft services
# --------------------------------------------------------------------------

class MicrosoftLoginError(RuntimeError):
    pass


def start_device_code() -> dict:
    r = requests.post(
        config.MS_DEVICE_CODE_URL,
        data={"client_id": config.MS_CLIENT_ID, "scope": "XboxLive.signin offline_access"},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()  # contains device_code, user_code, verification_uri, interval, expires_in


def poll_device_code(device_code: str, interval: int, expires_in: int,
                      on_tick: Optional[Callable[[], None]] = None) -> dict:
    deadline = time.time() + expires_in
    while time.time() < deadline:
        time.sleep(interval)
        if on_tick:
            on_tick()
        r = requests.post(
            config.MS_TOKEN_URL,
            data={
                "client_id": config.MS_CLIENT_ID,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
            },
            timeout=20,
        )
        payload = r.json()
        if r.status_code == 200:
            return payload
        err = payload.get("error")
        if err == "authorization_pending":
            continue
        if err == "authorization_declined":
            raise MicrosoftLoginError("Login was declined.")
        if err == "expired_token":
            raise MicrosoftLoginError("Device code expired, please try again.")
        raise MicrosoftLoginError(f"Microsoft login error: {err}")
    raise MicrosoftLoginError("Timed out waiting for login.")


def _xbl_authenticate(ms_access_token: str) -> dict:
    r = requests.post(
        config.XBL_AUTH_URL,
        json={
            "Properties": {
                "AuthMethod": "RPS",
                "SiteName": "user.auth.xboxlive.com",
                "RpsTicket": f"d={ms_access_token}",
            },
            "RelyingParty": "http://auth.xboxlive.com",
            "TokenType": "JWT",
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def _xsts_authorize(xbl_token: str) -> dict:
    r = requests.post(
        config.XSTS_AUTH_URL,
        json={
            "Properties": {"SandboxId": "RETAIL", "UserTokens": [xbl_token]},
            "RelyingParty": "rp://api.minecraftservices.com/",
            "TokenType": "JWT",
        },
        timeout=20,
    )
    if r.status_code == 401:
        body = r.json()
        code = body.get("XErr")
        if code == 2148916233:
            raise MicrosoftLoginError("This Microsoft account has no Xbox profile. Create one at xbox.com first.")
        if code == 2148916238:
            raise MicrosoftLoginError("This account is a child account and needs to be added to a Family group.")
        raise MicrosoftLoginError(f"Xbox Live rejected the login (XErr {code}).")
    r.raise_for_status()
    return r.json()


def login_microsoft_full(on_code: Callable[[str, str], None],
                          on_tick: Optional[Callable[[], None]] = None) -> Account:
    """Full chain. on_code(user_code, verification_uri) is called so the UI can show it."""
    dc = start_device_code()
    on_code(dc["user_code"], dc["verification_uri"])
    token_payload = poll_device_code(dc["device_code"], dc.get("interval", 5), dc.get("expires_in", 900), on_tick)

    ms_access_token = token_payload["access_token"]
    ms_refresh_token = token_payload.get("refresh_token", "")

    xbl = _xbl_authenticate(ms_access_token)
    xbl_token = xbl["Token"]
    user_hash = xbl["DisplayClaims"]["xui"][0]["uhs"]

    xsts = _xsts_authorize(xbl_token)
    xsts_token = xsts["Token"]

    mc_login = requests.post(
        config.MC_LOGIN_URL,
        json={"identityToken": f"XBL3.0 x={user_hash};{xsts_token}"},
        timeout=20,
    )
    mc_login.raise_for_status()
    mc_payload = mc_login.json()
    mc_access_token = mc_payload["access_token"]

    profile_r = requests.get(
        config.MC_PROFILE_URL,
        headers={"Authorization": f"Bearer {mc_access_token}"},
        timeout=20,
    )
    if profile_r.status_code == 404:
        raise MicrosoftLoginError("This account doesn't own Minecraft.")
    profile_r.raise_for_status()
    profile = profile_r.json()

    account = Account(
        kind="microsoft",
        username=profile["name"],
        uuid=profile["id"],
        access_token=mc_access_token,
        refresh_token=ms_refresh_token,
        expires_at=time.time() + mc_payload.get("expires_in", 86400),
    )
    add_account(account)
    return account
