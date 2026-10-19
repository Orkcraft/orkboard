"""The words New idea completes with (the phone's idea field): a goal's own terms, from what is written about it.

    words(["Ship the offline mode: the SyncQueue …", …], phrases=["Offline mode", …])
        # ["Offline mode", "SyncQueue", "offline", …]: the phrases first, then the words, the most used first

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
