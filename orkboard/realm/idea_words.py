"""The words New idea completes with (the phone's idea field): a goal's own terms, from what is written about it; and
a short name (docs/specs/41-phone-round-3.md §3): an idea's, a goal's or a task's name that fits its chip.

    words(["Ship the offline mode: the SyncQueue …", …], phrases=["Offline mode", …])
        # ["Offline mode", "SyncQueue", "offline", …]: the phrases first, then the words, the most used first
    short_of("Давай сделаем тёмную тему в настройках")      # "Сделаем тёмную тему"
    short_said("Dark mode", "Add a dark mode toggle")     # the model's short name when it fits, else short_of(title)

A word is one of at least MIN_CHARS letters, or a name of the code (`sync_queue`, `docs/plan.md`, `SyncQueue`), in
any script; the common words of English and Russian are left out. The same word in other cases is one, written as
it is written most (in lower case on a tie: a capital is most often a sentence's first word). No face, no model.
"""
from __future__ import annotations

import re
from collections import Counter

MIN_CHARS = 4
MAX_WORDS = 200
PHRASE_CHARS = 60
_WORD = re.compile(r"[^\W\d_](?:[\w./-]*\w)?")
_CODE = re.compile(r"[_./]|[a-zа-я][A-ZА-Я]")              # snake_case, a path or a file, camelCase

COMMON = frozenset("""
about above after again against also among another anything around because been before being below between both
cannot could does doing done down during each either else enough even ever every few first from further have having
here into itself just know last least less like made make many maybe more most much must need never next once only
other ought ours over same shall should since some such than that their theirs them then there these they thing
things this those though through thus under until upon very want were what when where whether which while whom
whose will with within without would your yours able also back come came give goes going good great keep left let
look make much really right said says show still take tell time used uses using well what work works
этот эта это эти того тому этого этой этих этим также тоже чтобы когда который которая которое которые если после
перед через только более менее очень всех всем весь вся всё все может можно нужно надо есть было были будет будут
быть него нему неё ними них свой своя своё свои себя тебя меня нами вами какой какая какое какие такой такая такое
такие где куда откуда почему зачем потому поэтому пока ещё уже даже лишь именно вот здесь там тут сейчас теперь
тогда всегда никогда иногда часто между около против без для или либо ни что как так кто чем при над под про
""".split())


def _words(text: str) -> list[str]:
    out = []
    for w in _WORD.findall(text or ""):
        w = w.strip(".-/")
        if not w or w.lower() in COMMON:
            continue
        if len(w) >= MIN_CHARS or _CODE.search(w):
            out.append(w)
    return out


def words(texts: list[str], phrases: list[str] = (), limit: int = MAX_WORDS) -> list[str]:
    """The phrases (titles) first, as written; then the words of the texts, the most used first."""
    seen: set[str] = set()
    out: list[str] = []
    for p in phrases:
        p = " ".join(str(p or "").split())
        if p and len(p) <= PHRASE_CHARS and p.lower() not in seen:
            seen.add(p.lower())
            out.append(p)
    counts: Counter[str] = Counter()
    forms: dict[str, Counter[str]] = {}
    for t in texts:
        for w in _words(t):
            counts[w.lower()] += 1
            forms.setdefault(w.lower(), Counter())[w] += 1
    for low, _n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        if low not in seen:
            seen.add(low)
            out.append(min(forms[low].items(), key=lambda f: (-f[1], f[0] != low))[0])      # a tie: as in a sentence's middle
    return out[:limit]


# -- a short name (spec 41 §3) ---------------------------------------------------------------------------------------

SHORT_CHARS = 24
SHORT_WORDS = 4                       # the most a model's short name may have
# What a request starts with before what it asks for: left out of a short name (lower case, the longest first).
ASKING = ("i would like to", "i'd like to", "we need to", "we should", "i want to", "could we", "can we", "let's",
          "let us", "please", "maybe", "хотелось бы", "может быть", "пожалуйста", "давайте", "давай", "нужно", "надо",
          "хочу", "может", "можно")
# What a short name never ends with: it reads as cut in a sentence's middle.
_DANGLING = frozenset("""a an the to of in on at by for from with and or but as into
и в во на с со к ко по о об у для из от до а но или же""".split())
_SENTENCE_END = re.compile(r"[.!?…:;](?=\s|$)|\n")
_LEAD = re.compile(r"^[\s\-–—*#>\"'«“(\[]+")


def _drop_asking(text: str) -> str:
    """`text` without the asking words at its start ("Давай, может, сделаем …" → "сделаем …")."""
    while True:
        low = text.lower()
        hit = next((a for a in ASKING if low.startswith(a) and (len(low) == len(a) or not low[len(a)].isalnum())), "")
        if not hit:
            return text
        text = text[len(hit):].lstrip(" ,.!—–-")


def short_of(text: str, limit: int = SHORT_CHARS) -> str:
    """A name of at most `limit` characters from `text`, no model: its first sentence (Markdown's marks left out), the
    asking words at its start left out, its first letter in capital (a name of the code as it is written), cut at a
    word's end (no "…") and never on a word that leaves it dangling; a first word longer than `limit` gives its file's
    name when it is a path, else is cut. "" only for a text with no words."""
    plain = str(text or "").replace("*", "").replace("`", "")
    first = _SENTENCE_END.split(_LEAD.sub("", plain).strip(), 1)[0]
    words = _drop_asking(" ".join(first.split())).split() or " ".join(plain.split()).split()
    if not words:
        return ""
    out: list[str] = []
    for w in words:
        if len(" ".join([*out, w])) > limit:
            break
        out.append(w)
    while len(out) > 1 and out[-1].lower().strip(",") in _DANGLING:
        out.pop()
    name = " ".join(out).rstrip(",;:—–-") if out else words[0].rstrip("/").rsplit("/", 1)[-1][:limit]
    return name if _CODE.search(name.split()[0]) else name[:1].upper() + name[1:]


def short_said(said: object, title: str, limit: int = SHORT_CHARS) -> str:
    """A model's short name, strictly: at most `limit` characters and SHORT_WORDS words; else `short_of(title)`."""
    name = " ".join(str(said or "").split()) if isinstance(said, str) else ""
    if name and len(name) <= limit and len(name.split()) <= SHORT_WORDS:
        return name
    return short_of(title, limit)
