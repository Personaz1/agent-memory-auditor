#!/usr/bin/env python3
import argparse, pathlib, json, re, datetime


def read_files(root):
    items = []
    for p in sorted(pathlib.Path(root).glob("*.md")):
        try:
            txt = p.read_text(encoding="utf-8")
        except Exception:
            txt = ""
        items.append((p.name, txt))
    return items


def normalize_line(line):
    return re.sub(r"\s+", " ", line.strip().lower())


def scan(files):
    line_index = {}
    duplicates = []
    stale = []
    contradictions = []

    for fn, txt in files:
        for i, raw in enumerate(txt.splitlines(), 1):
            line = normalize_line(raw)
            if len(line) < 15:
                continue
            if line in line_index:
                duplicates.append({"line": line, "first": line_index[line], "second": f"{fn}:{i}"})
            else:
                line_index[line] = f"{fn}:{i}"

            if any(k in line for k in ["todo", "later", "tbd", "fixme"]):
                stale.append({"file": fn, "line": i, "text": raw.strip()})

    # crude contradiction hints: 'always' vs 'never' on similar tokens
    for fn, txt in files:
        lines = [normalize_line(x) for x in txt.splitlines() if len(normalize_line(x)) > 15]
        has_always = [l for l in lines if "always" in l]
        has_never = [l for l in lines if "never" in l]
        if has_always and has_never:
            contradictions.append({"file": fn, "hint": "contains both 'always' and 'never' statements"})

    return duplicates, stale, contradictions


def score(dups, stale, contra):
    s = 100 - (len(dups) * 2 + len(stale) * 1 + len(contra) * 5)
    return max(0, s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="memory")
    ap.add_argument("--out", default="report.md")
    ap.add_argument("--json", default="report.json")
    args = ap.parse_args()

    files = read_files(args.dir)
    dups, stale, contra = scan(files)
    s = score(dups, stale, contra)

    data = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "files": [f for f, _ in files],
        "score": s,
        "duplicates": dups,
        "stale_candidates": stale,
        "contradiction_hints": contra,
    }

    pathlib.Path(args.json).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Memory Audit Report",
        "",
        f"Score: **{s}/100**",
        "",
        "## Duplicates",
        *( [f"- {x['line'][:80]}... ({x['first']} vs {x['second']})" for x in dups] or ["- none"] ),
        "",
        "## Stale candidates",
        *( [f"- {x['file']}:{x['line']} — {x['text']}" for x in stale] or ["- none"] ),
        "",
        "## Contradiction hints",
        *( [f"- {x['file']}: {x['hint']}" for x in contra] or ["- none"] ),
    ]
    pathlib.Path(args.out).write_text("\n".join(md), encoding="utf-8")
    print(f"Saved: {args.out}, {args.json}")


if __name__ == "__main__":
    main()
