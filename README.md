# arxiv-watcher

*A daily arXiv butler for kaon physics (and friends).*

This script checks **arXiv** for new papers every day and flags those that are relevant to  
**kaon physics, CKM, NA62, KOTO, KLEVER, HIKE, KLOE, KTeV, NA48, BESIII**, and related experiments.  
It combines **keyword matches** and **known author names** to catch interesting preprints, downloads PDFs, logs results, and (on macOS) can send notifications.

On macOS you can also schedule it to run automatically at a fixed time (e.g. 09:30 every morning) using a LaunchAgent `.plist`. The script can even build and install that plist for you.

---

## Features

- Monitors categories: `hep-ex`, `hep-ph`, `hep-lat`
- Matches by:
  - **Keywords:** *kaon, CKM, Vus, NA62, KOTO-II, KLOE, KTeV, NA48/2, BESIII*, etc.
  - **Authors:** *Buras, Ceccucci, Isidori, Grossman, Jüttner, Knecht, Bordone, Gorbahn, Stamou*, and more
- Saves PDFs into a folder (default: `~/Papers/arxiv_hits`)
- Appends metadata to a CSV log (`hits_log.csv`)
- Optional macOS notifications for new matches
- Built-in **LaunchAgent builder** to auto-run daily at your chosen time

---

## Installation

```bash
git clone https://github.com/yourname/arxiv-watcher.git
cd arxiv-watcher
chmod +x arxiv_watcher.py
```

> Replace `yourname` with your GitHub username.  
> Python 3 only, standard library only (no extra packages).

---

## Usage

### Manual runs

Check Python:
```bash
python3 --version
```

Look back **24 hours**:
```bash
python3 arxiv_watcher.py --hours 24 --out ~/Papers/arxiv_hits --notify
```

Fetch **since a date** (no downloads, just list):
```bash
python3 arxiv_watcher.py --since 2025-01-01 --dry
```

**Common options**
```
--hours N             Look back N hours
--since YYYY-MM-DD    Look back to a given date
--out PATH            Output folder for PDFs
--csv PATH            Log file (CSV)
--notify              macOS notification
--dry                 Don’t download PDFs, just list them
```

---

## Automatic daily run (macOS)

Build a LaunchAgent plist (defaults: 09:30 every day, last 24h, notifications on):
```bash
python3 arxiv_watcher.py --build-plist
```

Build **and install** it:
```bash
python3 arxiv_watcher.py --build-plist --install-plist --schedule 09:30 --out ~/Papers/arxiv_hits
```

Trigger a run immediately:
```bash
launchctl start com.arxiv.watcher
```

Check logs:
```bash
tail -n 50 ~/Library/Logs/arxiv_watcher.out
tail -n 50 ~/Library/Logs/arxiv_watcher.err
```

> To uninstall later:  
> `launchctl unload ~/Library/LaunchAgents/com.arxiv.watcher.plist && rm ~/Library/LaunchAgents/com.arxiv.watcher.plist`

---

## Example output

```
Found 5 matching entries in the last 24h.

[4 = kw2+au2] CP violation in K→μ+μ− with and without time dependence
     http://arxiv.org/abs/2507.13445v1
     PDF: http://arxiv.org/pdf/2507.13445v1
     Authors: G. D’Ambrosio, Y. Grossman, T. Kitahara, D. Martínez Santos
```

---

## License

MIT — see [LICENSE](./LICENSE).
