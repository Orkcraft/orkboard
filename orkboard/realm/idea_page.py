"""A board page as text: front matter, a title and `##` sections (split from ideas.py).

    page = parse(text)                    # nothing it does not know is lost
    page.set_section("Risks", "…")        # a missing known section goes after the last known one before it
    page.text()                           # … written back with every key and section kept

`Page` and `parse` read and write a page; `clean_text` makes a section safe to write into one (a model's answer is
untrusted); `thesis`, `items` and `slugify` read a section's first line, its list and a title's slug. The tracks,
ideas and their files stay in realm/ideas.py, which re-exports every name here. No face, no model.
"""
from __future__ import annotations

import datetime as dt
import re
import unicodedata

SECTIONS = ("Gist", "Why", "Done when", "Out", "Risks", "Depends on", "Stages", "Open questions", "Decisions")   # spec 35 §3
SECTION_CHARS = 20_000           # of a section, the most a write keeps
_FENCE = re.compile(r"\A---\n(.*?)\n---\n?", re.S)
_HEADING = re.compile(r"^(#{1,2})[ \t]+(.+?)[ \t]*#*[ \t]*$", re.M)
_KEY = re.compile(r"^([A-Za-z_][\w-]*):[ \t]*(.*)$")


# -- a page: front matter, a title, sections --------------------------------------------------------

class Page:
    """A Markdown page as the board reads it: front matter (`meta`, its order and its unknown lines kept), the `#`
    title, what stands before the first `##` (`head`), and the `##` sections in the order they are written."""

    def __init__(self, meta: list[tuple[str, str]] | None = None, title: str = "", head: str = "",
                 sections: list[tuple[str, str]] | None = None) -> None:
        self.meta = list(meta or [])         # (key, value); a line that is no `key: value` is kept as ("", line)
        self.title = title
        self.head = head
        self.sections = list(sections or [])

    def get(self, key: str, default: str = "") -> str:
        return next((v for k, v in self.meta if k == key), default)

    def set(self, key: str, value: object) -> None:
        value = "" if value is None else str(value)
        for i, (k, _v) in enumerate(self.meta):
            if k == key:
                self.meta[i] = (key, value)
                return
        self.meta.append((key, value))

    def section(self, name: str) -> str:
        return next((t for n, t in self.sections if n.lower() == name.lower()), "")

    def set_section(self, name: str, text: str, order: tuple[str, ...] = SECTIONS) -> None:
        text = clean_text(text)
        for i, (n, _t) in enumerate(self.sections):
            if n.lower() == name.lower():
                self.sections[i] = (n, text)
                return
        # a missing known section goes after the last known one that comes before it
        at = len(self.sections)
        if name in order:
            before = order[:order.index(name)]
            at = max((i + 1 for i, (n, _t) in enumerate(self.sections) if n in before), default=0)
        self.sections.insert(at, (name, text))

    def text(self) -> str:
        meta = "\n".join(f"{k}: {v}".rstrip() if k else v for k, v in self.meta)
        out = f"---\n{meta}\n---\n"
        if self.title:
            out += f"# {self.title}\n"
        if self.head.strip():
            out += f"\n{self.head.strip()}\n"
        for name, text in self.sections:
            out += f"\n## {name}\n" + (f"{text.strip()}\n" if text.strip() else "")
        return out


def parse(text: str) -> Page:
    """A page as written, by hand or by the board: nothing it does not know is lost."""
    text = text.replace("\r\n", "\n")
    meta: list[tuple[str, str]] = []
    m = _FENCE.match(text)
    if m:
        for line in m.group(1).split("\n"):
            km = _KEY.match(line)
            meta.append((km.group(1), km.group(2).strip()) if km else ("", line))
        text = text[m.end():]
    title, head, sections = "", [], []
    current: list[str] | None = None
    for line in text.split("\n"):
        hm = _HEADING.match(line)
        if hm and len(hm.group(1)) == 1 and not title and current is None:
            title = hm.group(2).strip()
            continue
        if hm and len(hm.group(1)) == 2:
            current = []
            sections.append((hm.group(2).strip(), current))
            continue
        (head if current is None else current).append(line)
    return Page(meta, title, "\n".join(head).strip(), [(n, "\n".join(lines).strip()) for n, lines in sections])


def clean_text(text: str) -> str:
    """A section's text as it may be written into a page: a `#` or `##` heading inside it is made a `###` one, so a
    section never splits the page (a model's answer is untrusted, a person may paste anything)."""
    text = str(text or "").replace("\r\n", "\n")[:SECTION_CHARS]
    text = re.sub(r"^#{1,2}(?=[ \t])", "###", text, flags=re.M)
    return re.sub(r"^---[ \t]*$", "- - -", text, flags=re.M).strip()


def thesis(text: str) -> str:
    """The first line of a section, without Markdown: its bold thesis."""
    for line in (text or "").split("\n"):
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^(#+|[-*+]|\d+[.)]|>)\s+", "", line)
        line = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line)
        line = re.sub(r"[*_`~]+", "", line).strip()
        if line:
            return line[:200]
    return ""


def items(text: str) -> list[str]:
    """A section's list (`- x`), or its lines when it has no list."""
    lines = [ln.strip() for ln in (text or "").split("\n") if ln.strip()]
    marked = [re.sub(r"^([-*+]|\d+[.)])\s+", "", ln) for ln in lines if re.match(r"^([-*+]|\d+[.)])\s+", ln)]
    return marked or lines


def slugify(text: str, limit: int = 48) -> str:
    plain = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    words = re.findall(r"[a-z0-9]+", plain)
    out = ""
    for w in words:
        if len(out) + len(w) + 1 > limit:
            break
        out = f"{out}-{w}" if out else w
    return out or "idea"


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _int(value: object, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default
