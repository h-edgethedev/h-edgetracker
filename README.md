# H~EDGE Tracker

> Automatically track how you spend your time on your laptop — coding, watching videos, browsing, reading, and more. Get AI-powered daily summaries and productivity insights.

Built by [H~EDGE Studios](https://github.com/h-edgethedev)

---

## Features

- **Auto-tracking** — detects your active window every 5 seconds, no manual input needed
- **Smart categorization** — automatically classifies activity as coding, video, browsing, reading, social, gaming, or other
- **Dark GUI dashboard** — live activity log, breakdown bars, and session stats
- **CLI interface** — check stats, history, and AI insights straight from the terminal
- **AI insights** — daily summaries, productivity tips, and time balance analysis powered by Claude
- **Local storage** — all data saved to your machine, nothing sent to any server except when you request AI insights
- **100% offline** for tracking and stats — internet only needed for AI features

---

## Requirements

- Windows 10 or 11
- Python 3.10 or higher — download from [python.org](https://python.org)
- An Anthropic API key (optional — only needed for AI features)

---

## Installation

**Step 1** — Download or clone this repo:

```bash
git clone https://github.com/h-edgethedev/hedge-tracker.git
cd hedge-tracker
```

**Step 2** — Run the installer (double-click or run in terminal):

```bash
install.bat
```

This installs all Python dependencies automatically.

**Step 3 (optional)** — Set your Anthropic API key for AI features:

```bash
python cli.py set-key sk-ant-YOUR_KEY_HERE
```

Get a key at [console.anthropic.com](https://console.anthropic.com)

---

## Usage

### GUI (recommended)

Double-click `run.bat` or run:

```bash
python gui.py
```

### CLI

```bash
python cli.py start       # Start tracking in terminal (Ctrl+C to stop)
python cli.py status      # Show today's stats
python cli.py summary     # AI daily summary
python cli.py tips        # AI productivity tips
python cli.py balance     # AI time balance analysis
python cli.py history     # Show past 7 days
python cli.py set-key KEY # Save Anthropic API key
```

---

## How it works

The tracker polls your active window title and process name every **5 seconds** using the Windows API. It classifies each window based on keywords and saves completed sessions to a local JSON file at:

```
C:\Users\YOU\.hedgetracker\activities.json
```

Sessions shorter than ~18 seconds are ignored to filter out alt-tab noise.

---

## Customizing categories

Open `tracker.py` and edit `CATEGORY_RULES` to add your own apps or websites to any category:

```python
CATEGORY_RULES = {
    "code": [
        "visual studio code", "pycharm", ...  # add your apps here
    ],
    ...
}
```

---

## Privacy

- All activity data is stored **locally** on your machine
- No data is ever sent anywhere except to the Anthropic API when you explicitly click an AI insight button
- You can find and delete your data at `C:\Users\YOU\.hedgetracker\`

---

## Contributing

Pull requests are welcome! If you want to add a feature, fix a bug, or improve the categorization rules, feel free to open an issue or submit a PR.

1. Fork the repo
2. Create a branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push and open a Pull Request

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

<p align="center">Made with love by <a href="https://github.com/h-edgethedev">H~EDGE Studios</a></p>
