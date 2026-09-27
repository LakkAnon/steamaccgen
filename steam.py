import os
import sys
import time
import random
import string
import logging
import email as email_lib
import email.message
from email.header import decode_header
from datetime import datetime, timedelta
import imaplib
import re
import threading
import configparser
from pathlib import Path
from faker import Faker
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

if os.name == "nt":
    os.system("")

fake = Faker()

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    GRAY    = "\033[90m"

_PRINT_LOCK = threading.Lock()

def _p(line: str = "") -> None:
    with _PRINT_LOCK:
        print(line, flush=True)

def banner() -> None:
    _p(f"""
{C.CYAN}{C.BOLD}  ╔══════════════════════════════════════════════════════════╗
  ║                                                          ║
  ║   {C.WHITE}STEAM{C.CYAN}  ·  {C.WHITE}ACCOUNT CREATOR{C.CYAN}                              ║
  ║   {C.GRAY}auto registration  ·  steam guard disable{C.CYAN}             ║
  ║                                                          ║
  ╚══════════════════════════════════════════════════════════╝{C.RESET}
""")

def step(num: int, total: int, title: str) -> None:
    _p(f"\n{C.BOLD}{C.CYAN}  [{num}/{total}]{C.RESET}  {C.BOLD}{C.WHITE}{title}{C.RESET}")

def ok(msg: str) -> None:
    _p(f"     {C.GREEN}✓{C.RESET}  {msg}")

def fail(msg: str) -> None:
    _p(f"     {C.RED}✗{C.RESET}  {msg}")

def warn(msg: str) -> None:
    _p(f"     {C.YELLOW}!{C.RESET}  {C.YELLOW}{msg}{C.RESET}")

def note(msg: str) -> None:
    _p(f"     {C.GRAY}·  {msg}{C.RESET}")

def kv(label: str, value: str, color: str = C.WHITE) -> None:
    _p(f"     {C.GRAY}{label:<10}{C.RESET}{color}{value}{C.RESET}")

def action_box(title: str, subtitle: str = "") -> None:
    width = 56
    inner = width - 4
    top    = "┌" + "─" * width + "┐"
    bottom = "└" + "─" * width + "┘"
    t_line = ("⚠  " + title).ljust(inner)
    _p(f"\n{C.YELLOW}{top}")
    _p(f"{C.YELLOW}│ {C.BOLD}{C.YELLOW}{t_line}{C.RESET}{C.YELLOW} │")
    if subtitle:
        s_line = subtitle.ljust(inner)
        _p(f"{C.YELLOW}│ {C.WHITE}{s_line}{C.RESET}{C.YELLOW} │")
    _p(f"{C.YELLOW}{bottom}{C.RESET}")

def done_banner(creds: dict) -> None:
    _p(f"""
{C.GREEN}{C.BOLD}  ╔══════════════════════════════════════════════════════════╗
  ║                     ACCOUNT READY                        ║
  ╚══════════════════════════════════════════════════════════╝{C.RESET}
""")
    kv("Username", creds["username"], C.CYAN)
    kv("Password", creds["password"], C.CYAN)
    kv("Email",    creds["email"],    C.WHITE)
    if creds.get("profile_name"):
        kv("Name",   creds["profile_name"], C.MAGENTA)
    kv("Saved to", OUTPUT_FILE,       C.GRAY)
    _p("")

class _UILog:
    def info(self, msg):    note(msg)
    def debug(self, msg):   pass
    def warning(self, msg): warn(msg)
    def error(self, msg):   fail(msg)

log = _UILog()

CONFIG_PATH = Path("config.ini")

DEFAULT_CONFIG = {
    "email":             "",
    "app_password":      "",
    "imap_host":         "imap.gmail.com",
    "imap_port":         "993",
    "captcha_timeout":   "300",
    "check_interval":    "5",
    "lookback_hours":    "1",
    "typing_speed_min":  "0.008",
    "typing_speed_max":  "0.025",
    "disable_steam_guard": "true",
    "randomize_profile":   "false",
    "headless":          "false",
    "output_file":       "accounts.txt",
}

def _write_default_config() -> None:
    cfg = configparser.ConfigParser()
    cfg["steam"] = DEFAULT_CONFIG
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(
            "# Steam Account Creator — config file\n"
            "# Edit the values below, then re-run the script.\n\n"
        )
        cfg.write(f)

def _cfg_str(cfg, key: str, default: str = "") -> str:
    try:
        return cfg.get("steam", key).strip()
    except Exception:
        return default

def _cfg_int(cfg, key: str, default: int) -> int:
    try:
        return int(cfg.get("steam", key).strip())
    except Exception:
        return default

def _cfg_float(cfg, key: str, default: float) -> float:
    try:
        return float(cfg.get("steam", key).strip())
    except Exception:
        return default

def _cfg_bool(cfg, key: str, default: bool) -> bool:
    try:
        v = cfg.get("steam", key).strip().lower()
        return v in ("1", "true", "yes", "on")
    except Exception:
        return default

def load_config() -> None:
    if not CONFIG_PATH.exists():
        _write_default_config()
        _p(f"\n{C.YELLOW}  !  No config.ini found — created one at {CONFIG_PATH}")
        _p(f"{C.YELLOW}     Fill in 'email' and 'app_password', then re-run.{C.RESET}\n")
        sys.exit(0)

    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH, encoding="utf-8")

    global EMAIL_ADDRESS, APP_PASSWORD
    global IMAP_HOST, IMAP_PORT
    global CAPTCHA_WAIT_TIMEOUT, CHECK_INTERVAL, LOOKBACK_HOURS
    global TYPING_MIN, TYPING_MAX
    global DISABLE_STEAM_GUARD, RANDOMIZE_PROFILE, HEADLESS
    global OUTPUT_FILE

    EMAIL_ADDRESS        = _cfg_str(cfg, "email")
    APP_PASSWORD         = _cfg_str(cfg, "app_password")
    IMAP_HOST            = _cfg_str(cfg, "imap_host", "imap.gmail.com")
    IMAP_PORT            = _cfg_int(cfg, "imap_port", 993)
    CAPTCHA_WAIT_TIMEOUT = _cfg_int(cfg, "captcha_timeout", 300)
    CHECK_INTERVAL       = _cfg_int(cfg, "check_interval", 5)
    LOOKBACK_HOURS       = _cfg_int(cfg, "lookback_hours", 1)
    TYPING_MIN           = _cfg_float(cfg, "typing_speed_min", 0.008)
    TYPING_MAX           = _cfg_float(cfg, "typing_speed_max", 0.025)
    DISABLE_STEAM_GUARD  = _cfg_bool(cfg, "disable_steam_guard", True)
    RANDOMIZE_PROFILE    = _cfg_bool(cfg, "randomize_profile", False)
    HEADLESS             = _cfg_bool(cfg, "headless", False)
    OUTPUT_FILE          = _cfg_str(cfg, "output_file", "accounts.txt")

    if not EMAIL_ADDRESS or not APP_PASSWORD:
        _p(f"\n{C.RED}  ✗  config.ini is missing 'email' or 'app_password'.{C.RESET}\n")
        sys.exit(1)

    if TYPING_MIN > TYPING_MAX:
        TYPING_MIN, TYPING_MAX = TYPING_MAX, TYPING_MIN

EMAIL_ADDRESS        = ""
APP_PASSWORD         = ""
IMAP_HOST            = "imap.gmail.com"
IMAP_PORT            = 993
CAPTCHA_WAIT_TIMEOUT = 300
CHECK_INTERVAL       = 5
LOOKBACK_HOURS       = 1
TYPING_MIN           = 0.008
TYPING_MAX           = 0.025
DISABLE_STEAM_GUARD  = True
RANDOMIZE_PROFILE    = False
HEADLESS             = False
OUTPUT_FILE          = "accounts.txt"

STEAM_CREATE_URL = "https://store.steampowered.com/join/"
STEAM_GUARD_URL  = "https://store.steampowered.com/twofactor/manage/"
STEAM_COMMUNITY_HOME = "https://steamcommunity.com/"
STEAM_PROFILE_EDIT_URL = "https://steamcommunity.com/my/edit/info"

STEAM_SENDERS = [
    "noreply@steampowered.com",
    "no-reply@steampowered.com",
    "support@steampowered.com",
]

CONFIRM_PATTERNS = [
    r'https?://store\.steampowered\.com/account/newaccountverification\?[^\s<>"]+',
]

STEAM_GUARD_LINK_PATTERNS = [
    r'https?://store\.steampowered\.com/twofactor/[^\s<>"]+',
    r'https?://store\.steampowered\.com/account/[^\s<>"]*(?:guard|twofactor|authenticator)[^\s<>"]*',
    r'https?://store\.steampowered\.com/[^\s<>"]*(?:guard|twofactor|authenticator)[^\s<>"]*confirm[^\s<>"]*',
    r'https?://store\.steampowered\.com/[^\s<>"]*(?:confirm|disable)[^\s<>"]*(?:guard|twofactor|authenticator)[^\s<>"]*',
    r'https?://store\.steampowered\.com/[^\s<>"]*(?:guard|twofactor|authenticator)[^\s<>"]*',
]

STEAM_GUARD_CODE_PATTERNS = [
    r'Steam Guard code[:\s]*\n?\s*([A-Z0-9]{5})\b',
    r'code[:\s]*\n?\s*([A-Z0-9]{5})\b',
    r'\n\s*([A-Z0-9]{5})\s*\n',
]

def random_username() -> str:
    adjectives = [
        "dark", "silent", "ghost", "iron", "neon", "rapid", "void",
        "storm", "frost", "solar", "lunar", "toxic", "pixel", "cyber",
        "hyper", "ultra", "alpha", "omega", "turbo", "nova",
    ]
    nouns = [
        "wolf", "blade", "hawk", "fox", "raven", "viper", "titan",
        "shade", "drift", "forge", "reaper", "striker", "phantom",
        "ranger", "hunter", "cipher", "vector", "pulse", "nexus",
    ]
    return f"{random.choice(adjectives)}_{random.choice(nouns)}_{random.randint(100, 9999)}"

def random_password() -> str:
    length = random.randint(14, 22)
    pool = (
        random.choices(string.ascii_uppercase, k=3) +
        random.choices(string.ascii_lowercase, k=5) +
        random.choices(string.digits, k=3) +
        random.choices("!@#$%^&*", k=2)
    )
    while len(pool) < length:
        pool.append(random.choice(string.ascii_letters + string.digits))
    random.shuffle(pool)
    return "".join(pool)

def random_profile_name() -> str:
    patterns = [
        lambda: fake.name(),
        lambda: f"{fake.first_name()}{random.randint(1, 99)}",
        lambda: f"{fake.word().capitalize()}{fake.word().capitalize()}",
        lambda: f"xX{fake.first_name()}Xx",
        lambda: f"{fake.first_name()}_{fake.last_name()}",
        lambda: f"{fake.word().capitalize()}{random.randint(10, 9999)}",
    ]
    return random.choice(patterns)()

def get_email() -> str:
    return EMAIL_ADDRESS

def slow_type(element, text: str) -> None:
    element.clear()
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(TYPING_MIN, TYPING_MAX))

def decode_mime_header(raw: str) -> str:
    parts = decode_header(raw)
    decoded = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            decoded.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(chunk)
    return " ".join(decoded)

def get_email_body(msg: email.message.Message) -> str:
    bodies = []
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if "attachment" in cd:
                continue
            if ct in ("text/plain", "text/html"):
                charset = part.get_content_charset() or "utf-8"
                try:
                    bodies.append(part.get_payload(decode=True).decode(charset, errors="replace"))
                except Exception:
                    pass
    else:
        charset = msg.get_content_charset() or "utf-8"
        try:
            bodies.append(msg.get_payload(decode=True).decode(charset, errors="replace"))
        except Exception:
            pass
    return "\n".join(bodies)

def extract_confirm_links(body: str) -> list[str]:
    links = []
    for pattern in CONFIRM_PATTERNS:
        links.extend(re.findall(pattern, body, re.IGNORECASE))
    seen, unique = set(), []
    for link in links:
        if link not in seen:
            seen.add(link)
            unique.append(link)
    return unique

def extract_steam_guard_link(body: str) -> str | None:
    text = body.replace("&amp;", "&").replace("&nbsp;", " ")
    text_plain = re.sub(r'<[^>]+>', ' ', text)
    for source in (text, text_plain):
        for pattern in STEAM_GUARD_LINK_PATTERNS:
            m = re.search(pattern, source, re.IGNORECASE)
            if m:
                link = m.group(0).rstrip('.,;:)!?\'"<>')
                if "login" in link.lower():
                    continue
                return link
    return None

def extract_steam_guard_code(body: str) -> str | None:
    text = re.sub(r'<[^>]+>', ' ', body)
    text = re.sub(r'&nbsp;', ' ', text)
    for pattern in STEAM_GUARD_CODE_PATTERNS:
        m = re.search(pattern, text)
        if m:
            code = m.group(1)
            if len(code) == 5 and any(c.isalpha() for c in code):
                return code
    return None

def is_steam_sender(from_header: str) -> bool:
    return any(s in from_header.lower() for s in STEAM_SENDERS)

def connect_imap() -> imaplib.IMAP4_SSL:
    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    conn.login(EMAIL_ADDRESS, APP_PASSWORD)
    return conn

def confirm_link(link: str) -> bool:
    try:
        import urllib.request
        import urllib.error
        req = urllib.request.Request(link, headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            ok(f"Confirmation email link verified [{resp.status}]")
            return resp.status in (200, 302)
    except Exception as e:
        fail(f"Link confirmation failed: {e}")
        return False

def verifier_loop(stop_event: threading.Event,
                  confirmed_event: threading.Event,
                  guard_event: threading.Event,
                  state: dict) -> None:
    try:
        conn = connect_imap()
    except Exception as e:
        fail(f"IMAP connection failed: {e}")
        return

    processed: set = set()

    while not stop_event.is_set():
        try:
            conn.noop()
        except Exception:
            try:
                conn = connect_imap()
            except Exception:
                time.sleep(10)
                continue

        try:
            conn.select("INBOX")
            since = (datetime.now() - timedelta(hours=LOOKBACK_HOURS)).strftime("%d-%b-%Y")
            _, msg_ids = conn.search(None, f'(UNSEEN SINCE {since})')

            for msg_id in msg_ids[0].split():
                if msg_id in processed:
                    continue

                _, msg_data = conn.fetch(msg_id, "(RFC822)")
                raw = msg_data[0][1]
                msg = email_lib.message_from_bytes(raw)

                from_addr = decode_mime_header(msg.get("From", ""))
                subject   = decode_mime_header(msg.get("Subject", ""))

                if not is_steam_sender(from_addr):
                    continue

                body = get_email_body(msg)
                subj = subject.lower()

                if ("steam guard" in subj and
                        any(k in subj for k in ["disabl", "off", "remov", "deactiv", "confirm"])):
                    link = extract_steam_guard_link(body)
                    if link:
                        note(f"Guard email received → {C.CYAN}confirmation link{C.RESET}")
                        state["steam_guard_link"] = link
                        state["steam_guard_code"] = None
                        guard_event.set()
                        conn.store(msg_id, "+FLAGS", "\\Seen")
                        processed.add(msg_id)
                        continue

                    code = extract_steam_guard_code(body)
                    if code:
                        note(f"Guard email received → {C.CYAN}code {code}{C.RESET}")
                        state["steam_guard_code"] = code
                        state["steam_guard_link"] = None
                        guard_event.set()
                        conn.store(msg_id, "+FLAGS", "\\Seen")
                        processed.add(msg_id)
                        continue

                links = extract_confirm_links(body)
                if links:
                    note("Steam verification email received")
                    for link in links:
                        if confirm_link(link):
                            confirmed_event.set()
                    conn.store(msg_id, "+FLAGS", "\\Seen")
                    processed.add(msg_id)
                    continue

                processed.add(msg_id)

        except Exception as e:
            fail(f"Verifier error: {e}")

        time.sleep(CHECK_INTERVAL)

def build_driver() -> webdriver.Chrome:
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless=new")
        opts.add_argument("--window-size=1920,1080")
    else:
        opts.add_argument("--start-maximized")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-infobars")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=opts)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
    )
    return driver

CAPTCHA_STATE_JS = """
function visible(el) {
    if (!el) return false;
    var r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return false;
    var s = window.getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden') return false;
    return true;
}
var rc = document.getElementById('g-recaptcha-response');
var hc = document.querySelector('[name="h-captcha-response"]');
var widget =
    document.querySelector('#g-recaptcha') ||
    document.querySelector('[class*="h-captcha"]') ||
    document.querySelector('[id*="captcha"]:not(#g-recaptcha-response):not([name="h-captcha-response"])');
var ifr = document.querySelector('iframe[src*="recaptcha"], iframe[src*="hcaptcha"]');
return {
    token: (rc && rc.value) || (hc && hc.value) || null,
    widget: visible(widget) || visible(ifr)
};
"""

CAPTCHA_RESET_JS = """
try { if (typeof grecaptcha !== 'undefined' && grecaptcha.reset) grecaptcha.reset(); } catch(e) {}
try { if (typeof hcaptcha   !== 'undefined' && hcaptcha.reset)   hcaptcha.reset();   } catch(e) {}
var rc = document.getElementById('g-recaptcha-response');
if (rc) rc.value = '';
var hc = document.querySelector('[name="h-captcha-response"]');
if (hc) hc.value = '';
return true;
"""

def read_captcha_state(driver) -> dict:
    try:
        return driver.execute_script(CAPTCHA_STATE_JS) or {}
    except Exception:
        return {}

def read_captcha_token(driver) -> str:
    return read_captcha_state(driver).get("token") or ""

def wait_for_captcha_token(driver, timeout: int = None) -> bool:
    if timeout is None:
        timeout = CAPTCHA_WAIT_TIMEOUT
    deadline = time.time() + timeout
    saw_widget = False

    while time.time() < deadline:
        state = read_captcha_state(driver)
        if state.get("widget"):
            saw_widget = True
        if state.get("token"):
            return True
        time.sleep(0.25)

    return not saw_widget

def wait_for_captcha(driver: webdriver.Chrome) -> bool:
    action_box("Solve the CAPTCHA in the browser",
               "Script will continue automatically once solved")
    ok_flag = wait_for_captcha_token(driver)
    if ok_flag:
        ok("Captcha solved")
    else:
        fail("Captcha timed out")
    return ok_flag

def reacquire_fresh_captcha(driver, timeout: int = None) -> bool:
    if timeout is None:
        timeout = CAPTCHA_WAIT_TIMEOUT
    state = read_captcha_state(driver)
    old_token = state.get("token") or ""
    widget_visible = bool(state.get("widget"))

    if not widget_visible:
        return True

    try:
        driver.execute_script(CAPTCHA_RESET_JS)
    except Exception:
        pass

    action_box("Solve the new CAPTCHA in the browser",
               "A fresh token is required to continue")

    deadline = time.time() + timeout
    while time.time() < deadline:
        st = read_captcha_state(driver)
        if not st.get("widget"):
            return True
        token = st.get("token") or ""
        if token and token != old_token:
            ok("Fresh captcha solved")
            return True
        time.sleep(0.25)

    fail("Fresh captcha timed out")
    return False

def fill_email(driver: webdriver.Chrome) -> dict:
    wait = WebDriverWait(driver, 20)
    creds = {
        "email":    get_email(),
        "username": random_username(),
        "password": random_password(),
    }

    kv("Email",    creds["email"],    C.WHITE)
    kv("Username", creds["username"], C.CYAN)
    kv("Password", creds["password"], C.CYAN)

    email_field = wait.until(EC.presence_of_element_located((By.ID, "email")))
    slow_type(email_field, creds["email"])
    time.sleep(random.uniform(0.15, 0.3))

    try:
        confirm_field = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, "reenter_email"))
        )
        slow_type(confirm_field, creds["email"])
        time.sleep(random.uniform(0.1, 0.25))
    except Exception:
        pass

    return creds

def submit_email_form(driver: webdriver.Chrome) -> bool:
    wait = WebDriverWait(driver, 15)

    try:
        checkbox = wait.until(EC.presence_of_element_located((By.ID, "i_agree_check")))
        if not checkbox.is_selected():
            driver.execute_script("arguments[0].click();", checkbox)
            time.sleep(random.uniform(0.2, 0.45))
    except Exception as e:
        fail(f"Terms checkbox not found: {e}")
        return False

    try:
        btn = wait.until(EC.element_to_be_clickable((By.ID, "createAccountButton")))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        time.sleep(random.uniform(0.3, 0.6))
        try:
            btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", btn)
        ok("Form submitted — verification email requested")
        return True
    except Exception as e:
        fail(f"Continue button not found: {e}")
        return False

def find_continue_button(driver):
    try:
        modal = driver.find_element(By.CSS_SELECTOR, "dialog.newmodal[open]")
    except Exception:
        modal = None

    scope = modal if modal else driver

    try:
        candidates = scope.find_elements(By.CSS_SELECTOR, "button, a")
    except Exception:
        candidates = []

    for el in candidates:
        try:
            if (el.text or "").strip().lower() == "continue" and el.is_displayed():
                return el
        except Exception:
            continue
    return None

def page_shows_invalid_captcha(driver) -> bool:
    try:
        txt = (driver.execute_script("return document.body.innerText;") or "").lower()
    except Exception:
        return False
    return "captcha" in txt and "invalid" in txt

def page_shows_account_details(driver) -> bool:
    return bool(driver.find_elements(
        By.CSS_SELECTOR,
        "#accountname, input[name='accountname'], input[autocomplete='username']"
    ))

def click_continue_and_wait(driver, timeout: int = 20) -> bool:
    deadline = time.time() + timeout
    btn = None
    while time.time() < deadline:
        btn = find_continue_button(driver)
        if btn is not None:
            try:
                if btn.is_enabled():
                    break
            except Exception:
                pass
        time.sleep(0.3)

    if btn is None:
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        time.sleep(0.2)
    except Exception:
        pass

    try:
        btn.click()
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", btn)
        except Exception:
            return False

    end = time.time() + 15
    while time.time() < end:
        if page_shows_account_details(driver):
            return True
        if page_shows_invalid_captcha(driver):
            return False
        time.sleep(0.3)
    return False

def wait_for_continue_button(driver: webdriver.Chrome,
                             confirmed_event: threading.Event) -> bool:
    if not confirmed_event.wait(timeout=120):
        fail("Email verification timed out")
        return False

    ok("Email verified")
    time.sleep(1.0)

    for attempt in range(1, 4):
        if click_continue_and_wait(driver, timeout=20):
            ok("Advanced past 'Email In Use'")
            return True

        warn(f"Continue click didn't advance (attempt {attempt}/3) — re-solving captcha")
        if not reacquire_fresh_captcha(driver):
            return False
        time.sleep(1.0)

    fail("Could not advance past 'Email In Use' after retries")
    return False

def find_account_form_scope(driver):
    try:
        return driver.find_element(
            By.XPATH,
            "//input[@id='accountname' or @name='accountname' or @autocomplete='username']"
            "/ancestor::form[1]"
        )
    except Exception:
        return None

def find_account_submit_button(driver):
    form = find_account_form_scope(driver)
    if form is None:
        return None

    selectors = [
        "#createAccountButton",
        "button[type='submit']",
        "input[type='submit']",
        "button.btn_green_steamui",
        "button.btn_blue_steamui",
        "button",
    ]
    for sel in selectors:
        try:
            candidates = form.find_elements(By.CSS_SELECTOR, sel)
        except Exception:
            candidates = []
        for c in candidates:
            try:
                if c.is_displayed() and c.is_enabled():
                    return c
            except Exception:
                continue
    return None

def fill_account_details(driver: webdriver.Chrome, creds: dict) -> bool:
    wait = WebDriverWait(driver, 30)

    try:
        name_field = wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR,
            "#accountname, input[name='accountname'], input[autocomplete='username']"
        )))
        slow_type(name_field, creds["username"])
        time.sleep(random.uniform(0.15, 0.3))
    except Exception as e:
        fail(f"Account name field not found: {e}")
        return False

    try:
        pw_fields = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
        if len(pw_fields) >= 2:
            slow_type(pw_fields[0], creds["password"])
            time.sleep(random.uniform(0.1, 0.25))
            slow_type(pw_fields[1], creds["password"])
            time.sleep(random.uniform(0.15, 0.3))
        elif pw_fields:
            slow_type(pw_fields[0], creds["password"])
    except Exception as e:
        fail(f"Password fields failed: {e}")
        return False

    try:
        for cb in driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']"):
            try:
                if cb.is_displayed() and not cb.is_selected():
                    driver.execute_script("arguments[0].click();", cb)
                    time.sleep(random.uniform(0.15, 0.3))
            except Exception:
                continue
    except Exception:
        pass

    state = read_captcha_state(driver)
    if state.get("widget"):
        if not reacquire_fresh_captcha(driver):
            warn("No fresh captcha token — attempting submit anyway")

    submit_btn = None
    deadline = time.time() + 20
    while time.time() < deadline:
        submit_btn = find_account_submit_button(driver)
        if submit_btn is not None:
            break
        time.sleep(0.3)

    if submit_btn is None:
        fail("Submit button not found in account form")
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", submit_btn)
        time.sleep(random.uniform(0.3, 0.5))
    except Exception:
        pass

    try:
        submit_btn.click()
    except Exception:
        driver.execute_script("arguments[0].click();", submit_btn)

    time.sleep(2.5)
    after_url = driver.current_url

    if "/search" in after_url:
        fail("Wrong submit button clicked (landed on search)")
        return False

    body = ""
    try:
        body = (driver.execute_script("return document.body.innerText;") or "").lower()
    except Exception:
        pass

    if "captcha" in body and "invalid" in body:
        fail("Steam reports captcha invalid on final submit")
        return False
    if "account name" in body and "already" in body:
        fail("Account name already taken")
        return False

    return True

def find_first_element(driver, xpaths, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for xp in xpaths:
            try:
                els = driver.find_elements(By.XPATH, xp)
            except Exception:
                continue
            for el in els:
                try:
                    if el.is_displayed():
                        return el
                except Exception:
                    continue
        time.sleep(0.2)
    return None

def radio_is_checked(driver, radio_input) -> bool:
    if radio_input is None:
        return True
    try:
        return bool(driver.execute_script("return arguments[0].checked;", radio_input))
    except Exception:
        return True

def select_radio_by_id(driver, element_id: str) -> bool:
    radio_input = None
    try:
        radio_input = driver.find_element(By.ID, element_id)
    except Exception:
        pass

    label = None
    try:
        label = driver.find_element(By.CSS_SELECTOR, f"label[for='{element_id}']")
    except Exception:
        pass
    if label is None:
        try:
            label = driver.find_element(
                By.XPATH, f"//label[.//input[@id='{element_id}']]"
            )
        except Exception:
            pass

    if label is not None:
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", label)
            time.sleep(0.15)
            label.click()
            time.sleep(0.3)
            if radio_is_checked(driver, radio_input):
                return True
        except Exception:
            pass

        try:
            ActionChains(driver).move_to_element(label).click().perform()
            time.sleep(0.3)
            if radio_is_checked(driver, radio_input):
                return True
        except Exception:
            pass

    if radio_input is not None:
        try:
            driver.execute_script("arguments[0].click();", radio_input)
            time.sleep(0.3)
            if radio_is_checked(driver, radio_input):
                return True
        except Exception:
            pass

        try:
            driver.execute_script("""
                var input = arguments[0];
                input.checked = true;
                ['mousedown','mouseup','click','input','change'].forEach(function(evt) {
                    try { input.dispatchEvent(new Event(evt, {bubbles: true, cancelable: true})); } catch (e) {}
                    try { input.dispatchEvent(new MouseEvent(evt, {bubbles: true, cancelable: true})); } catch (e) {}
                });
            """, radio_input)
            time.sleep(0.3)
            if radio_is_checked(driver, radio_input):
                return True
        except Exception:
            pass

    return False

def try_reveal_disable_button(driver, timeout: int = 6):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            els = driver.find_elements(
                By.XPATH,
                "//button[normalize-space(.)='Disable Steam Guard'] | "
                "//a[normalize-space(.)='Disable Steam Guard'] | "
                "//*[contains(@class, 'btn_green') and contains(., 'Disable Steam Guard')] | "
                "//*[normalize-space(text())='Disable Steam Guard']"
            )
            for el in els:
                try:
                    if el.is_displayed() and el.is_enabled():
                        return el
                except Exception:
                    continue
        except Exception:
            pass
        time.sleep(0.2)
    return None

def disable_steam_guard(driver: webdriver.Chrome,
                        creds: dict,
                        guard_event: threading.Event,
                        state: dict) -> bool:
    try:
        driver.get(STEAM_GUARD_URL)
        time.sleep(2.0)
    except Exception as e:
        fail(f"Could not load Steam Guard page: {e}")
        return False

    try:
        body = (driver.execute_script("return document.body.innerText;") or "").lower()
        if "no mobile authenticator" in body or "isn't currently linked" in body:
            ok("Steam Guard is already off")
            return True
    except Exception:
        pass

    select_radio_by_id(driver, "email_authenticator_check")
    time.sleep(1.2)
    select_radio_by_id(driver, "none_authenticator_check")

    disable_btn = try_reveal_disable_button(driver, timeout=6)

    if disable_btn is None:
        try:
            driver.execute_script("""
                var inputs = document.querySelectorAll('input[type="radio"]');
                for (var i = 0; i < inputs.length; i++) {
                    var inp = inputs[i];
                    if ((inp.id || '').indexOf('none_authenticator') !== -1) {
                        inp.checked = true;
                        inp.dispatchEvent(new Event('change', {bubbles: true}));
                        inp.dispatchEvent(new Event('click', {bubbles: true}));
                    }
                }
            """)
            time.sleep(1.0)
        except Exception:
            pass
        disable_btn = try_reveal_disable_button(driver, timeout=5)

    if disable_btn is None:
        action_box("Manual step required",
                   "Select 'Turn Steam Guard off' and confirm in the browser")
        input(f"     {C.GRAY}press ENTER when done → {C.RESET}")
        disable_btn = try_reveal_disable_button(driver, timeout=4)

    if disable_btn is not None:
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", disable_btn)
            time.sleep(0.3)
            try:
                disable_btn.click()
            except Exception:
                driver.execute_script("arguments[0].click();", disable_btn)
            ok("Disable Steam Guard clicked")
        except Exception as e:
            fail(f"Could not click Disable button: {e}")

    note("Waiting for confirmation email...")
    if not guard_event.wait(timeout=120):
        fail("Steam Guard email timed out")
        action_box("Manual step required",
                   "Finish disabling Steam Guard in the browser")
        input(f"     {C.GRAY}press ENTER when done → {C.RESET}")
        return True

    link = state.get("steam_guard_link")
    code = state.get("steam_guard_code")

    if link:
        try:
            driver.get(link)
        except Exception as e:
            fail(f"Could not open confirmation link: {e}")
            return False

        deadline = time.time() + 12
        last_click_time = 0.0
        while time.time() < deadline:
            try:
                body = (driver.execute_script(
                    "return document.body.innerText;"
                ) or "").lower()
            except Exception:
                body = ""

            if ("steam guard" in body and
                    ("disabled" in body or "successfully" in body or
                     "no longer" in body or "has been disabled" in body)):
                ok("Steam Guard disabled")
                return True

            now = time.time()
            if now - last_click_time > 1.0:
                btn = find_first_element(driver, [
                    "//button[normalize-space(.)='Disable Steam Guard']",
                    "//button[contains(., 'Confirm') and contains(., 'Disable')]",
                    "//a[contains(., 'Confirm')]",
                ], timeout=0.5)
                if btn is not None:
                    try:
                        btn.click()
                        last_click_time = now
                    except Exception:
                        pass

            time.sleep(0.3)

        ok("Steam Guard disabled")
        return True

    if code:
        note(f"Entering code {C.CYAN}{code}{C.RESET}")

        code_field = find_first_element(driver, [
            "//input[@type='text' and @maxlength='5']",
            "//input[contains(@id,'code') and @type='text']",
            "//input[contains(@name,'code') and @type='text']",
            "//input[@type='text']",
        ], timeout=12)

        if code_field is None:
            action_box("Manual step required", "Enter the Steam Guard code in the browser")
            input(f"     {C.GRAY}press ENTER when done → {C.RESET}")
            return True

        try:
            slow_type(code_field, code)
            time.sleep(0.3)
            try:
                code_field.send_keys(Keys.ENTER)
            except Exception:
                pass

            try:
                submit_btn = driver.find_element(
                    By.XPATH,
                    "//button[contains(., 'Submit') or contains(., 'Confirm') "
                    "or contains(., 'Continue') or contains(., 'Disable')]"
                )
                if submit_btn.is_displayed() and submit_btn.is_enabled():
                    try:
                        submit_btn.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", submit_btn)
            except Exception:
                pass

            time.sleep(1.5)
        except Exception as e:
            fail(f"Could not auto-fill code: {e}")
            return False

        try:
            body = (driver.execute_script("return document.body.innerText;") or "").lower()
        except Exception:
            body = ""

        if "disabled" in body or "successfully" in body:
            ok("Steam Guard disabled")
            return True

        action_box("Manual confirmation required",
                   "Verify Steam Guard is off in the browser")
        input(f"     {C.GRAY}press ENTER when done → {C.RESET}")
        return True

    fail("Steam Guard email contained neither a link nor a code")
    return False

def find_profile_name_field(driver):
    selectors = [
        (By.ID, "personaName"),
        (By.CSS_SELECTOR, "input[name='personaName']"),
        (By.CSS_SELECTOR, "form#editForm input[type='text']"),
        (By.CSS_SELECTOR, "input[type='text'][maxlength='32']"),
        (By.XPATH,
         "//div[contains(translate(., 'abcdefghijklmnopqrstuvwxyz', "
         "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'PROFILE NAME')]"
         "/following::input[@type='text'][1]"),
        (By.XPATH,
         "//*[contains(translate(., 'abcdefghijklmnopqrstuvwxyz', "
         "'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'PROFILE NAME')]"
         "/following::input[@type='text'][1]"),
    ]

    for by, sel in selectors:
        try:
            els = driver.find_elements(by, sel)
        except Exception:
            continue
        for el in els:
            try:
                if el.is_displayed() and el.is_enabled():
                    return el
            except Exception:
                continue
    return None

def randomize_profile(driver: webdriver.Chrome) -> str | None:
    try:
        driver.get(STEAM_COMMUNITY_HOME)
        time.sleep(1.5)
    except Exception as e:
        fail(f"Could not reach steamcommunity.com: {e}")
        return None

    try:
        driver.get(STEAM_PROFILE_EDIT_URL)
        time.sleep(1.5)
    except Exception as e:
        fail(f"Could not load profile edit page: {e}")
        return None

    if "login" in driver.current_url.lower():
        fail("Not logged in to Steam Community — cannot edit profile")
        return None

    name_field = None
    deadline = time.time() + 15
    while time.time() < deadline:
        name_field = find_profile_name_field(driver)
        if name_field is not None:
            break
        time.sleep(0.3)

    if name_field is None:
        try:
            inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
            note(f"Page has {len(inputs)} text inputs:")
            for i, inp in enumerate(inputs[:6]):
                note(f"  [{i}] id='{inp.get_attribute('id')}' "
                     f"name='{inp.get_attribute('name')}' "
                     f"maxlength='{inp.get_attribute('maxlength')}'")
        except Exception:
            pass
        fail("Profile name field not found")
        return None

    new_name = random_profile_name()
    note(f"New profile name: {C.CYAN}{new_name}{C.RESET}")

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", name_field)
        time.sleep(0.2)
        try:
            name_field.send_keys(Keys.CONTROL, "a")
            name_field.send_keys(Keys.DELETE)
        except Exception:
            try:
                name_field.clear()
            except Exception:
                pass
        time.sleep(0.15)
        slow_type(name_field, new_name)
        time.sleep(random.uniform(0.25, 0.4))
    except Exception as e:
        fail(f"Could not type profile name: {e}")
        return None

    try:
        actual = name_field.get_attribute("value") or ""
        if actual.strip() != new_name:
            warn(f"Field value mismatch: '{actual}' != '{new_name}'")
            return None
    except Exception:
        pass

    save_btn = find_first_element(driver, [
        "//button[normalize-space(.)='Save']",
        "//button[normalize-space(.)='Save Changes']",
        "//button[contains(., 'Save Changes')]",
        "//span[normalize-space(.)='Save']/ancestor::button[1]",
        "//span[normalize-space(.)='Save Changes']/ancestor::button[1]",
        "//span[normalize-space(.)='Save']/ancestor::a[1]",
        "//span[normalize-space(.)='Save Changes']/ancestor::a[1]",
        "//div[normalize-space(.)='Save']",
        "//input[@type='submit' and contains(@value, 'Save')]",
        "//*[@id='editForm']//button[@type='submit']",
        "//form[contains(@action, 'edit')]//button[@type='submit']",
    ], timeout=8)

    if save_btn is None:
        fail("Save button not found")
        return None

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", save_btn)
        time.sleep(0.2)
    except Exception:
        pass

    try:
        save_btn.click()
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", save_btn)
        except Exception as e:
            fail(f"Could not click Save: {e}")
            return None

    end = time.time() + 5.0
    while time.time() < end:
        try:
            toast = driver.find_elements(
                By.CSS_SELECTOR,
                ".newmodal_content, .toast, .success, .notification, "
                ".profile_updated, [class*='toast'], [class*='success']"
            )
            for t in toast:
                try:
                    txt = (t.text or "").lower()
                    if t.is_displayed() and (
                        "saved" in txt or "updated" in txt or "success" in txt
                    ):
                        ok(f"Profile name set to {C.CYAN}{new_name}{C.RESET}")
                        return new_name
                except Exception:
                    continue
        except Exception:
            pass

        try:
            check = driver.find_element(By.ID, "personaName")
            val = (check.get_attribute("value") or "").strip()
            if val == new_name:
                ok(f"Profile name set to {C.CYAN}{new_name}{C.RESET}")
                return new_name
        except Exception:
            pass

        try:
            body = (driver.execute_script(
                "return document.body.innerText;"
            ) or "").lower()
            if "error" in body and "profile name" in body:
                fail("Steam rejected the new profile name")
                return None
        except Exception:
            pass

        time.sleep(0.15)

    ok(f"Profile name saved: {C.CYAN}{new_name}{C.RESET}")
    return new_name

def save_credentials(creds: dict) -> None:
    line = f"{creds['username']}:{creds['password']}"
    name = creds.get("profile_name")
    if name:
        line += f" - {name}"
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def main() -> None:
    load_config()
    banner()

    stop_event       = threading.Event()
    confirmed_event  = threading.Event()
    guard_event      = threading.Event()
    state = {"steam_guard_code": None, "steam_guard_link": None}

    verifier_thread = threading.Thread(
        target=verifier_loop,
        args=(stop_event, confirmed_event, guard_event, state),
        daemon=True
    )
    verifier_thread.start()

    driver = build_driver()
    try:
        total = 3
        if DISABLE_STEAM_GUARD:
            total += 1
        if RANDOMIZE_PROFILE:
            total += 1

        current = 0

        current += 1
        step(current, total, "Creating account")
        driver.get(STEAM_CREATE_URL)
        time.sleep(1.5)

        creds = fill_email(driver)

        if not wait_for_captcha(driver):
            fail("Captcha not solved — aborting")
            return

        if not submit_email_form(driver):
            return

        current += 1
        step(current, total, "Verifying email")
        if not wait_for_continue_button(driver, confirmed_event):
            return

        current += 1
        step(current, total, "Finalizing account")
        if not fill_account_details(driver, creds):
            fail("Account details step failed")
            return

        try:
            if DISABLE_STEAM_GUARD:
                current += 1
                step(current, total, "Disabling Steam Guard")
                if not disable_steam_guard(driver, creds, guard_event, state):
                    fail("Steam Guard disable step failed")

            if RANDOMIZE_PROFILE:
                current += 1
                step(current, total, "Randomizing profile")
                profile_name = randomize_profile(driver)
                if not profile_name:
                    fail("Profile randomization failed")
                else:
                    creds["profile_name"] = profile_name
        finally:
            save_credentials(creds)
            ok(f"Account saved to {OUTPUT_FILE}")

        done_banner(creds)

        input(f"  {C.GRAY}press ENTER to close...{C.RESET}")

    except Exception as e:
        fail(f"Fatal: {e}")
    finally:
        stop_event.set()
        driver.quit()

if __name__ == "__main__":
    main()