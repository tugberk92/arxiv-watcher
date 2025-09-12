# arxiv-watcher

*A daily arXiv butler for kaon physics (and friends).*

This script checks **arXiv** for new papers every day and flags those that are relevant to **kaon physics, CKM, NA62, KOTO, KLEVER, HIKE, KLOE, KTeV, NA48, BESIII**, and related experiments.  
It combines **keyword matches** and **known author names** to catch interesting preprints, downloads PDFs, logs results, and can even notify you via macOS Notification Center.

On macOS you can schedule it automatically at a fixed time (e.g. 09:30 every morning) using a LaunchAgent plist. The script can even build and install that plist for you.

---

## Features

- Monitors `hep-ex`, `hep-ph`, `hep-lat`.
- Matches by:
  - Keywords: *kaon, CKM, Vus, NA62, KOTO-II, KLOE, KTeV, NA48/2, BESIII*, etc.
  - Authors: *Buras, Ceccucci, Isidori, Grossman, Jüttner, Knecht, Bordone, Gorbahn, Stamou,* and more.
- Saves PDFs into a folder (default: `~/Papers/arxiv_hits`).
- Appends metadata to a CSV log (`hits_log.csv`).
- macOS notifications for new matches.
- Built-in **LaunchAgent builder**: generates and installs a `.plist` that runs daily at your chosen time.

---

## Installation

1. Clone the repo:
   ```bash
   git clone https://github.com/yourname/arxiv-watcher.git
   cd arxiv-watcher
   chmod +x arxiv_watcher.py```

2. Usage

- Make sure python is installed: ```python3 --version```
- Manual run: ```python3 arxiv_watcher.py --hours 24 --out ~/Papers/arxiv_hits --notify```
- Check since a given date: ```python3 arxiv_watcher.py --since 2025-01-01 --dry```
- Options:
    ```--hours N → look back N hours
    --since YYYY-MM-DD → look back to a given date
    --out PATH → output folder for PDFs
    --csv PATH → log file (CSV)
    --notify → macOS notification
    --dry → don’t download PDFs, just list them```

3. Automatic daily run for macOS
- Build a plist (default: run at 09:30 am daily for the last 24h, notify on hits): ```python3 arxiv_watcher.py --build-plist```
- Build and install it: ```python3 arxiv_watcher.py --build-plist --install-plist --schedule 09:30 --out ~/Papers/arxiv_hits```
- Trigger it immediately: ```launchctl start com.arxiv.watcher```
- Check the logs:
    ```tail -n 50 ~/Library/Logs/arxiv_watcher.out
    tail -n 50 ~/Library/Logs/arxiv_watcher.err```


4. Example output
```Found 5 matching entries in the last 24h.

[4 = kw2+au2] CP violation in K→μ+μ− with and without time dependence
     http://arxiv.org/abs/2507.13445v1
     PDF: http://arxiv.org/pdf/2507.13445v1
     Authors: G. D’Ambrosio, Y. Grossman, T. Kitahara, D. Martínez Santos```
