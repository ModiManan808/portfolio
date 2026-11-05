# -*- coding: utf-8 -*-
"""
CTF Writeup Archive Generator
Recursively scans C:\\Users\\modim\\CTF and generates a polished, self-contained HTML archive.
"""

import os
import re
import json
import base64
import html
from collections import defaultdict

ROOT_DIR = r"C:\Users\modim\CTF"
PORTFOLIO_DIR = r"C:\Users\modim\Code\Portfolio"
LOGO_PATH = os.path.join(PORTFOLIO_DIR, "download.jpg")
OUT_HTML = os.path.join(PORTFOLIO_DIR, "index.html")
OUT_HTML_BACKUP = os.path.join(PORTFOLIO_DIR, "ctf-archive.html")

CATEGORY_ICONS = {
    "Crypto": "🔐",
    "Cryptography": "🔐",
    "Web": "🌐",
    "Forensic": "🔍",
    "Forensics": "🔍",
    "Mobile": "📱",
    "Reversing": "⚙️",
    "Reverse Engineering": "⚙️",
    "Pwn": "💥",
    "OSINT": "🕵️",
    "Misc": "🎲",
    "AI-ML": "🤖",
}

def get_cat_icon(cat):
    return CATEGORY_ICONS.get(cat, "🚩")

def slugify(text):
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return text or "section"

def parse_inline(text):
    text = html.escape(text, quote=True)
    # Inline code
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    # Bold italic
    text = re.sub(r"\*\*\*([^*]+)\*\*\*", r"<strong><em>\1</em></strong>", text)
    # Bold
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    # Italic
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    # Markdown Links
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    return text

def convert_markdown_to_html(md_text):
    lines = md_text.replace("\r\n", "\n").split("\n")
    output = []
    i = 0
    in_list = None
    in_table = False
    table_headers = []
    table_rows = []

    def close_list():
        nonlocal in_list
        if in_list:
            output.append(f"</{in_list}>")
            in_list = None

    def close_table():
        nonlocal in_table, table_headers, table_rows
        if in_table:
            t = ["<table><thead><tr>"]
            for th in table_headers:
                t.append(f"<th>{th}</th>")
            t.append("</tr></thead><tbody>")
            for r in table_rows:
                t.append("<tr>")
                for td in r:
                    t.append(f"<td>{td}</td>")
                t.append("</tr>")
            t.append("</tbody></table>")
            output.append("".join(t))
            in_table = False
            table_headers = []
            table_rows = []

    while i < len(lines):
        line = lines[i]

        # Fenced code block
        if line.strip().startswith("```"):
            close_list()
            close_table()
            lang = line.strip()[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # consume closing ```
            code_content = html.escape("\n".join(code_lines))
            lang_attr = f' class="language-{lang}"' if lang else ""
            output.append(
                f'<div class="code-block"><button class="copy-btn">COPY</button><pre><code{lang_attr}>{code_content}</code></pre></div>'
            )
            continue

        # Table row
        if "|" in line:
            if not in_table and i + 1 < len(lines) and re.match(r"^\s*\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$", lines[i+1]):
                close_list()
                in_table = True
                cols = [c.strip() for c in line.split("|")]
                if cols and cols[0] == "": cols.pop(0)
                if cols and cols[-1] == "": cols.pop()
                table_headers = [parse_inline(c) for c in cols]
                i += 2
                table_rows = []
                continue
            elif in_table:
                if re.match(r"^\s*\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$", line):
                    i += 1
                    continue
                cols = [c.strip() for c in line.split("|")]
                if cols and cols[0] == "": cols.pop(0)
                if cols and cols[-1] == "": cols.pop()
                table_rows.append([parse_inline(c) for c in cols])
                i += 1
                continue

        if in_table:
            close_table()

        # Blank line
        if not line.strip():
            close_list()
            close_table()
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^\s*([-*_]\s*){3,}\s*$", line):
            close_list()
            close_table()
            output.append("<hr />")
            i += 1
            continue

        # Headings
        m_h = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m_h:
            close_list()
            close_table()
            level = len(m_h.group(1))
            htext = m_h.group(2).strip()
            hslug = slugify(htext)
            output.append(f'<h{level} id="{hslug}">{parse_inline(htext)}</h{level}>')
            i += 1
            continue

        # Blockquote
        if line.strip().startswith(">"):
            close_list()
            close_table()
            bq_lines = []
            while i < len(lines) and (lines[i].strip().startswith(">") or (lines[i].strip() and bq_lines)):
                if lines[i].strip().startswith(">"):
                    bq_lines.append(re.sub(r"^\s*>\s?", "", lines[i]))
                else:
                    break
                i += 1
            bq_html = convert_markdown_to_html("\n".join(bq_lines))
            output.append(f"<blockquote>{bq_html}</blockquote>")
            continue

        # Unordered list
        m_ul = re.match(r"^\s*[-*+]\s+(.+)$", line)
        if m_ul:
            close_table()
            if in_list != "ul":
                close_list()
                output.append("<ul>")
                in_list = "ul"
            output.append(f"<li>{parse_inline(m_ul.group(1))}</li>")
            i += 1
            continue

        # Ordered list
        m_ol = re.match(r"^\s*(\d+)\.\s+(.+)$", line)
        if m_ol:
            close_table()
            if in_list != "ol":
                close_list()
                output.append("<ol>")
                in_list = "ol"
            output.append(f"<li>{parse_inline(m_ol.group(2))}</li>")
            i += 1
            continue

        # Normal paragraph
        close_list()
        close_table()
        p_lines = [line]
        i += 1
        while (i < len(lines) and lines[i].strip() and
               not lines[i].strip().startswith(("#", "```", ">", "|", "- ", "* ", "+ ")) and
               not re.match(r"^\s*\d+\.\s+", lines[i])):
            p_lines.append(lines[i])
            i += 1
        output.append(f"<p>{parse_inline(' '.join(p_lines))}</p>")

    close_list()
    close_table()
    return "\n".join(output)

# Specific curated data corrections for challenges with unique structures
WRITEUP_OVERWRITES = {
    "dual_linera": {
        "flag": "OmniCTF{crt_makes_a_tiny_nonce_without_leaking_it}",
        "title": "Dual Linear",
        "category": "Crypto",
    },
    "orbital-strike-cannon": {
        "title": "Orbital Strike Cannon",
        "category": "Crypto",
    },
    "Whiskerfield-Meowtin": {
        "title": "CuteSecure-DH MITM",
        "category": "Crypto",
    },
    "baccarat": {
        "title": "Baccarat Duel Betting Challenge",
        "category": "Misc",
    },
    "Downsize": {
        "title": "Downsize",
        "category": "Misc",
    },
    "Gridpilot": {
        "title": "Gridpilot Copilot Tool Abuse",
        "category": "Web",
    },
    "8": {
        "title": "Maya's Veil (Challenge 8)",
        "category": "Misc",
    },
    "9": {
        "title": "Maya Never Lies (Challenge 9)",
        "category": "Misc",
    },
    "The_Keymaster": {
        "title": "Flag Fragments (Warmup)",
        "category": "Web",
    },
    "Atomic_Substitution_Theory": {
        "title": "Atomic Substitution Theory",
        "category": "Crypto",
    },
    "Digital_Crumbs": {
        "title": "Digital Crumbs",
        "category": "OSINT",
    },
    "Negative_Bread": {
        "title": "Negative Bread",
        "category": "Reversing",
    },
    "No_Laughing_Matter": {
        "title": "No Laughing Matter",
        "category": "Crypto",
    },
    "Pwntutorial": {
        "title": "Pwntorial Buffer Overflow",
        "category": "Pwn",
    },
    "THE_DATABASE": {
        "title": "THE DATABASE (Anonymous Auth)",
        "category": "Mobile",
    },
    "THE_VAULT": {
        "title": "THE VAULT (Firebase App Check Bypass)",
        "category": "Mobile",
    },
    "THE_ENDPOINT": {
        "title": "THE ENDPOINT (Native Request Signing Bypass)",
        "category": "Mobile",
    },
    "THE_LIBRARY": {
        "title": "THE LIBRARY (Static Analysis)",
        "category": "Reversing",
    },
    "THE_VAULT_DOOR": {
        "title": "THE VAULT DOOR (NexaVault JWT None Bypass)",
        "category": "Web",
    },
    "Mement0": {
        "title": "Mement0 (Git Archaeology & Prompt Injection)",
        "category": "AI-ML",
    },
    "Whisper": {
        "title": "AI Tool Exfiltration (Ollama / TinyLlama)",
        "category": "Forensic",
    },
    "Small_Root": {
        "title": "Small Root (e = 3 RSA)",
        "category": "Crypto",
    },
    "Mailroom_Echo": {
        "title": "Mailroom Echo (MIME Base64)",
        "category": "Forensic",
    },
    "Pcap_secret": {
        "title": "PCAP Secret (Header X-Sync-Token)",
        "category": "Forensic",
    },
}

def scan_writeups():
    writeups = []
    skipped_folders = set()
    event_writeup_count = defaultdict(int)

    # List all top-level event folders
    events = [d for d in os.listdir(ROOT_DIR) if os.path.isdir(os.path.join(ROOT_DIR, d))]

    for ev in events:
        ev_dir = os.path.join(ROOT_DIR, ev)

        for dirpath, dirnames, filenames in os.walk(ev_dir):
            for fname in filenames:
                lower_name = fname.lower()
                is_candidate = (
                    re.match(r"^(readme|writeup|solution)\.(md|txt)$", lower_name) or
                    "writeup" in lower_name and lower_name.endswith((".md", ".txt")) or
                    lower_name in ["solution.txt", "writeup.txt"]
                )
                if not is_candidate:
                    continue

                full_path = os.path.join(dirpath, fname)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                        raw_content = f.read()
                except Exception:
                    continue

                # Filter out pure repositories, challenge descriptions without solutions, or malware warnings
                if "GitTools" in dirpath or "internetwache/GitTools" in raw_content:
                    skipped_folders.add(f"{ev}/Osint/GitTools")
                    continue
                if "training-challenge" in dirpath or "intro-pwn-1" in dirpath:
                    skipped_folders.add(f"{ev}/intro-pwn-1")
                    continue
                if "Fatmike_02_Handout" in dirpath:
                    skipped_folders.add(f"{ev}/Fatmike_02_Handout")
                    continue
                if "case_01" in dirpath and "Nine frames remain" in raw_content:
                    skipped_folders.add(f"{ev}/case_01")
                    continue
                if "Operation_Nightshade" in dirpath:
                    skipped_folders.add(f"{ev}/Operation_Nightshade")
                    continue
                if "UNcrackable" in dirpath:
                    skipped_folders.add(f"{ev}/UNcrackable")
                    continue
                if "GeoOSINT" in dirpath and "You are given 6 images" in raw_content:
                    skipped_folders.add(f"{ev}/GeoOSINT")
                    continue
                if "Miletus" in dirpath and "WARNING: This archive contains a real malware sample" in raw_content:
                    skipped_folders.add(f"{ev}/Miletus")
                    continue
                if lower_name == "readme.md" and "Crownspire Registry -- Copy-Set" in raw_content:
                    continue
                if len(raw_content.strip()) < 15:
                    continue

                # Identify challenge name and folder
                chal_dir = os.path.basename(dirpath)
                parent_dir = os.path.basename(os.path.dirname(dirpath))

                # Check if this challenge is in our known writeups
                ovr = WRITEUP_OVERWRITES.get(chal_dir, {})

                # Extract category
                category = ovr.get("category", "")
                if not category:
                    m_cat = re.search(r"(?i)\*\*Category:\*\*\s*([^\n\r]+)", raw_content)
                    if not m_cat:
                        m_cat = re.search(r"(?i)Category:\s*([^\n\r|]+)", raw_content)
                    if m_cat:
                        raw_cat = re.split(r"[/|•,]", m_cat.group(1).strip())[0].strip()
                        category = raw_cat
                    elif parent_dir and parent_dir != ev:
                        category = parent_dir
                    else:
                        category = "Misc"

                # Normalize category
                c_low = category.lower()
                if "crypto" in c_low: category = "Crypto"
                elif "web" in c_low: category = "Web"
                elif "forensic" in c_low: category = "Forensic"
                elif "mobile" in c_low or "firebase" in c_low: category = "Mobile"
                elif "pwn" in c_low: category = "Pwn"
                elif "osint" in c_low: category = "OSINT"
                elif "rev" in c_low: category = "Reversing"
                elif "ai" in c_low or "ml" in c_low: category = "AI-ML"
                elif "misc" in c_low or category in ["8", "9"]: category = "Misc"

                # Extract title
                title = ovr.get("title", "")
                if not title:
                    m_title = re.search(r"^#\s+(.+)$", raw_content, re.MULTILINE)
                    if m_title:
                        title = m_title.group(1).strip()
                        title = re.sub(r"(?i)\s*[-—]\s*(write-?up|solution).*$", "", title).strip()
                    else:
                        title = chal_dir.replace("_", " ").title()

                # Extract flag
                flag = ovr.get("flag", "")
                if not flag:
                    flag_matches = re.findall(r"([A-Za-z0-9_-]+)\{([^}\r\n]{3,120})\}", raw_content)
                    if flag_matches:
                        prefix, body = flag_matches[-1]
                        flag = f"{prefix}{{{body}}}"

                # Extract difficulty, points, target
                difficulty = ""
                m_diff = re.search(r"(?i)\*\*Difficulty:\*\*\s*([^\n\r]+)", raw_content)
                if m_diff: difficulty = m_diff.group(1).strip()

                points = ""
                m_pts = re.search(r"(?i)(\d+)\s*(?:pts|points)", raw_content)
                if m_pts: points = m_pts.group(1).strip()

                target = ""
                m_targ = re.search(r"(?i)\*\*Target:\*\*\s*([^\n\r]+)", raw_content)
                if m_targ:
                    target = m_targ.group(1).strip()
                elif "Target:" in raw_content:
                    m_targ2 = re.search(r"(?i)Target:\s*`?([^\n\r`]+)`?", raw_content)
                    if m_targ2: target = m_targ2.group(1).strip()

                # Extract challenge prompt/description
                prompt = ""
                m_desc = re.search(r"(?i)##\s*(?:Challenge\s*Description|Description|Challenge\s*prompt)[^\n]*\n+((?:>.*\n?)+)", raw_content)
                if m_desc:
                    prompt = "\n".join(re.sub(r"^\s*>\s?", "", l) for l in m_desc.group(1).split("\n")).strip()

                body_html = convert_markdown_to_html(raw_content)
                cid = f"{slugify(ev)}-{slugify(chal_dir)}"

                writeups.append({
                    "id": cid,
                    "event": ev,
                    "category": category,
                    "challenge": chal_dir,
                    "title": title,
                    "flag": flag,
                    "difficulty": difficulty,
                    "points": points,
                    "target": target,
                    "prompt": prompt,
                    "body_html": body_html,
                    "path": full_path,
                })
                event_writeup_count[ev] += 1

    # Add any event with 0 writeups to skipped folders
    for ev in events:
        if event_writeup_count[ev] == 0:
            skipped_folders.add(ev)

    return writeups, sorted(list(skipped_folders))

def generate_site():
    writeups, skipped_folders = scan_writeups()

    # Sort writeups by Category, then Event, then Challenge Title
    writeups.sort(key=lambda w: (w["category"], w["event"], w["title"]))

    # Prepare Logo
    logo_data_uri = ""
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as lf:
            b64_logo = base64.b64encode(lf.read()).decode("ascii")
            logo_data_uri = f"data:image/jpeg;base64,{b64_logo}"

    categories = sorted(list(set(w["category"] for w in writeups)))
    events = sorted(list(set(w["event"] for w in writeups)))
    flags_captured = sum(1 for w in writeups if w["flag"])

    challenges_json = json.dumps([{
        "id": w["id"],
        "event": w["event"],
        "category": w["category"],
        "icon": get_cat_icon(w["category"]),
        "challenge": w["challenge"],
        "title": w["title"],
        "flag": w["flag"],
        "difficulty": w["difficulty"],
        "points": w["points"],
        "target": w["target"],
        "prompt": w["prompt"],
        "body_html": w["body_html"]
    } for w in writeups], ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
<title>🚩 CTF Archive — Writeups</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,600;0,700;1,500&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --cream:#f4f0e6;
    --cream-2:#ece6d6;
    --ink:#1c1a15;
    --ink-soft:#55503f;
    --rule:#ddd5bd;
    --terracotta:#c1501f;
    --terracotta-soft:#e9c9b4;
    --card:#fbf9f2;
    --code-bg:#17150f;
    --code-text:#f2ead9;
    --green:#4d7a4a;
    color-scheme: light;
  }}
  *, *::before, *::after {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; height: 100%; }}
  body {{
    background: var(--cream);
    color: var(--ink);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 15px;
    line-height: 1.65;
    padding-top: env(safe-area-inset-top, 0px);
    padding-bottom: env(safe-area-inset-bottom, 0px);
  }}
  a {{ color: var(--terracotta); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  code {{ font-family: 'JetBrains Mono', monospace; }}

  /* Layout */
  .app {{ display: flex; min-height: 100vh; }}
  
  /* Sidebar */
  .sidebar {{
    width: 252px;
    min-width: 252px;
    flex-shrink: 0;
    background: var(--cream-2);
    border-right: 1px solid var(--rule);
    padding: 22px 14px 40px;
    position: sticky;
    top: 0;
    height: 100vh;
    overflow-y: auto;
  }}
  .brand {{
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 2px 6px 18px;
    border-bottom: 1px solid var(--rule);
    margin-bottom: 12px;
    cursor: pointer;
  }}
  .brand .logo-img {{
    width: 34px;
    height: 34px;
    border-radius: 8px;
    object-fit: cover;
    border: 1px solid var(--rule);
    flex-shrink: 0;
  }}
  .brand .logo-fallback {{
    width: 34px;
    height: 34px;
    border-radius: 8px;
    background: var(--terracotta);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    font-size: 16px;
    border: 1px solid var(--rule);
    flex-shrink: 0;
  }}
  .brand-text {{ display: flex; flex-direction: column; }}
  .brand-text .site-name {{
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: 18px;
    color: var(--ink);
    letter-spacing: 0.2px;
    line-height: 1.2;
  }}
  .brand-text .site-sub {{
    font-size: 11px;
    color: var(--ink-soft);
    font-family: 'Inter', sans-serif;
    font-weight: 500;
  }}

  /* Sidebar Navigation */
  .nav-item {{
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 8px 10px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    color: var(--ink-soft);
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    user-select: none;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .nav-item:hover {{
    background: rgba(193, 80, 31, 0.08);
    color: var(--ink);
  }}
  .nav-item.active {{
    background: var(--ink);
    color: var(--cream);
  }}
  .nav-item.active .ic {{ color: var(--cream); }}
  .nav-item .ic {{
    width: 18px;
    text-align: center;
    font-size: 13px;
    flex-shrink: 0;
  }}
  .nav-item-title {{
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  .nav-label {{
    margin-top: 16px;
    margin-bottom: 5px;
    padding: 0 10px;
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: #8a8368;
    text-transform: uppercase;
  }}

  /* Main area */
  .main {{
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }}
  .topbar {{
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 12px 32px;
    border-bottom: 1px solid var(--rule);
    position: sticky;
    top: 0;
    background: var(--cream);
    z-index: 10;
  }}
  .search-wrap {{
    flex: 1;
    max-width: 480px;
    position: relative;
    display: flex;
    align-items: center;
  }}
  .search-input {{
    width: 100%;
    background: var(--card);
    border: 1px solid var(--rule);
    border-radius: 7px;
    padding: 8px 12px 8px 34px;
    color: var(--ink);
    font-family: 'Inter', sans-serif;
    font-size: 13.5px;
    outline: none;
    transition: border-color 0.15s, box-shadow 0.15s;
  }}
  .search-input:focus {{
    border-color: var(--terracotta);
    box-shadow: 0 0 0 2px var(--terracotta-soft);
  }}
  .search-icon {{
    position: absolute;
    left: 11px;
    font-size: 13px;
    color: #9a927a;
    pointer-events: none;
  }}
  .top-right {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-left: auto;
    font-size: 12.5px;
    color: var(--ink-soft);
  }}
  .pill {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11.5px;
    background: var(--card);
    border: 1px solid var(--rule);
    border-radius: 20px;
    padding: 4px 11px;
    color: var(--ink-soft);
    font-weight: 500;
  }}

  /* Content area */
  .content {{
    flex: 1;
    display: flex;
  }}
  .col-main {{
    flex: 1;
    padding: 34px 40px 80px;
    max-width: 900px;
    min-width: 0;
  }}
  .col-toc {{
    width: 250px;
    flex-shrink: 0;
    padding: 34px 24px 40px;
    border-left: 1px solid var(--rule);
    position: sticky;
    top: 57px;
    align-self: flex-start;
    max-height: calc(100vh - 57px);
    overflow-y: auto;
  }}

  /* Typography & Elements */
  h1.page-title {{
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: 34px;
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 0 0 14px;
    line-height: 1.25;
    color: var(--ink);
  }}
  .divider {{
    border: none;
    border-top: 1px solid var(--rule);
    margin: 16px 0 24px;
  }}
  .lede {{
    font-size: 16.5px;
    font-style: italic;
    color: var(--ink-soft);
    max-width: 680px;
    margin: 0 0 20px;
    line-height: 1.6;
    font-family: 'Playfair Display', serif;
  }}
  p {{
    color: var(--ink-soft);
    margin: 0 0 16px;
    line-height: 1.7;
  }}

  /* Stats row */
  .stat-row {{
    display: flex;
    gap: 16px;
    margin: 24px 0 34px;
    flex-wrap: wrap;
  }}
  .card {{
    background: var(--card);
    border: 1px solid var(--rule);
    border-radius: 10px;
    padding: 16px 20px;
    flex: 1;
    min-width: 140px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02);
  }}
  .card .num {{
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
    font-size: 28px;
    color: var(--terracotta);
    line-height: 1.1;
  }}
  .card .lbl {{
    font-size: 11px;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: #8a8368;
    font-weight: 700;
    margin-top: 6px;
  }}

  /* Home challenges table */
  h2.section-title {{
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: 22px;
    margin: 34px 0 14px;
    color: var(--ink);
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13.5px;
    margin: 14px 0 24px;
  }}
  thead th {{
    text-align: left;
    font-size: 10.5px;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: #8a8368;
    font-weight: 700;
    padding: 0 12px 10px;
    border-bottom: 1px solid var(--rule);
    white-space: nowrap;
  }}
  tbody td {{
    padding: 12px 12px;
    border-bottom: 1px solid var(--rule);
    color: var(--ink-soft);
    vertical-align: middle;
  }}
  tbody tr {{
    transition: background 0.12s;
  }}
  tbody tr:hover {{
    background: rgba(193, 80, 31, 0.05);
    cursor: pointer;
  }}
  tbody tr:hover td.ev-name {{
    color: var(--terracotta);
  }}
  .ev-name {{
    color: var(--ink);
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .flagcell {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: var(--terracotta);
    max-width: 250px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}

  /* Writeup page */
  .back-link {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 16px;
    font-size: 12.5px;
    color: var(--terracotta);
    font-weight: 600;
    cursor: pointer;
  }}
  .back-link:hover {{ text-decoration: underline; }}
  .cat-label {{
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #8a8368;
    font-weight: 700;
    margin: 10px 0 6px;
  }}
  h3.writeup-title {{
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: 26px;
    margin: 0 0 14px;
    line-height: 1.3;
    color: var(--ink);
    display: flex;
    align-items: center;
    gap: 10px;
  }}
  .meta-row {{
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
    padding-bottom: 16px;
    margin-bottom: 22px;
    border-bottom: 1px solid var(--rule);
    font-size: 12px;
    font-variant: all-small-caps;
    color: #8a8368;
    letter-spacing: 0.04em;
  }}
  .meta-row b {{
    color: var(--ink);
    font-weight: 600;
    font-variant: normal;
  }}

  /* Description callout */
  .desc-box {{
    background: var(--card);
    border: 1px solid var(--rule);
    border-left: 3px solid var(--terracotta);
    border-radius: 0 8px 8px 0;
    padding: 16px 20px;
    margin: 18px 0 24px;
    color: var(--ink-soft);
    font-size: 14px;
    line-height: 1.65;
  }}
  .desc-box p {{
    margin: 0 0 8px;
    color: var(--ink-soft);
  }}
  .desc-box p:last-child {{ margin-bottom: 0; }}

  /* Writeup body headings and styling */
  .col-main h1 {{
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: 24px;
    margin: 32px 0 12px;
    color: var(--ink);
  }}
  .col-main h2 {{
    font-family: 'Playfair Display', serif;
    font-weight: 700;
    font-size: 21px;
    margin: 30px 0 10px;
    color: var(--ink);
    border-bottom: 1px solid var(--rule);
    padding-bottom: 6px;
  }}
  .col-main h3 {{
    font-weight: 700;
    font-size: 16.5px;
    margin: 22px 0 8px;
    color: var(--ink);
  }}
  .col-main h4 {{
    font-weight: 700;
    font-size: 14.5px;
    margin: 16px 0 6px;
    color: var(--ink);
  }}
  .col-main ul, .col-main ol {{
    color: var(--ink-soft);
    padding-left: 22px;
    margin: 0 0 16px;
  }}
  .col-main li {{
    margin: 4px 0;
    line-height: 1.6;
  }}
  .col-main blockquote {{
    border-left: 3px solid var(--terracotta-soft);
    background: var(--card);
    padding: 12px 18px;
    margin: 16px 0;
    border-radius: 0 6px 6px 0;
    color: var(--ink-soft);
    font-style: italic;
  }}
  .col-main blockquote p {{
    margin: 0 0 8px;
  }}
  .col-main blockquote p:last-child {{ margin-bottom: 0; }}
  
  /* Inline code */
  .col-main code {{
    background: var(--code-bg);
    color: var(--code-text);
    font-size: 12.5px;
    padding: 2px 7px;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
  }}

  /* Code block */
  .code-block {{
    position: relative;
    background: var(--code-bg);
    color: var(--code-text);
    font-family: 'JetBrains Mono', monospace;
    font-size: 12.5px;
    border-radius: 8px;
    padding: 18px 18px 16px;
    margin: 14px 0 22px;
    overflow-x: auto;
    border: 1px solid rgba(255, 255, 255, 0.05);
  }}
  .code-block pre {{
    margin: 0;
    white-space: pre;
    font-family: inherit;
  }}
  .code-block code {{
    background: none;
    color: inherit;
    padding: 0;
    font-size: inherit;
  }}
  .copy-btn {{
    position: absolute;
    top: 10px;
    right: 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    font-weight: 700;
    background: #2a2719;
    color: #cfc7ad;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 5px;
    padding: 4px 9px;
    letter-spacing: 0.05em;
    cursor: pointer;
    transition: all 0.15s;
  }}
  .copy-btn:hover {{
    background: #3a3624;
    color: var(--code-text);
  }}
  .copy-btn.copied {{
    background: var(--green);
    color: #fff;
    border-color: var(--green);
  }}

  /* Flag box */
  .flag-box {{
    display: flex;
    align-items: center;
    gap: 0;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid var(--rule);
    margin-top: 34px;
    background: var(--code-bg);
  }}
  .flag-box .tag {{
    background: var(--terracotta);
    color: #fff;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    padding: 14px 18px;
    letter-spacing: 0.1em;
    flex-shrink: 0;
    text-transform: uppercase;
  }}
  .flag-box .val {{
    flex: 1;
    background: var(--code-bg);
    color: #f0c9a8;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13.5px;
    padding: 14px 18px;
    word-break: break-all;
  }}
  .flag-box .copy-btn {{
    position: static;
    background: var(--cream-2);
    color: var(--ink);
    border: 1px solid var(--rule);
    flex-shrink: 0;
    margin-right: 12px;
    padding: 6px 12px;
  }}
  .flag-box .copy-btn:hover {{
    background: var(--card);
  }}

  /* TOC Column */
  .toc-head {{
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--terracotta);
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
  }}
  .toc-head::before {{
    content: "";
    width: 3px;
    height: 14px;
    background: var(--terracotta);
    display: inline-block;
    border-radius: 2px;
  }}
  .toc-link {{
    display: block;
    padding: 6px 10px;
    margin-left: -10px;
    border-radius: 5px;
    font-size: 12.5px;
    color: var(--ink-soft);
    border-left: 2px solid transparent;
    cursor: pointer;
    line-height: 1.4;
    transition: all 0.12s;
    text-decoration: none;
  }}
  .toc-link:hover {{
    color: var(--ink);
    background: rgba(0,0,0,0.03);
  }}
  .toc-link.active {{
    color: var(--terracotta);
    border-left: 2px solid var(--terracotta);
    background: rgba(193, 80, 31, 0.06);
    font-weight: 600;
  }}

  /* Scrollbars */
  ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
  ::-webkit-scrollbar-thumb {{ background: #c9c1a6; border-radius: 4px; }}
  ::-webkit-scrollbar-track {{ background: transparent; }}

  /* Responsiveness */
  @media (max-width: 980px) {{
    .col-toc {{ display: none; }}
    .sidebar {{ width: 210px; min-width: 210px; }}
    .col-main {{ padding: 26px 20px 60px; }}
    .topbar {{ padding: 12px 20px; }}
  }}
  @media (max-width: 680px) {{
    .sidebar {{ display: none; }}
    h1.page-title {{ font-size: 26px; }}
  }}
</style>
</head>
<body>

<div class="app">
  <!-- Left Sidebar -->
  <aside class="sidebar" id="sidebar">
    <div class="brand" onclick="location.hash='#/'">
      {'<img class="logo-img" src="' + logo_data_uri + '" alt="logo" />' if logo_data_uri else '<div class="logo-fallback">M</div>'}
      <div class="brand-text">
        <span class="site-name">CTF Archive</span>
        <span class="site-sub">Writeups &amp; Solutions</span>
      </div>
    </div>

    <!-- Home Nav -->
    <div class="nav-item" data-route="#/">
      <span class="ic">🏠</span>
      <span class="nav-item-title">Home</span>
    </div>

    <!-- Category Nav sections -->
    <div id="sidebar-categories"></div>
  </aside>

  <!-- Main Area -->
  <div class="main">
    <!-- Topbar -->
    <header class="topbar">
      <div class="search-wrap">
        <span class="search-icon">🔍</span>
        <input type="search" class="search-input" id="search-input" placeholder="Search challenges, events, flags..." autocomplete="off" />
      </div>
      <div class="top-right">
        <span class="pill" id="solved-pill">{flags_captured} / {len(writeups)} Solved</span>
      </div>
    </header>

    <!-- Content Area -->
    <main class="content" id="content"></main>
  </div>
</div>

<script>
const challenges = {challenges_json};

// Sidebar generator
function renderSidebar() {{
  const container = document.getElementById("sidebar-categories");
  container.innerHTML = "";

  // Group by category
  const catMap = {{}};
  challenges.forEach(c => {{
    if (!catMap[c.category]) catMap[c.category] = [];
    catMap[c.category].push(c);
  }});

  const sortedCats = Object.keys(catMap).sort();
  sortedCats.forEach(cat => {{
    const label = document.createElement("div");
    label.className = "nav-label";
    label.textContent = cat;
    container.appendChild(label);

    catMap[cat].forEach(c => {{
      const item = document.createElement("div");
      item.className = "nav-item";
      item.dataset.route = "#/w/" + c.id;
      item.innerHTML = `<span class="ic">${{c.icon}}</span><span class="nav-item-title">${{c.title}}</span>`;
      item.title = `${{c.event}} — ${{c.title}}`;
      container.appendChild(item);
    }});
  }});
}}

// Home page renderer
function renderHome(searchQuery = "") {{
  const q = searchQuery.toLowerCase().trim();
  let list = challenges;
  if (q) {{
    list = challenges.filter(c => 
      c.title.toLowerCase().includes(q) ||
      c.event.toLowerCase().includes(q) ||
      c.category.toLowerCase().includes(q) ||
      c.flag.toLowerCase().includes(q) ||
      c.challenge.toLowerCase().includes(q)
    );
  }}

  const rows = list.map(c => `
    <tr onclick="location.hash='#/w/${{c.id}}'">
      <td class="ev-name"><span class="ic">${{c.icon}}</span>${{c.title}}</td>
      <td>${{c.category}}</td>
      <td>${{c.event}}</td>
      <td>${{c.target || c.difficulty || '—'}}</td>
      <td class="flagcell">${{c.flag || '—'}}</td>
    </tr>
  `).join("");

  const categoriesCount = new Set(challenges.map(c => c.category)).size;
  const eventsCount = new Set(challenges.map(c => c.event)).size;
  const capturedCount = challenges.filter(c => c.flag).length;

  return `
    <div class="col-main">
      <h1 class="page-title">🚩 CTF Archive — Writeups</h1>
      <hr class="divider">
      <p class="lede">A personal collection of verified Capture The Flag writeups — full methodology, working exploit scripts, reverse engineering steps, and root-cause analyses.</p>
      <p>Browse challenges across multiple CTF events by category in the sidebar, or filter by keyword using the search bar above. Click any challenge to open the complete solution writeup.</p>

      <div class="stat-row">
        <div class="card"><div class="num">${{challenges.length}}</div><div class="lbl">Total Writeups</div></div>
        <div class="card"><div class="num">${{categoriesCount}}</div><div class="lbl">Categories</div></div>
        <div class="card"><div class="num">${{capturedCount}}</div><div class="lbl">Flags Captured</div></div>
        <div class="card"><div class="num">${{eventsCount}}</div><div class="lbl">Events</div></div>
      </div>

      <h2 class="section-title">All Challenges (${{list.length}})</h2>
      <table>
        <thead>
          <tr>
            <th>Challenge</th>
            <th>Category</th>
            <th>Event</th>
            <th>Target / Diff</th>
            <th>Flag</th>
          </tr>
        </thead>
        <tbody>
          ${{rows || '<tr><td colspan="5" style="text-align:center;padding:24px;color:var(--ink-soft)">No matching writeups found.</td></tr>'}}
        </tbody>
      </table>
    </div>
  `;
}}

// Writeup page renderer
function renderWriteup(c) {{
  // Extract h2 headings for TOC
  const tempDiv = document.createElement("div");
  tempDiv.innerHTML = c.body_html;
  const h2Elements = Array.from(tempDiv.querySelectorAll("h2"));
  const tocItems = h2Elements.map(h => ({{
    id: h.id || h.textContent.toLowerCase().replace(/[^a-z0-9]+/g, '-'),
    text: h.textContent
  }}));

  const metaItems = [
    `<div>CATEGORY: <b>${{c.category}}</b></div>`,
    `<div>EVENT: <b>${{c.event}}</b></div>`,
    c.target ? `<div>TARGET: <b>${{c.target}}</b></div>` : '',
    c.difficulty ? `<div>DIFFICULTY: <b>${{c.difficulty}}</b></div>` : '',
    c.points ? `<div>POINTS: <b>${{c.points}}</b></div>` : '',
    `<div>STATUS: <b style="color:var(--green)">${{c.flag ? 'Captured' : 'Solved'}}</b></div>`
  ].filter(Boolean).join("");

  const promptBlock = c.prompt ? `
    <div class="desc-box">
      <strong>Challenge Prompt:</strong>
      <p>${{c.prompt}}</p>
    </div>
  ` : "";

  const flagBox = c.flag ? `
    <div class="flag-box">
      <div class="tag">FLAG</div>
      <div class="val">${{c.flag}}</div>
      <button class="copy-btn" data-copy="${{c.flag}}">COPY</button>
    </div>
  ` : "";

  return `
    <div class="col-main">
      <span class="back-link" onclick="location.hash='#/'">← Back to Archive</span>
      <div class="cat-label">${{c.category}} • ${{c.event}}</div>
      <h3 class="writeup-title">${{c.icon}} ${{c.title}}</h3>
      <div class="meta-row">
        ${{metaItems}}
      </div>
      ${{promptBlock}}
      <div class="writeup-body">
        ${{c.body_html}}
      </div>
      ${{flagBox}}
    </div>
    <div class="col-toc">
      <div class="toc-head">On This Page</div>
      ${{tocItems.map(t => `<a class="toc-link" href="#${{t.id}}" onclick="event.preventDefault(); document.getElementById('${{t.id}}')?.scrollIntoView({{behavior:'smooth'}});">${{t.text}}</a>`).join("") || '<span style="font-size:12px;color:var(--ink-soft);font-style:italic">No subheadings</span>'}}
    </div>
  `;
}}

function updateActiveNav() {{
  const hash = location.hash || "#/";
  document.querySelectorAll(".nav-item[data-route]").forEach(n => {{
    n.classList.toggle("active", n.dataset.route === hash);
  }});
}}

function initCopyButtons() {{
  document.querySelectorAll(".copy-btn").forEach(btn => {{
    btn.onclick = () => {{
      let text = btn.dataset.copy;
      if (!text) {{
        const block = btn.closest(".code-block");
        if (block) {{
          const pre = block.querySelector("pre");
          if (pre) text = pre.innerText;
        }}
      }}
      if (text) {{
        navigator.clipboard.writeText(text).then(() => {{
          btn.textContent = "COPIED";
          btn.classList.add("copied");
          setTimeout(() => {{
            btn.textContent = "COPY";
            btn.classList.remove("copied");
          }}, 1200);
        }}).catch(() => {{}});
      }}
    }};
  }});
}}

function initTocScrollSpy() {{
  const headings = Array.from(document.querySelectorAll(".col-main h2"));
  const links = Array.from(document.querySelectorAll(".toc-link"));
  if (!headings.length || !links.length) return;

  const observer = new IntersectionObserver((entries) => {{
    entries.forEach(entry => {{
      if (entry.isIntersecting) {{
        const id = entry.target.id;
        links.forEach(l => {{
          const targetId = l.getAttribute("onclick")?.match(/'([^']+)'/)?.[1];
          l.classList.toggle("active", targetId === id);
        }});
      }}
    }});
  }}, {{ rootMargin: "-10% 0px -75% 0px" }});

  headings.forEach(h => observer.observe(h));
}}

function route() {{
  const hash = location.hash || "#/";
  const content = document.getElementById("content");
  if (hash.startsWith("#/w/")) {{
    const id = hash.replace("#/w/", "");
    const c = challenges.find(item => item.id === id) || challenges[0];
    content.innerHTML = renderWriteup(c);
    document.title = `${{c.title}} — CTF Archive`;
    window.scrollTo(0, 0);
  }} else {{
    const searchVal = document.getElementById("search-input").value;
    content.innerHTML = renderHome(searchVal);
    document.title = "🚩 CTF Archive — Writeups";
  }}
  updateActiveNav();
  initCopyButtons();
  initTocScrollSpy();
}}

// Global Click Delegation for data-route
document.addEventListener("click", (e) => {{
  const item = e.target.closest("[data-route]");
  if (item) {{
    location.hash = item.dataset.route;
  }}
}});

// Search bar input
document.getElementById("search-input").addEventListener("input", (e) => {{
  if (!location.hash || location.hash === "#/") {{
    document.getElementById("content").innerHTML = renderHome(e.target.value);
    initCopyButtons();
  }} else {{
    location.hash = "#/";
    setTimeout(() => {{
      document.getElementById("content").innerHTML = renderHome(e.target.value);
      initCopyButtons();
    }}, 50);
  }}
}});

window.addEventListener("hashchange", route);

// Initialize
renderSidebar();
route();
</script>
</body>
</html>
"""

    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)

    with open(OUT_HTML_BACKUP, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"[+] Successfully generated: {OUT_HTML}")
    print(f"[+] Total writeups parsed: {len(writeups)}")
    print(f"[+] Total events: {len(events)}")
    print(f"[+] Total categories: {len(categories)}")
    print(f"[+] Total flags captured: {flags_captured}")
    print()
    print("Breakdown per Event:")
    for ev in events:
        c_list = [w for w in writeups if w['event'] == ev]
        print(f"  • {ev}: {len(c_list)} writeup(s)")

    print()
    print("Breakdown per Category:")
    for cat in categories:
        c_list = [w for w in writeups if w['category'] == cat]
        print(f"  • {cat}: {len(c_list)} writeup(s)")

    print()
    print(f"Folders with files but no parseable writeup ({len(skipped_folders)}):")
    for s in sorted(skipped_folders):
        print(f"  • {s}")

if __name__ == "__main__":
    generate_site()
