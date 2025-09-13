# arxiv-watcher

*A daily arXiv butler for kaon physics (and friends).*

This script checks **arXiv** for new papers every day and flags those that are relevant to **kaon physics, CKM, NA62, KOTO, KLEVER, HIKE, KLOE, KTeV, NA48, BESIII**, and related experiments.	
It combines **keyword matches** and **known author names** to catch interesting preprints, downloads PDFs, logs results, and can even notify you via macOS Notification Center.

On macOS you can schedule it automatically at a fixed time (e.g. 09:30 every morning) using a LaunchAgent plist. The script can even build and install that plist for you.

---

## Features

- Monitors `hep-ex`, `hep-ph`, `hep-lat`.
- Matches by external pattern files:
  - `patterns/keywords.txt` → list of keywords/regex (e.g. kaon, CKM, NA62, KOTO-II, …)
  - `patterns/authors.txt` → list of known author names (one per line)
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
   chmod +x arxiv_watcher.py
   ```

2. (Optional) Prepare your pattern files:
   ```bash
   mkdir -p patterns
   echo "kaon" >> patterns/keywords.txt
   echo "Andrzej Buras" >> patterns/authors.txt
   ```
   Edit them to suit your own interests.

---

## Usage

- Make sure python is installed:  
  ```bash
  python3 --version
  ```

- Manual run:  
  ```bash
  python3 arxiv_watcher.py --hours 24 --out ~/Papers/arxiv_hits --notify
  ```

- Check since a given date:  
  ```bash
  python3 arxiv_watcher.py --since 2025-01-01 --dry
  ```

### Options
```
--hours N			 Look back N hours (default: 24)
--since YYYY-MM-DD	 Look back to a given date
--out PATH			 Output folder for PDFs (default: ~/Papers/arxiv_hits)
--csv PATH			 Log file (CSV, default: hits_log.csv)
--notify			 Send macOS notification on hits
--dry				 Don’t download PDFs, just list them
--build-plist		 Generate a LaunchAgent plist for automatic runs
--install-plist		 Install the plist into ~/Library/LaunchAgents
--schedule HH:MM	 Time of day for automatic run (with --install-plist)
```

---

## Automatic daily run for macOS

- Build a plist so that you can get messages in the notification center (default: run at 09:30 am daily for the last 24h, notify on hits):	
  ```bash
  python3 arxiv_watcher.py --build-plist
  ```

- Build and install it:  
  ```bash
  python3 arxiv_watcher.py --build-plist --install-plist --schedule 09:30 --out ~/Papers/arxiv_hits
  ```

- Trigger it immediately:  
  ```bash
  launchctl start com.arxiv.watcher
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

MIT License – see [LICENSE](LICENSE) for details.
