#!/usr/bin/env python3
"""Bereinigt die IMDb-Top-250-M3U.

Was repariert wird:
  1. Nur echte Videodateien behalten (.mp4/.mkv/.avi/.mov/.m4v/.ts)
     → .srt/.sub/.jpg/.nfo/.txt-Einträge fliegen raus
  2. Saubere Anzeigenamen aus dem Pfad ableiten (Filmordner)
     → '12 Years a Slave (2013)' statt der URL als Name
  3. Duplikate entfernen (derselbe Titel mehrfach)
  4. Gruppen-Titel setzen ('Filme bis 2020')
  5. UTF-8 sauber schreiben, CRLF-frei

Ergebnis: imdb250-clean.m3u neben der Quelldatei.
"""
import re
import urllib.parse
from collections import Counter, OrderedDict
from pathlib import Path

BASE = Path("/home/momo/Filme/beste Filme bis 2020")
SRC = BASE / "imdb250.m3u"
OUT = BASE / "imdb250-clean.m3u"

VIDEO = (".mp4", ".mkv", ".avi", ".mov", ".m4v", ".ts")
QUALITY_RE = re.compile(
    r"\b(2160p|1080p|720p|480p|BluRay|BRRip|BDRip|WEB-?DL|WEBRip|HDTV|"
    r"x264|x265|H\.?264|H\.?265|HEVC|AAC|AC3|DTS|DD5|5\.1|10bit|8bit|"
    r"EXTENDED|REMASTERED|PROPER|REPACK|iNTERNAL|REMUX|RARBG|YIFY|DDN|"
    r"Ozlem|NTb|Ganool|ShAaNiG|Hon3y|Darkside|RG)\b",
    re.IGNORECASE,
)


def is_video(u: str) -> bool:
    path = urllib.parse.unquote(u).split("?")[0]
    return path.lower().endswith(VIDEO)


def clean_title(u: str) -> str:
    """Aus der URL einen lesbaren Titel bauen."""
    path = urllib.parse.unquote(u).split("?")[0]
    parts = [x for x in path.split("/") if x]
    # Der Filmordner ist das Verzeichnis über der Datei. Wenn dieser nur
    # technisch ist, stattdessen den Dateinamen nehmen.
    folder = parts[-2] if len(parts) >= 2 else ""
    name = parts[-1]
    name = re.sub(r"\.(mp4|mkv|avi|mov|m4v|ts)$", "", name, flags=re.I)

    cand = folder or name
    # Ordner wie 'RARBG.COM' oder 'Subtitles Eng […]' sind keine Titel
    if not cand or len(cand) < 3 or re.fullmatch(r"[A-Z.\-]+(COM)?", cand):
        cand = name

    t = cand
    t = re.sub(r"(%5b|\[)[^%\]]*(%5d|\])", " ", t, flags=re.I)   # [1080p] / %5b..%5d
    t = re.sub(r"\b\d{3,4}p\b", " ", t)
    t = QUALITY_RE.sub(" ", t)
    t = t.replace(".", " ").replace("_", " ").replace("-", " ")
    # Sprach-/Quellenanhängsel am Ende entfernen
    t = re.sub(
        r"\b(English|Englisch|Hindi|Italian|Japanese|French|German|Spanish|KORSUB|"
        r"Eng|Fre|Ger|Spa|Subs?|Dual|Audio)\b\.?$",
        " ", t, flags=re.I)
    # Nicht darstellbare Zeichen (kaputtes Encoding in der Quelle)
    t = t.replace("\ufffd", "").replace("?", "")
    # Führende Artikel-/Zahlenreste wie "8�" → behalten, aber bereinigen
    t = re.sub(r"\s{2,}", " ", t).strip(" -_·,.")
    # Jahreszahl am Ende in Klammern doppelt vermeiden
    t = re.sub(r"\s*\((19\d{2}|20\d{2})\)\s*$", "", t)
    t = re.sub(r"\s*[.\s](19\d{2}|20\d{2})\s*$", "", t)
    return t.strip(" -_·,.") or name


def year(u: str):
    path = urllib.parse.unquote(u)
    m = re.search(r"\((\d{4})\)", path)
    if not m:
        m = re.search(r"[.\s_\[(](19\d{2}|20\d{2})[.\s_\])]", path)
    if not m:
        return None
    y = int(m.group(1))
    return y if 1900 <= y <= 2020 else None


def main():
    if not SRC.exists():
        raise SystemExit(f"Quelle fehlt: {SRC}")

    lines = SRC.read_text(encoding="utf-8", errors="replace").split("\n")
    raw = []
    for i, l in enumerate(lines):
        if l.startswith("#EXTINF"):
            u = next((x.strip() for x in lines[i + 1:i + 3] if x.strip().startswith("http")), "")
            if u:
                raw.append(u)

    videos = [u for u in raw if is_video(u)]
    dropped_format = len(raw) - len(videos)

    # Duplikate: gleicher bereinigter Titel + gleiches Jahr
    seen, kept, dropped_dup = OrderedDict(), [], 0
    for u in videos:
        t = clean_title(u)
        y = year(u)
        key = (re.sub(r"[^a-z0-9]", "", t.lower()), y)
        if key in seen:
            dropped_dup += 1
            continue
        seen[key] = True
        kept.append((t, y, u))

    kept.sort(key=lambda x: (x[0].lower(), x[1] or 0))

    out = ["#EXTM3U", "x-tvg-url".replace("x-tvg-url", "# Filme bis 2020 (Englisch)")]
    for t, y, u in kept:
        label = f"{t} ({y})" if y else t
        out.append(f'#EXTINF:-1 group-title="Filme bis 2020",{label}')
        out.append(u)
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")

    print(f"Quelle        : {len(raw)} Einträge")
    print(f"  − Nicht-Video: {dropped_format}")
    print(f"  − Duplikate  : {dropped_dup}")
    print(f"fertig        : {len(kept)} Filme → {OUT.name}")
    print("\nBeispiele:")
    for t, y, u in kept[:8]:
        print(f"   {t} ({y})" if y else f"   {t}")


if __name__ == "__main__":
    main()
