#!/usr/bin/env python3
"""
Secondary lint check for Projects/field-manual.

IMPORTANT:
This script only checks for common literal patterns (private IP ranges, local
user paths, non-noreply email addresses, crypto addresses/invoices/keys, PEM
keys, tokens, and domains), plus any custom terms stored in an untracked
`.local-blocklist.txt` file (one term per line) so the blocklist itself never
leaks private identifiers into the repo.

Passing this script does NOT guarantee a file is free of private context or
safe to publish. Always perform a full human review of filenames, prose
content, and git history before pushing to any remote.
"""

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_BLOCKLIST_PATH = os.path.join(ROOT, ".local-blocklist.txt")

PATTERNS = [
    ("RFC1918 10.x.x.x IP", re.compile(r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")),
    ("RFC1918 192.168.x.x IP", re.compile(r"\b192\.168\.\d{1,3}\.\d{1,3}\b")),
    ("RFC1918 172.16-31.x.x IP", re.compile(r"\b172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}\b")),
    ("Tailscale/CGNAT 100.x.x.x IP", re.compile(r"\b100\.(?:6[4-9]|[7-9]\d|1[0-1]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b")),
    ("Windows Users\\<name> path", re.compile(r"(?i)(?<![A-Za-z0-9_.-])[a-z]:[\\/]+users[\\/]+(?!public|default)[a-z0-9_.-]+")),
    ("macOS /Users/<name> path", re.compile(r"(?i)(?<![A-Za-z0-9_.-])/[Uu]sers/(?!shared|guest|example)[a-z0-9_.-]+")),
    ("Unix /home/<name> path", re.compile(r"(?<![A-Za-z0-9_.-])/home/(?!user|example)[a-z0-9_.-]+")),
    ("Desktop hostname DESKTOP-*", re.compile(r"\bDESKTOP-[A-Z0-9]+\b")),
    ("Tailscale MagicDNS domain", re.compile(r"\b[a-z0-9-]+\.ts\.net\b")),
    ("Tor Onion address", re.compile(r"\b[a-z2-7]{16,56}\.onion\b")),
    ("PEM/PGP private key block", re.compile(r"-----BEGIN (?:[A-Z0-9_-]+ )?PRIVATE KEY(?: BLOCK)?-----")),
    (
        "Email address (non-noreply)",
        re.compile(r"\b[A-Za-z0-9._%+-]+@(?!users\.noreply\.github\.com\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
    ("Long hex string (40+ chars, check if address/tx/key)", re.compile(r"\b0x[a-fA-F0-9]{40,}\b")),
    ("Bitcoin Extended Public Key (xpub/ypub/zpub)", re.compile(r"\b(?:[xyzt]pub[1-9A-HJ-NP-Za-km-z]{95,115})\b")),
    ("Bitcoin Bech32 address (bc1/tb1)", re.compile(r"\b(?:bc1|tb1)[0-9ac-hj-np-z]{25,65}\b")),
    ("Lightning invoice (lnbc/lntb/lnbcrt)", re.compile(r"\b(?:lnbc|lntb|lnbcrt)[0-9a-zA-Z]{15,}\b")),
    ("Google API key (AIza)", re.compile(r"\bAIza[0-9A-Za-z-_]{30,45}\b")),
    ("JSON Web Token (JWT)", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    (
        "Secret token prefix (OpenAI, Anthropic, GitHub, Slack, AWS)",
        re.compile(
            r"\b(?:sk-[A-Za-z0-9]{16,}|sk-ant-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{40,}|gho_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]+|AKIA[0-9A-Z]{16})\b"
        ),
    ),
]

if os.path.isfile(LOCAL_BLOCKLIST_PATH):
    with open(LOCAL_BLOCKLIST_PATH, "r", encoding="utf-8", errors="replace") as bf:
        terms = [re.escape(line.strip()) for line in bf if line.strip() and not line.startswith("#")]
    if terms:
        PATTERNS.append(("Local blocklist term", re.compile(r"(?i)\b(?:" + "|".join(terms) + r")\b")))


def scan_text(source_label: str, text: str) -> list[str]:
    findings = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for label, regex in PATTERNS:
            for match in regex.finditer(line):
                findings.append(f"{source_label}:{line_no}: [{label}] -> {match.group(0)!r}")
    return findings


def main() -> int:
    findings: list[str] = []

    for dirpath, dirnames, filenames in os.walk(ROOT):
        for skip in (".git", "__pycache__", ".venv"):
            if skip in dirnames:
                dirnames.remove(skip)
        for fn in filenames:
            full_path = os.path.join(dirpath, fn)
            rel_path = os.path.relpath(full_path, ROOT).replace("\\", "/")
            if rel_path == ".local-blocklist.txt":
                continue
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                findings.extend(scan_text(rel_path, content))
            except Exception as exc:
                findings.append(f"{rel_path}:0: [Read Error] {exc}")

    git_dir = os.path.join(ROOT, ".git")
    if os.path.isdir(git_dir):
        try:
            proc = subprocess.run(
                [
                    "git",
                    "-C",
                    ROOT,
                    "log",
                    "--all",
                    "-p",
                    "--format=commit %H %an <%ae> %s",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if proc.returncode == 0:
                if proc.stdout:
                    findings.extend(scan_text("git-history", proc.stdout))
            else:
                print(f"Error: Git history scan failed with exit code {proc.returncode}:\n{proc.stderr}", file=sys.stderr)
                return 2
        except FileNotFoundError:
            print("Error: 'git' command not found in PATH. Install git to verify commit history.", file=sys.stderr)
            return 2
    else:
        print("Error: No .git directory found. Git commit history must be scanned before release.", file=sys.stderr)
        return 2

    if findings:
        print("Potential sensitive patterns detected (review manually):")
        for item in findings:
            print("  -", item)
        return 1

    print("OK: No literal regex matches found in tracked files or git history.")
    print("Reminder: Regex checks cannot detect contextual or prose leaks. Review all files manually.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
