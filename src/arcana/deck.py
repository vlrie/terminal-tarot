"""Canonical card identities, original fallback meanings, and external art."""

from dataclasses import dataclass, field
from functools import cached_property
from hashlib import sha256
from pathlib import Path
import json
import shutil

from .art import Grid, parse, rotate
from .meanings import MINOR_MEANINGS

MAJORS = [
    ("The Fool", "Begin with curiosity; leave room to learn.", "Pause before the leap; notice what you have overlooked."),
    ("The Magician", "Use the tools already within reach.", "Gather your attention before spending your energy."),
    ("The High Priestess", "Listen for what quiet attention reveals.", "Make space to hear your own judgment."),
    ("The Empress", "Nurture something that needs time to grow.", "Care for the source of your generosity."),
    ("The Emperor", "Build a structure that supports your intention.", "Ask where structure has become rigidity."),
    ("The Hierophant", "Learn from a tradition or a trusted guide.", "Consider which inherited rules still serve you."),
    ("The Lovers", "Choose in agreement with your values.", "Notice a gap between your values and your choices."),
    ("The Chariot", "Bring competing energies toward one direction.", "Find your direction before pressing forward."),
    ("Strength", "Meet difficulty with patience and steadiness.", "Treat vulnerability with the same care as resolve."),
    ("The Hermit", "Step back far enough to see what matters.", "Notice whether solitude has become disconnection."),
    ("Wheel of Fortune", "Respond to the opening a change creates.", "Release the effort to control every turn."),
    ("Justice", "Consider consequences and choose fairly.", "Look again at an assumption about fairness."),
    ("The Hanged Man", "A deliberate pause may reveal another angle.", "Ask what keeps a useful pause from becoming movement."),
    ("Death", "Let an ending make room for what comes next.", "Notice what you are keeping after its season has passed."),
    ("Temperance", "Find a sustainable balance through small adjustments.", "Attend to the place where your pace is unsustainable."),
    ("The Devil", "Name the attachment that narrows your choices.", "A small act of honesty can loosen an old pattern."),
    ("The Tower", "Rebuild from what remains true after disruption.", "Examine what fear of change is holding in place."),
    ("The Star", "Return to a modest source of hope.", "Let restoration be gradual rather than demanded."),
    ("The Moon", "Move carefully while the picture is incomplete.", "Separate a feeling from the evidence around it."),
    ("The Sun", "Let clarity and simple enjoyment guide your attention.", "Make room for joy without requiring perfect conditions."),
    ("Judgement", "Answer a call to look honestly at your life.", "Notice where self-criticism prevents a fresh beginning."),
    ("The World", "Recognize a completion and what it has taught you.", "Give an unfinished ending the attention it needs."),
]
SUITS = [("wands", "initiative"), ("cups", "connection"), ("swords", "discernment"), ("coins", "material care")]
RANKS = ["Ace", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Page", "Knight", "Queen", "King"]


@dataclass(frozen=True)
class Card:
    id: str
    name: str
    filename: str
    upright: str
    reversed: str
    artwork: bytes | Grid = field(default=b"", repr=False)
    source_sha256: str | None = None

    @cached_property
    def grid(self) -> Grid:
        if not isinstance(self.artwork, bytes):
            return self.artwork
        if not self.artwork:
            return ()
        try:
            return parse(self.artwork.decode("utf-8"))[0]
        except (ValueError, UnicodeError) as error:
            raise ValueError(f"Cannot load {self.filename}: {error}") from error

    @cached_property
    def inverted_grid(self) -> Grid:
        return rotate(self.grid)

    def meaning(self, reversed: bool) -> str:
        return self.reversed if reversed else self.upright


@dataclass(frozen=True)
class Deck:
    cards: tuple[Card, ...]
    fingerprint: str
    art_dir: Path | None
    notices: tuple[str, ...]

    @cached_property
    def _index(self) -> dict[str, Card]:
        return {card.id: card for card in self.cards}

    def by_id(self, card_id: str) -> Card:
        return self._index[card_id]


def discover(explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit).expanduser()
        if not p.is_dir():
            raise ValueError("art directory does not exist; pass arttime's textart directory")
        return p
    paths = [Path.home() / ".local/share/arttime/textart", Path("/usr/local/share/arttime/textart"), Path("/usr/share/arttime/textart"), Path("/opt/homebrew/share/arttime/textart")]
    executable = shutil.which("arttime")
    if executable:
        paths.insert(0, Path(executable).resolve().parent.parent / "share/arttime/textart")
    return next((p for p in paths if p.is_dir()), None)


def load(art_dir: str | None = None, major: bool = False) -> Deck:
    definitions = [Card(f"major-{i:02}", name, f"tarot-0major_arcana{i:02}", up, rev) for i, (name, up, rev) in enumerate(MAJORS)]
    if not major:
        for suit_index, (suit, _) in enumerate(SUITS, 1):
            for rank, (name, (upright, reversed)) in enumerate(zip(RANKS, MINOR_MEANINGS[suit], strict=True), 1):
                definitions.append(Card(f"{suit}-{rank:02}", f"{name} of {suit.title()}", f"tarot-{suit_index}{suit}{rank:02}", upright, reversed))
    path = discover(art_dir)
    cards = []
    notices = []
    if path is None:
        notices.append("Art not found. Install arttime or set --art-dir to its textart directory; using text cards.")
    for card in definitions:
        if path:
            try:
                with (path / card.filename).open("rb") as source:
                    data = source.read(256 * 1024 + 1)
                if len(data) > 256 * 1024:
                    raise ValueError("art file exceeds size limit")
                card = Card(card.id, card.name, card.filename, card.upright, card.reversed, data, sha256(data).hexdigest())
            except (OSError, ValueError, UnicodeError) as error:
                raise ValueError(f"Cannot load {card.filename}: {error}") from error
        cards.append(card)
    # Source content is intentionally part of the identity; different art
    # revisions never silently reuse a daily draw from another deck version.
    manifest = [(c.id, c.filename, c.source_sha256) for c in cards]
    fingerprint = sha256(json.dumps(manifest, separators=(",", ":")).encode()).hexdigest()
    return Deck(tuple(cards), fingerprint, path, tuple(notices))
