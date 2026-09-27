# steamaccgen
Automated Steam account registration with IMAP email verification, optional Steam Guard disabling, and profile randomization. Python + Selenium.

# Steam Account Creator

A Python automation script that registers new Steam accounts, verifies the email via IMAP, optionally disables Steam Guard, and optionally randomizes the profile name.

> ⚠️ **Disclaimer**  
> This project is for educational purposes only. Automating Steam account creation violates the [Steam Subscriber Agreement](https://store.steampowered.com/subscriber_agreement/) and may result in account or IP bans. Use at your own risk. The author is not responsible for any misuse or consequences.

---

## Features

- Automated Steam registration form filling
- Human-like typing delays
- Manual CAPTCHA solving (you solve it in the browser; the script waits)
- Email verification via IMAP (Gmail, Outlook, etc.)
- Optional: disable Steam Guard via email confirmation link or code
- Optional: randomize profile name after account creation
- Saves generated credentials to `accounts.txt`

---

## Requirements

- **Python 3.10 or newer** (uses `str | None` and `list[str]` type hints)
- **Google Chrome** installed
- An email account with **IMAP access** (Gmail recommended)
- **pip packages:** `faker`, `selenium`

---

## Installation

1. **Clone the repository** or download the script.
2. **Install dependencies:**
   ```bash
   pip install faker selenium
