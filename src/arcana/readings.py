"""Original offline reflections and a shared, concrete invitation for AI readings."""

from .deck import Card, Deck
from .draw import Draw

# Actions are optional, ordinary rituals: no supplies, belief, or purchases needed.
PRACTICES = {
    "wands": ("Give an idea five unhurried minutes. Stop with enough energy to return tomorrow.", "What deserves a little of your fire, and what is only asking for your urgency?"),
    "cups": ("Put a feeling into one honest sentence. You can keep the sentence to yourself.", "What would care look like here if it made room for your feelings too?"),
    "swords": ("Write two short lines: what you know, and what you are assuming. Leave a little space between them.", "Which part of the story would change if one assumption softened?"),
    "coins": ("Tend one small thing within reach: a surface, a meal, a message, or a neglected task.", "What modest act would make tomorrow feel a little more supported?"),
}
MAJOR_PRACTICES = [
    ("Take one reversible first step toward something unfamiliar.", "What could you begin without needing to know the whole path?"),
    ("Choose one tool you already have and use it for five focused minutes.", "What becomes possible when you use what is already in your hands?"),
    ("Spend a minute without input, then write down what keeps returning to your attention.", "What is easier to hear when you leave a little silence?"),
    ("Give a living thing, a project, or yourself one undistracted act of care.", "What is asking to be nourished rather than hurried?"),
    ("Make one boundary clear enough that you do not have to keep defending it.", "Which structure supports you, and which one asks too much?"),
    ("Write down one rule you inherited and the reason you would choose it today.", "What would you keep from the tradition if keeping it were a choice?"),
    ("Name one value before making an ordinary choice today.", "Which choice feels more like a promise you want to keep?"),
    ("Choose one direction for the next ten minutes and let the other directions wait.", "What are you trying to move toward, beneath the effort to keep moving?"),
    ("Relax your shoulders before returning to a difficult task or conversation.", "Where might a gentler kind of strength be enough?"),
    ("Take a short interval alone without asking it to produce an answer.", "Which question deserves your own company for a while?"),
    ("Name one thing you can influence and one thing you can let turn without you.", "What opening becomes visible when control loosens a little?"),
    ("Describe a decision once from each person's position, including your own.", "What would fairness require you to notice before deciding?"),
    ("Describe a stuck situation from an unfamiliar angle before trying to solve it.", "What becomes visible if the pause is allowed to change your perspective?"),
    ("Finish or release one small thing that has already reached its ending.", "What needs a clean ending before the next beginning can breathe?"),
    ("Adjust one part of your day by a small amount instead of overhauling it.", "What would a sustainable middle feel like in practice?"),
    ("Notice one automatic habit and leave a brief pause before following it.", "What choice might still be available inside this familiar pattern?"),
    ("Name one thing that remains dependable while something else changes.", "What can you build from what is still true?"),
    ("Return to one modest source of restoration without requiring it to fix everything.", "What small hope feels worth tending today?"),
    ("Write a feeling and a fact on separate lines; give each room to exist.", "What can remain uncertain while you take the next careful step?"),
    ("Let yourself enjoy one ordinary good thing without making it productive.", "What light is already here that you have been moving too quickly to notice?"),
    ("Write one sentence about what you are ready to answer differently.", "What would you choose if an old verdict no longer had the final word?"),
    ("Mark one completion, however small, before opening the next task.", "What deserves recognition before you move on?"),
]


def invitation(card: Card) -> tuple[str, str]:
    suit, rank = card.id.split("-")
    return MAJOR_PRACTICES[int(rank)] if suit == "major" else PRACTICES[suit]


def spread_thread(draw: Draw) -> str:
    suits = {pick.card_id.split("-")[0] for pick in draw.picks}
    if suits == {"major"}:
        return "Three major arcana make a wide sky over this reading. Give the larger pattern some room before reducing it to today's task."
    if len(suits) == 1:
        lens = {"wands": "fire and initiative", "cups": "water and connection", "swords": "air and discernment", "coins": "earth and practical care"}[next(iter(suits))]
        return f"The shared suit gives the spread one recurring texture: {lens}. Notice how that same concern changes from situation to tension to invitation."
    if "major" in suits:
        return "A larger life theme meets the texture of an ordinary day. Let the smaller, practical card details give that larger theme somewhere to land."
    pairs = {
        frozenset(("wands", "cups")): "Desire and feeling meet here. Give an impulse enough attention to discover what it cares about.",
        frozenset(("wands", "swords")): "An impulse meets an argument. Let clarity give the energy a direction it can sustain.",
        frozenset(("wands", "coins")): "A spark meets the work of keeping it alive. Give enthusiasm a practical place to land.",
        frozenset(("cups", "swords")): "Feeling and analysis share the table. Give each a voice before asking either to decide alone.",
        frozenset(("cups", "coins")): "Care wants a tangible form here. Notice how time, attention, and ordinary support can carry a feeling.",
        frozenset(("swords", "coins")): "An idea meets its everyday consequences. Try giving one clear thought a small, practical test.",
    }
    return pairs.get(frozenset(suits), "The spread crosses several kinds of attention. Look for the place where intention, feeling, thought, or practical care can help one another.")


def local_reading(draw: Draw, deck: Deck) -> str:
    cards = [deck.by_id(pick.card_id) for pick in draw.picks]
    names = [f"{card.name} ({'reversed' if pick.reversed else 'upright'})" for card, pick in zip(cards, draw.picks)]
    meanings = [card.meaning(pick.reversed) for card, pick in zip(cards, draw.picks)]
    practice, question = invitation(cards[-1])
    if len(cards) == 1:
        thread = f"{names[0]}\n{meanings[0]}"
    else:
        thread = (f"Read together, {names[0]} opens the scene: {meanings[0]} "
                  f"{names[1]} puts pressure on that opening: {meanings[1]} "
                  f"{names[2]} offers a way to respond: {meanings[2]}\n\n{spread_thread(draw)}")
    reversed_count = sum(pick.reversed for pick in draw.picks)
    if reversed_count:
        thread += " Let the reversed " + ("card mark" if reversed_count == 1 else "cards mark") + " a place to listen inward, adjust the pace, or try another approach."
    return f"The thread\n{thread}\n\nA small ritual\n{practice}\n\nA question to carry\n{question}"
