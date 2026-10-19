"""Versioned reproducible selection, independent of screen and providers."""

from dataclasses import asdict, dataclass
from hashlib import sha256
import hmac
import json
import unicodedata

from .deck import Deck

ALGORITHM = "arcana/draw/v1"


@dataclass(frozen=True)
class Pick:
    card_id: str
    reversed: bool
    position: str


@dataclass(frozen=True)
class Draw:
    algorithm: str
    deck: str
    mode: str
    date: str | None
    timezone: str | None
    picks: tuple[Pick, ...]

    def public(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict, deck: Deck) -> "Draw":
        picks = tuple(Pick(**p) for p in data["picks"])
        ids = {c.id for c in deck.cards}
        if (data["algorithm"] != ALGORITHM or data["deck"] != deck.fingerprint
                or len(picks) != 1 or len({p.card_id for p in picks}) != len(picks)
                or any(p.card_id not in ids or type(p.reversed) is not bool for p in picks)):
            raise ValueError("invalid stored draw")
        return cls(data["algorithm"], data["deck"], data["mode"], data["date"], data["timezone"], picks)


class Stream:
    def __init__(self, key: bytes, domain: bytes):
        self.key, self.domain, self.counter, self.buffer = key, domain, 0, b""

    def bounded(self, bound: int) -> int:
        limit = (2 ** 32 // bound) * bound
        while True:
            if len(self.buffer) < 4:
                self.buffer += hmac.digest(self.key, self.domain + self.counter.to_bytes(8, "big"), "sha256")
                self.counter += 1
            number = int.from_bytes(self.buffer[:4], "big")
            self.buffer = self.buffer[4:]
            if number < limit:
                return number % bound


def normalize(word: str) -> str:
    return unicodedata.normalize("NFC", word).strip()


def create(deck: Deck, count: int, material: bytes | str, mode: str, date: str | None = None, timezone: str | None = None, upright_only: bool = False) -> Draw:
    if count not in (1, 3):
        raise ValueError("draw count must be 1 or 3")
    payload = {"algorithm": ALGORITHM, "deck": deck.fingerprint, "count": count, "upright_only": upright_only, "mode": mode, "material_kind": "word" if isinstance(material, str) else "bytes", "material": normalize(material) if isinstance(material, str) else material.hex()}
    if date is not None:
        payload.update(date=date, timezone=timezone)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    key = sha256(ALGORITHM.encode() + b"\0" + canonical).digest()
    shuffle, orientations = Stream(key, b"shuffle"), Stream(key, b"orientation")
    ids = [card.id for card in deck.cards]
    for i in range(len(ids) - 1, 0, -1):
        j = shuffle.bounded(i + 1)
        ids[i], ids[j] = ids[j], ids[i]
    positions = ("Today",) if count == 1 else ("Situation", "Tension", "Invitation")
    return Draw(ALGORITHM, deck.fingerprint, mode, date, timezone, tuple(Pick(card_id, False if upright_only else bool(orientations.bounded(2)), pos) for card_id, pos in zip(ids[:count], positions)))
