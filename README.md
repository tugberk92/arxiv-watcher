# arxiv-watcher

*A daily arXiv butler for kaon physics (and friends).*

This script checks **arXiv** for new papers and flags those relevant to **kaon physics, CKM, NA62, KOTO, KLEVER, HIKE, NA48, fixed-target & precision-frontier experiments**, plus the **statistics and analysis** methods you actually use, and **specific authors** you follow.

It combines **keyword matches** (organised into editable topic groups) and **known author names** to catch interesting preprints, downloads PDFs, logs results, and notifies you via macOS Notification Center. Instead of arXiv's daily firehose of *every* abstract in a category, you get a short, scored, de-duplicated list.

On macOS you can schedule it to run automatically using a LaunchAgent plist. The script builds and installs that plist for you.

---

## Features

- Monitors `hep-ex`, `hep-ph`, `hep-lat` with a deliberately **focused** server-side query (kept low-volume on purpose).
- Matches by external pattern files — edit them freely, no need to touch the code:
  - `patterns/keywords.txt` → regex patterns grouped into **topic groups** via `## group` headers (`kaon`, `ckm`, `fixed-target`, `stats`, `analysis`). Notifications/reports show *which* group(s) matched.
  - `patterns/authors.txt` → known author names (one per line; matches weighted ×2).
  - `patterns/extra_query.txt` → *optional, empty by default.* OR-ed clauses to widen what gets fetched (e.g. `cat:physics.ins-det`). Add only if you want more volume.
- **Catch-up over any date range** with `--since` / `--until`.
- **Network-resilient & rate-limit friendly:** descriptive User-Agent, polite delay between pages, retry-with-backoff on HTTP 429/503, and a `--every-hours` guard so scheduled wake-ups don't re-poll (or hammer) arXiv.
- Saves PDFs into a folder (default: `~/Papers/arxiv_hits`) and appends metadata to a CSV log (`hits_log.csv`, now with a `groups` column).
- macOS notifications for new matches (safe against titles containing quotes).
- Built-in **LaunchAgent builder**: generates and installs a `.plist`.

---

## Quick start (one command)

```bash
git clone https://github.com/yourname/arxiv-watcher.git
cd arxiv-watcher
./setup.sh          # or ./setup.sh 08:00 to pick the daily time
```

`setup.sh` does everything: installs `terminal-notifier` (so clicking a
notification opens the arXiv page, not Script Editor), installs and loads the
daily LaunchAgent, creates double-clickable digest launchers in `launchers/`,
and runs once so you see it working. Then just edit the files in `patterns/` to
tune what you track.

---

## Manual installation

1. Clone the repo:
   ```bash
   git clone https://github.com/yourname/arxiv-watcher.git
   cd arxiv-watcher
   chmod +x arxiv_watcher.py
   ```

2. (Optional, for clickable notifications) install terminal-notifier:
   ```bash
   brew install terminal-notifier
   ```

3. Edit the pattern files in `patterns/` to suit your interests (see
   *Customising what you track* below).

---

## Usage

- Make sure python is installed:  
  ```bash
  python3 --version
  ```

- Manual run (look back 24h):  
  ```bash
  python3 arxiv_watcher.py --hours 24 --out ~/Papers/arxiv_hits --notify
  ```

- Run now even though the scheduler ran recently:  
  ```bash
  python3 arxiv_watcher.py --force --dry
  ```

### Get a list of papers on demand

Use `--open` to write a clickable HTML digest and open it in your browser. Add
`--no-dedupe` so you see *every* match in the window (not just unseen ones) and
the daily watch state is left untouched:

```bash
# Last 30 days
python3 arxiv_watcher.py --days 30 --no-dedupe --dry --open

# A whole year
python3 arxiv_watcher.py --year 2026 --no-dedupe --dry --open

# Any interval
python3 arxiv_watcher.py --since 2026-01-01 --until 2026-03-31 --no-dedupe --dry --open
```

Or just **double-click** a launcher in `launchers/` (created by `setup.sh`).

### Options
```
--hours N            Look back N hours
--days N             Look back N days (= --hours N*24)
--since YYYY-MM-DD   Start of a date range
--until YYYY-MM-DD   End of a date range (use with --since to catch up)
--year YYYY          A whole calendar year (Jan 1 → Dec 31)
--no-dedupe          Show every match in the window; don't touch the watch state
--every-hours N      Auto/scheduled mode: skip the API call if a successful run
                     happened within N hours (default 20). Prevents rate-limiting.
--force              Run the query even if a successful run happened recently.
--min-score N        Only keep hits scoring >= N (default 1).
--out PATH           Output folder for PDFs (default: ~/Papers/arxiv_hits)
--csv PATH           Log file (CSV, default: hits_log.csv)
--report-md PATH     Also write a Markdown report of the run
--html PATH          Write a clickable HTML digest to PATH
--open               Open an HTML digest in your browser when done
--notify             Send a macOS notification on hits (click → opens arXiv)
--dry                Don’t download PDFs, just list them
--build-plist        Generate a LaunchAgent plist for automatic runs
--install-plist      Install the plist into ~/Library/LaunchAgents
--schedule HH:MM     Time of day for the scheduled run
--plist-every-hours  Value passed to --every-hours in the installed plist (default 20)
```

**With no `--hours`/`--since`, the watcher runs in *auto mode*:** it looks back to
its last successful run (so it catches up after the laptop was closed), but skips
entirely if it already succeeded within `--every-hours`. That's what makes a
frequent launchd schedule safe.

---

## Automatic daily run for macOS

- Build a plist so that you can get messages in the notification center (default: run at 09:30 am daily for the last 24h, notify on hits):  
  ```bash
  python3 arxiv_watcher.py --build-plist
  ```

- Build and install it (runs daily at 09:30, plus hourly wake-ups that no-op
  unless ≥20h since the last success):  
  ```bash
  python3 arxiv_watcher.py \
    --build-plist \
    --install-plist \
    --schedule 09:30 \
    --plist-every-hours 20 \
    --backoff-interval 3600 \
    --out ~/Papers/arxiv_hits
  ```

- Trigger it immediately:  
  ```bash
  launchctl kickstart -k gui/$(id -u)/com.arxiv.watcher
  ```

- Confirm it's loaded (you should see `com.arxiv.watcher` listed):
  ```bash
  launchctl list | grep com.arxiv.watcher
  ```

- Check the logs:
  ```bash
  tail -n 50 ~/Library/Logs/arxiv_watcher.out
  tail -n 50 ~/Library/Logs/arxiv_watcher.err
  ```
- Successful runs show lines like:
  ```bash
  Found 2 matching entries in the last 24h.
  [2 = kw2+au0] ...
  ```

- Check your schedule (you will see a block starting with `StartCalendarInterval` then your `Hour/Minute`):
  ```bash
  cat ~/Library/LaunchAgents/com.arxiv.watcher.plist
  ```

- If you enabled `--notify`, macOS will show alerts like:
  ```bash
  arXiv hit — score 3 (kw 2 + au 1) — [arXiv:2507.13445] Paper title
  ```

- Sanity check:
  ```bash
  plutil -lint ~/Library/LaunchAgents/com.arxiv.watcher.plist
  ```

- Uninstall (remove the old job completely):
  ```bash
  # 1) Stop & unload (ignore errors if not loaded)
  launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.arxiv.watcher.plist 2>/dev/null || true
  
  # 2) Delete the LaunchAgent plist
  rm -f ~/Library/LaunchAgents/com.arxiv.watcher.plist
  
  # 3) Remove old logs
  rm -f ~/Library/Logs/arxiv_watcher.out ~/Library/Logs/arxiv_watcher.err
  
  # 4) (optional) reset state so dedupe/timestamp starts fresh
  rm -f ~/.local/share/arxiv_watcher/state.json
  
  # 5) Confirm it’s truly gone (should show nothing)
  launchctl print gui/$(id -u)/com.arxiv.watcher 2>/dev/null || echo "No such service (good)."
  ```

- Fresh re-installation after uninstallation:
  ```bash
  python3 arxiv_watcher.py \
    --build-plist \
    --install-plist \
    --schedule 09:30 \
    --plist-every-hours 20 \
    --backoff-interval 3600 \
    --out ~/Papers/arxiv_hits
  
  launchctl kickstart -k gui/$(id -u)/com.arxiv.watcher
  ```
---

## Customising what you track

Everything lives in `patterns/` — edit the text files, no code changes needed:

- **Add/remove keywords:** edit `patterns/keywords.txt`. Put each regex under a
  `## group` header so matches are labelled. Example:
  ```
  ## stats
  \bprofile\s+likelihood\b
  \bunfolding\b
  ```
- **Follow more people:** add names to `patterns/authors.txt` (one per line;
  these count double).
- **Cast a wider net:** add OR-clauses to `patterns/extra_query.txt`, e.g.
  `cat:physics.ins-det` for detector papers. Empty by default to keep volume low.
- **Tune the noise:** raise `--min-score` to keep only stronger matches.

---

## Example output

```
Found 5 matching entries in the last 24h.

[4 = kw2+au2] {kaon, ckm} CP violation in K→μ+μ− with and without time dependence
     http://arxiv.org/abs/2507.13445v1
     PDF: http://arxiv.org/pdf/2507.13445v1
     Authors: G. D’Ambrosio, Y. Grossman, T. Kitahara, D. Martínez Santos
```

The `{kaon, ckm}` tags show which topic groups matched; author hits appear as `{@Grossman}`.

---

## License

MIT License – see [LICENSE](LICENSE) for details.
