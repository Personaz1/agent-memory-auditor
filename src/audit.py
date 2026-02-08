#!/usr/bin/env python3
import argparse, pathlib, json, re, datetime, fnmatch


def normalize_line(line):
    return re.sub(r"\s+", " ", line.strip().lower())


def load_config(path):
    p = pathlib.Path(path)
    if not p.exists():
        return {
            "weights": {"duplicate": 2, "stale": 1, "contradiction": 5},
            "ignore_patterns": []
        }
    return json.loads(p.read_text(encoding="utf-8"))


def should_ignore(path, patterns):
    return any(fnmatch.fnmatch(path, pat) for pat in patterns)


def collect_files(memory_dir, include_memory_md=True, ignore_patterns=None):
    ignore_patterns = ignore_patterns or []
    out = []
    root = pathlib.Path(memory_dir)
    if root.exists():
        for p in sorted(root.rglob("*.md")):
            rel = str(p)
            if should_ignore(rel, ignore_patterns):
                continue
            out.append(p)
    if include_memory_md:
        m = pathlib.Path("MEMORY.md")
        if m.exists() and not should_ignore(str(m), ignore_patterns):
            out.append(m)
    return out


def read_files(paths):
    items = []
    for p in paths:
        try:
            txt = p.read_text(encoding="utf-8")
        except Exception:
            txt = ""
        items.append((str(p), txt))
    return items


def scan(files):
    line_index = {}
    duplicates, stale, contradictions = [], [], []

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

    for fn, txt in files:
        lines = [normalize_line(x) for x in txt.splitlines() if len(normalize_line(x)) > 15]
        has_always = any("always" in l for l in lines)
        has_never = any("never" in l for l in lines)
        if has_always and has_never:
            contradictions.append({"file": fn, "hint": "contains both 'always' and 'never' statements"})

    return duplicates, stale, contradictions


def calc_score(dups, stale, contra, weights):
    s = 100 - (len(dups) * weights.get("duplicate", 2) + len(stale) * weights.get("stale", 1) + len(contra) * weights.get("contradiction", 5))
    return max(0, s)


def remediation(dups, stale, contra):
    rec = []
    if dups:
        rec.append("Merge or delete duplicate lines; keep one canonical statement per fact.")
    if stale:
        rec.append("Resolve TODO/TBD/FIXME entries or move them to task tracking.")
    if contra:
        rec.append("Review always/never absolute statements and replace with scoped conditions.")
    if not rec:
        rec.append("No immediate remediation needed. Maintain current hygiene.")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="memory")
    ap.add_argument("--out", default="report.md")
    ap.add_argument("--json", default="report.json")
    ap.add_argument("--config", default="audit.config.json")
    ap.add_argument("--include-memory-md", action="store_true", default=True)
    args = ap.parse_args()

    cfg = load_config(args.config)
    weights = cfg.get("weights", {"duplicate": 2, "stale": 1, "contradiction": 5})
    ignore_patterns = cfg.get("ignore_patterns", [])

    paths = collect_files(args.dir, include_memory_md=args.include_memory_md, ignore_patterns=ignore_patterns)
    files = read_files(paths)
    dups, stale, contra = scan(files)
    score = calc_score(dups, stale, contra, weights)
    rec = remediation(dups, stale, contra)

    data = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scanned_files": [f for f, _ in files],
        "score": score,
        "weights": weights,
        "duplicates": dups,
        "stale_candidates": stale,
        "contradiction_hints": contra,
        "remediation": rec,
    }
    pathlib.Path(args.json).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Memory Audit Report",
        "",
        f"Score: **{score}/100**",
        "",
        "## Remediation suggestions",
        *[f"- {x}" for x in rec],
        "",
        "## Duplicates",
        *( [f"- {x['line'][:90]}... ({x['first']} vs {x['second']})" for x in dups] or ["- none"] ),
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
