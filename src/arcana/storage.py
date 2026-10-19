"""Private configuration and atomic daily state. No questions or readings."""

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import tomllib
from zoneinfo import ZoneInfo

from .deck import Deck
from .draw import Draw, create


def config_path() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/arcana/config.toml"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "arcana/config.toml"


def data_path() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/arcana/state"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "arcana"


@dataclass(frozen=True)
class Config:
    art_dir: str | None = None
    provider: str = "none"
    argv: tuple[str, ...] = ()
    timeout: float = 45
    timezone: str | None = None


def load_config(path: Path | None = None) -> Config:
    path = path or config_path()
    if not path.exists():
        return Config()
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
        if set(data) - {"art_dir", "provider", "argv", "timeout", "timezone"}:
            raise ValueError("unknown configuration key")
        for key in ("art_dir", "provider", "timezone"):
            if key in data and not isinstance(data[key], str):
                raise ValueError("configuration strings must be text")
        argv = data.get("argv", [])
        if not isinstance(argv, list) or not all(isinstance(x, str) and "\0" not in x for x in argv):
            raise ValueError("argv must be an array of strings")
        timeout = data.get("timeout", 45)
        if type(timeout) not in (int, float) or not 0 < timeout <= 600:
            raise ValueError("timeout must be between 0 and 600 seconds")
        return Config(data.get("art_dir"), data.get("provider", "none"), tuple(argv), timeout, data.get("timezone"))
    except (OSError, ValueError, TypeError) as error:
        raise ValueError("Cannot read configuration; check TOML keys and value types") from error


def today(timezone: str | None = None) -> tuple[str, str]:
    if timezone:
        now = datetime.now(ZoneInfo(timezone))
        return now.date().isoformat(), timezone
    now = datetime.now().astimezone()
    # The TZ setting captures named zones; otherwise include the resolved local
    # offset to keep launch identity explicit, including daylight-saving changes.
    return now.date().isoformat(), os.environ.get("TZ", str(now.tzinfo))


@contextmanager
def locked(root: Path):
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(root / "state.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def atomic(path: Path, value: dict):
    fd, name = tempfile.mkstemp(prefix=".state-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(value, handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def daily(deck: Deck, date: str, timezone: str, upright_only: bool, root: Path | None = None) -> Draw:
    root = root or data_path()
    with locked(root):
        statefile = root / "daily.json"
        try:
            state = json.loads(statefile.read_text()) if statefile.exists() else {"identity": secrets.token_hex(32), "draws": {}}
            if not isinstance(state, dict):
                raise ValueError("invalid daily state")
            identity_hex = state.get("identity")
            if not isinstance(identity_hex, str):
                raise ValueError("invalid daily state")
            identity = bytes.fromhex(identity_hex)
            if len(identity) != 32 or not isinstance(state["draws"], dict):
                raise ValueError("invalid daily state")
            key = json.dumps([date, timezone, deck.fingerprint, upright_only], separators=(",", ":"))
            if key in state["draws"]:
                draw = Draw.from_dict(state["draws"][key], deck)
                if draw.mode != "daily" or draw.date != date or draw.timezone != timezone or (upright_only and any(p.reversed for p in draw.picks)):
                    raise ValueError("daily identity mismatch")
                return draw
            draw = create(deck, 1, identity, "daily", date, timezone, upright_only)
            state["draws"][key] = draw.public()
            atomic(statefile, state)
            return draw
        except (OSError, ValueError, TypeError, KeyError) as error:
            raise ValueError("Cannot read or write daily state; inspect daily.json (it was not replaced)") from error
