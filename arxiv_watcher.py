#!/usr/bin/env python3
"""
arxiv_watcher.py

Polls arXiv for the past N hours OR since a given date and flags papers about
Kaon physics / CKM / NA62 / KOTO(-II).

- Uses arXiv API (no key) via Atom feed.
- Combines keyword rules + author triggers (weighted higher).
- Downloads PDFs for matched items.
- On macOS, shows a Notification Center alert via osascript (optional).

Examples:
  # Look back 8 hours (typical daily run)
  python arxiv_watcher.py --hours 8 --out ~/Papers/arxiv_hits --notify

  # Historical test since a date
  python arxiv_watcher.py --since 2025-01-01 --out ~/Papers/arxiv_hits --dry
"""
import argparse
import csv
import datetime as dt
from pathlib import Path
import re
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urlencode
import sys
import shutil
import getpass
import os
import textwrap
import json

ARXIV_API = "http://export.arxiv.org/api/query"

STATE_PATH = Path.home() / ".local" / "share" / "arxiv_watcher" / "state.json"

def _load_state():
    p = STATE_PATH
    if not p.exists():
        return {"last_success_iso": None, "seen_ids": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"last_success_iso": None, "seen_ids": []}

def _save_state(state):
    p = STATE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")

def _now_utc():
    return dt.datetime.now(dt.timezone.utc)

def _parse_iso(s):
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None

def format_authors(authors, max_authors=6):
    """Return 'A. First, B. Second, … et al.'; keeps full list for CSV."""
    if not authors:
        return ""
    if len(authors) <= max_authors:
        return ", ".join(authors)
    return ", ".join(authors[:max_authors]) + ", et al."

def term_width(default=120):
    try:
        return shutil.get_terminal_size((default, 20)).columns
    except Exception:
        return default

def wrap_line(s, width):
    if width is None or width <= 0:
        return s
    return "\n     ".join(textwrap.wrap(s, width=width))

PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
   "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>__LABEL__</string>

  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>__HOUR__</integer>
    <key>Minute</key>
    <integer>__MINUTE__</integer>
  </dict>

__START_INTERVAL_BLOCK__

  <key>ProgramArguments</key>
  <array>
    <string>__PYTHON__</string>
    <string>__SCRIPT__</string>
    <string>--hours</string>
    <string>__HOURS_LOOKBACK__</string>
    <string>--out</string>
    <string>__OUT_DIR__</string>
__NOTIFY_ARG__
  </array>

  <key>StandardOutPath</key>
  <string>__LOG_DIR__/arxiv_watcher.out</string>
  <key>StandardErrorPath</key>
  <string>__LOG_DIR__/arxiv_watcher.err</string>

  <!-- Run immediately at load -->
  <key>RunAtLoad</key>
  <true/>

  <!-- Don’t respawn endlessly; only run on schedule + StartInterval -->
  <key>KeepAlive</key>
  <false/>
</dict>
</plist>
"""

def _parse_hhmm(s):
    # "09:30" -> (9, 30)
    parts = s.strip().split(":")
    if len(parts) != 2:
        raise ValueError("Schedule must be HH:MM")
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError("Hour 0–23, Minute 0–59")
    return h, m

def build_plist(
    schedule_hhmm="09:30",
    label="com.arxiv.watcher",
    hours_lookback=24,
    out_dir=None,
    notify=True,
    python_path=None,
    script_path=None,
    log_dir=None,
    backoff_interval=3600,  # seconds; 0 disables StartInterval
):
    # Resolve defaults
    script_path = str(Path(script_path or __file__).resolve())
    python_path = python_path or sys.executable
    out_dir = str(Path(out_dir or (Path.home() / "Papers" / "arxiv_hits")).expanduser().resolve())
    log_dir = str(Path(log_dir or (Path.home() / "Library" / "Logs")).expanduser().resolve())
    hour, minute = _parse_hhmm(schedule_hhmm)

    notify_arg = "      <string>--notify</string>\n" if notify else ""

    if backoff_interval and backoff_interval > 0:
        start_interval_block = f"""  <key>StartInterval</key>
  <integer>{int(backoff_interval)}</integer>"""
    else:
        start_interval_block = ""

    xml = (
        PLIST_TEMPLATE
        .replace("__LABEL__", label)
        .replace("__HOUR__", str(hour))
        .replace("__MINUTE__", str(minute))
        .replace("__PYTHON__", python_path)
        .replace("__SCRIPT__", script_path)
        .replace("__HOURS_LOOKBACK__", str(hours_lookback))
        .replace("__OUT_DIR__", out_dir)
        .replace("__LOG_DIR__", log_dir)
        .replace("__NOTIFY_ARG__", notify_arg)
        .replace("__START_INTERVAL_BLOCK__", start_interval_block)
    )

    plist_name = f"{label}.plist"
    plist_path = Path.cwd() / plist_name
    plist_path.write_text(xml, encoding="utf-8")
    return str(plist_path)

def install_plist(plist_path):
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True, exist_ok=True)
    dest = launch_agents / Path(plist_path).name
    shutil.copy2(plist_path, dest)

    # Try to unload the old job; it's fine if it wasn't loaded
    _ = subprocess.run(
        ["launchctl", "bootout", f"gui/{os.getuid()}", str(dest)],
        check=False, capture_output=True, text=True
    )

    # Load the new job
    r = subprocess.run(
        ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(dest)],
        check=False, capture_output=True, text=True
    )
    if r.returncode != 0:
        raise RuntimeError(f"bootstrap failed: {r.stderr.strip()}")

    return str(dest)

DEFAULT_QUERY = (
    '(cat:hep-ex OR cat:hep-ph OR cat:hep-lat)'
    ' AND (all:kaon OR all:kaons OR all:"CKM" OR all:"Vus" OR all:"|V_us|"'
    ' OR all:NA62 OR all:"KOTO" OR all:"KOTO-II" OR all:KLEVER OR all:HIKE)'
)

def _read_patterns_file(path):
    #Read non-empty, non-comment lines as regex patterns.
    pats = []
    p = Path(path).expanduser()
    if not p.exists():
        print(f"ERROR: patterns file missing: {p}", file=sys.stderr)
        return []
    for raw in p.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        pats.append(s)
    return pats

# Always load from external files
REGEX_PATTERNS = _read_patterns_file(Path(__file__).parent / "patterns" / "keywords.txt")
AUTHOR_PATTERNS = _read_patterns_file(Path(__file__).parent / "patterns" / "authors.txt")

if not REGEX_PATTERNS or not AUTHOR_PATTERNS:
    print("✖ No patterns loaded. Please edit patterns/keywords.txt and patterns/authors.txt")
    sys.exit(1)

def build_url(query, start=0, max_results=100, sort_by="submittedDate", sort_order="descending"):
    params = {
        "search_query": query,
        "start": start,
        "max_results": max_results,
        "sortBy": sort_by,
        "sortOrder": sort_order,
    }
    return f"{ARXIV_API}?{urlencode(params)}"


def fetch_entries_paged(query, since_iso=None, max_per_page=100, max_pages=100):
    """
    Generator over entries, newest first. If since_iso is provided, we sort by lastUpdatedDate
    and can early-stop once entries are older than the cutoff. Otherwise we sort by submittedDate.
    """
    start = 0
    page = 0
    cutoff = None
    if since_iso:
        cutoff = dt.datetime.fromisoformat(since_iso.replace("Z", "+00:00"))

    # --- IMPORTANT FIX: use lastUpdatedDate when since_iso is set ---
    sort_key = "lastUpdatedDate" if since_iso else "submittedDate"

    while page < max_pages:
        url = build_url(query, start=start, max_results=max_per_page,
                        sort_by=sort_key, sort_order="descending")
        try:
            with urllib.request.urlopen(url) as resp:
                data = resp.read()
        except Exception as e:
            # surface a sentinel so the caller knows it was partial
            raise RuntimeError(f"network-error:{e}")
        root = ET.fromstring(data)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        es = root.findall("a:entry", ns)
        if not es:
            break

        for e in es:
            def g(tag):
                x = e.find(f"a:{tag}", ns)
                return x.text if x is not None else ""
            title   = (g("title") or "").strip().replace("\n", " ")
            summary = (g("summary") or "").strip()
            link    = (g("id") or "").strip()
            updated = g("updated") or g("published")

            # --- IMPORTANT FIX: only early-stop when sorting by lastUpdatedDate ---
            if cutoff and sort_key == "lastUpdatedDate":
                try:
                    t = dt.datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    if t < cutoff:
                        return  # safe to stop; feed is descending by updated time
                except Exception:
                    pass

            pdf_url = None
            for l in e.findall("a:link", ns):
                if l.attrib.get("type", "").endswith("pdf"):
                    pdf_url = l.attrib.get("href")
            cats = [c.attrib.get("term", "") for c in e.findall("a:category", ns)]
            authors = []
            for a in e.findall("a:author", ns):
                n = a.find("a:name", ns)
                if n is not None and n.text:
                    authors.append(n.text.strip())
            yield {
                "title": title,
                "summary": summary,
                "link": link,
                "pdf": pdf_url,
                "updated": updated,
                "categories": cats,
                "authors": authors,
            }
        start += max_per_page
        page += 1


def within_hours(iso_ts, hours):
    if not iso_ts:
        return True
    try:
        t = dt.datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except Exception:
        return True
    return (_now_utc() - t).total_seconds() <= hours * 3600


def keyword_score(text):
    score = 0
    for pat in REGEX_PATTERNS:
        if re.search(pat, text, flags=re.IGNORECASE):
            score += 1
    return score


def author_score(authors_list):
    txt = " ; ".join(authors_list)
    score = 0
    for pat in AUTHOR_PATTERNS:
        if re.search(pat, txt, flags=re.IGNORECASE):
            score += 2  # heavier weight for author hits
    return score


def notify_macos(title, subtitle, message):
    # Works on macOS via Notification Center
    try:
        script = f'display notification "{message}" with title "{title}" subtitle "{subtitle}"'
        subprocess.run(["osascript", "-e", script], check=False)
    except Exception:
        pass


def download_pdf(url, out_dir, nice_name):
    if not url:
        return None
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # sanitize filename
    safe = re.sub(r'[^A-Za-z0-9_.-]+', '_', nice_name)[:180]
    path = out_dir / (safe + ".pdf")
    try:
        with urllib.request.urlopen(url) as resp, open(path, "wb") as f:
            f.write(resp.read())
        return str(path)
    except Exception:
        return None


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group()
    g.add_argument("--hours", type=int, default=None, help="Lookback window (hours).")
    g.add_argument("--since", type=str, default=None, help="Since date YYYY-MM-DD (local date).")
    p.add_argument("--out", type=str, default=str(Path.home() / "Papers" / "arxiv_hits"))
    p.add_argument("--max", type=int, default=150, help="Max results per page from API (100–200 ok).")
    p.add_argument("--notify", action="store_true", help="Show a macOS notification for each hit.")
    p.add_argument("--csv", type=str, default=str(Path.home() / "Papers" / "arxiv_hits" / "hits_log.csv"))
    p.add_argument("--dry", action="store_true", help="Do not download PDFs.")
        # --- plist builder/installer flags ---
    p.add_argument("--build-plist", action="store_true",
                   help="Build a LaunchAgent plist next to the current working dir.")
    p.add_argument("--install-plist", action="store_true",
                   help="Install the built plist into ~/Library/LaunchAgents and load it.")
    p.add_argument("--schedule", type=str, default="09:30",
                   help="Daily time HH:MM (24h) for the LaunchAgent. Default: 09:30.")
    p.add_argument("--label", type=str, default="com.arxiv.watcher",
                   help="LaunchAgent label (used for plist filename).")
    p.add_argument("--hours-lookback", type=int, default=24,
                   help="Lookback window in hours for the LaunchAgent. Default: 24.")
    p.add_argument("--backoff-interval", type=int, default=3600,
                   help="Extra periodic run in seconds via StartInterval (default: 3600). "
                    "Use 0 to disable. Example: 1800 for every 30 minutes.")
    p.add_argument("--logs-dir", type=str, default=str(Path.home() / "Library" / "Logs"),
                   help="Directory for stdout/stderr logs in the LaunchAgent.")
    p.add_argument("--no-notify", action="store_true", help="Disable notifications in LaunchAgent plist.")
    p.add_argument("--print", dest="print_n", type=int, default=50,
               help="Number of hits to print (use -1 for all).")
    p.add_argument("--min-score", type=int, default=1,
               help="Only keep hits with total score >= this value.")
    p.add_argument("--print-authors", type=int, default=6,
               help="Max authors to show in console (full list still saved to CSV). Default: 6.")
    p.add_argument("--no-authors", action="store_true",
                   help="Do not print authors line in console.")
    p.add_argument("--print-width", type=int, default=0,
                   help="Wrap console lines to this width (0 = auto-detect terminal).")
    p.add_argument("--max-title", type=int, default=140,
                   help="Truncate very long titles in console to this many chars. 0 = no limit. Default: 140.")
    p.add_argument("--report-md", type=str, default="",
               help="Optional path to write a pretty Markdown report of the run.")
    args = p.parse_args()
        # If user is building/ installing plist, do that first and exit.
    if args.build_plist or args.install_plist:
        plist_path = build_plist(
            schedule_hhmm=args.schedule,
            label=args.label,
            hours_lookback=args.hours_lookback,
            out_dir=args.out,
            notify=(not args.no_notify),
            python_path=sys.executable,
            script_path=str(Path(__file__).resolve()),
            log_dir=args.logs_dir,
            backoff_interval=args.backoff_interval,
        )
        print(f"Built plist: {plist_path}")
        if args.install_plist:
            dest = install_plist(plist_path)
            print(f"Installed & loaded: {dest}")
            print("Tip: run `launchctl kickstart -k gui/$(id -u)/{}` to trigger a run now.".format(args.label))
        return
    state = _load_state()

    dynamic_hours = None
    if args.hours is None and not args.since:
        # compute hours since last success (clamped to [23, 25])
        last = _parse_iso(state.get("last_success_iso"))
        if last is None:
            dynamic_hours = 24
        else:
            delta_h = (_now_utc() - last).total_seconds() / 3600.0
            # round to nearest hour and clamp
            dynamic_hours = max(23, min(25, int(round(delta_h))))
        # behave as if user supplied --hours
        args.hours = dynamic_hours

    since_iso = None
    if args.since:
        # Interpret as 00:00 at the given date; stored as UTC-style ISO string.
        since_iso = f"{args.since}T00:00:00+00:00"
    seen_ids_run = set()
    hits = []
    try:
        entries_iter = fetch_entries_paged(
            DEFAULT_QUERY,
            since_iso=since_iso if args.since else None,
            max_per_page=args.max,
            max_pages=500 if args.since else 3
        )
        seen_ids_state = set(state.get("seen_ids", []))
        for e in entries_iter:
            if args.hours is not None:
                if not within_hours(e.get("updated", ""), args.hours):
                    continue
            # derive arXiv ID and skip duplicates
            arxiv_id = (e.get("link", "").rstrip("/").split("/")[-1]) or None
            if not arxiv_id:
                continue
            if arxiv_id in seen_ids_state or arxiv_id in seen_ids_run:
                continue

            text = (e.get("title", "") + "\n" + e.get("summary", ""))
            kscore = keyword_score(text)
            ascore = author_score(e.get("authors", []))
            score = kscore + ascore
            if score >= 1:
                hits.append((score, e, kscore, ascore, arxiv_id))
                seen_ids_run.add(arxiv_id)
    except RuntimeError as ex:
        if str(ex).startswith("network-error:"):
            print(f"⚠️ Network error while fetching arXiv: {ex}", file=sys.stderr)
            network_failed = True
        else:
            raise
    else:
        network_failed = False

    # Sort primarily by total score (desc). The API feed is already newest-first.
    hits.sort(key=lambda x: (-x[0],))

    # --- Full log (kept as-is) ---
    csv_path_full = Path(args.csv).expanduser().resolve()
    csv_path_full.parent.mkdir(parents=True, exist_ok=True)
    new_file_full = not csv_path_full.exists()
    
    with open(csv_path_full, "a", newline="") as f:
        w = csv.writer(f)
        if new_file_full:
            w.writerow([
                "timestamp", "score_total", "score_keywords", "score_authors",
                "title", "link", "pdf_saved_or_url", "updated", "categories", "authors"
            ])
        for score, e, kscore, ascore, arxiv_id in hits:
            saved_pdf = None
            if not args.dry:
                base_name = f'{arxiv_id}_{e.get("title", "")[:80]}'
                saved_pdf = download_pdf(e.get("pdf"), args.out, base_name)
            # shorten author list here
            authors_short = format_authors(e.get("authors", []), max_authors=3)
            w.writerow([
                dt.datetime.now().isoformat(), score, kscore, ascore,
                e.get("title", ""), e.get("link", ""), saved_pdf or e.get("pdf", ""),
                e.get("updated", ""), ";".join(e.get("categories", [])), authors_short
            ])
            if args.notify:
                subtitle = f"score {score} (kw{kscore} + au{ascore})"
                message = f"[{arxiv_id}] {e.get('title', '')}"
                notify_macos("arXiv hit", subtitle, message)

    # Print concise report
    # --- Pretty console report (replace your old print block with this) ---

    scope_str = (
        f" since {args.since}" if args.since
        else f" in the last {args.hours}h" if args.hours is not None
        else ""
    )
    print(f"Found {len(hits)} matching entries{scope_str}.\n")
    
    # choose wrapping width (0 => auto)
    width = args.print_width if args.print_width and args.print_width > 0 else term_width()
    
    # collect lines for optional Markdown report
    lines_for_md = []
    
    # cap console list for sanity; change 50 if you like
    to_show = hits if args.print_n == -1 else hits[:args.print_n]
    for score, e, kscore, ascore, arxiv_id in to_show:
        title = e['title']

        # optionally truncate very long titles for console
        if args.max_title and args.max_title > 0 and len(title) > args.max_title:
            title = title[:args.max_title - 1] + "…"
    
        header = f"[{score} = kw{kscore}+au{ascore}] {title}"
        link   = e['link']
        pdf    = e.get('pdf') or ""
        authors_full  = e.get('authors', [])
        authors_short = format_authors(authors_full, args.print_authors)

        # Console print, wrapped to width
        print(wrap_line(header, width))
        print("     " + link)
        if pdf:
            print("     PDF: " + pdf)
        if not args.no_authors and authors_short:
            print("     Authors: " + wrap_line(authors_short, width))
        print()

        # Also prepare a Markdown bullet for optional report
        md = [
            f"- **{e['title']}**",
            f"  Score: `{score} = kw{kscore}+au{ascore}`",
            f"  Link: {link}",
        ]
        if pdf: md.append(f"  PDF: {pdf}")
        if authors_short and not args.no_authors:
            md.append(f"  Authors: {authors_short}")
        lines_for_md.append("  \n".join(md))

    # Optional Markdown report
    if args.report_md:
        md_path = Path(args.report_md).expanduser().resolve()
        md_path.parent.mkdir(parents=True, exist_ok=True)
        header_md = (
            f"# arXiv Kaon Watch — {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"Found **{len(hits)}** matching entries{scope_str}.\n\n"
        )
        md_path.write_text(header_md + "\n".join(lines_for_md) + "\n", encoding="utf-8")
        print(f"Wrote Markdown report to: {md_path}")

    # Persist dedupe IDs always; only advance last_success on full success
    merged = list(dict.fromkeys(state.get("seen_ids", []) + list(seen_ids_run)))
    if len(merged) > 5000:
        merged = merged[-5000:]
    state["seen_ids"] = merged
    
    if not network_failed:
        state["last_success_iso"] = _now_utc().isoformat()
    else:
        print("⚠️ Network error: kept seen_ids so we don't re-notify; last_success unchanged.", file=sys.stderr)

    _save_state(state)


if __name__ == "__main__":
    main()
