#!/usr/bin/env python3
"""
Generates llms.txt and llms-full.txt for Projects/field-manual.

Spec reference: https://llmstxt.org/
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES_DIR = os.path.join(ROOT, "notes")


def get_title(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("# "):
                return line.strip("# \r\n")
    return os.path.splitext(os.path.basename(file_path))[0]


def build_llms_txt() -> str:
    lines = [
        "# Field Manual",
        "",
        "> A curated collection of technical field notes drawn from real debugging, systems administration, and software engineering sessions.",
        "",
        "## Published Notes",
        "",
    ]

    notes = sorted([f for f in os.listdir(NOTES_DIR) if f.endswith(".md")])
    for note in notes:
        full_path = os.path.join(NOTES_DIR, note)
        title = get_title(full_path)
        lines.append(f"- [{title}](notes/{note})")

    lines.append("")
    lines.append("## Full Text Ingestion")
    lines.append("")
    lines.append("- [Complete Field Manual (Single File)](llms-full.txt): Complete concatenated text of all notes.")
    lines.append("")

    return "\n".join(lines)


def build_llms_full_txt() -> str:
    sections = [
        "# Field Manual — Complete Collection\n\n> All published notes and technical field guides in a single consolidated document for LLM ingestion and offline reference."
    ]

    # Add README
    readme_path = os.path.join(ROOT, "README.md")
    if os.path.isfile(readme_path):
        with open(readme_path, "r", encoding="utf-8", errors="replace") as f:
            sections.append(f.read().strip())

    # Add published notes
    notes = sorted([f for f in os.listdir(NOTES_DIR) if f.endswith(".md")])
    for note in notes:
        full_path = os.path.join(NOTES_DIR, note)
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            sections.append(f.read().strip())

    return "\n\n---\n\n".join(sections) + "\n"


def main():
    llms_path = os.path.join(ROOT, "llms.txt")
    llms_full_path = os.path.join(ROOT, "llms-full.txt")

    llms_content = build_llms_txt()
    with open(llms_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(llms_content)
    print(f"Wrote: {llms_path}")

    llms_full_content = build_llms_full_txt()
    with open(llms_full_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(llms_full_content)
    print(f"Wrote: {llms_full_path}")


if __name__ == "__main__":
    main()
