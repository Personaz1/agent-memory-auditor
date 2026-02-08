#!/usr/bin/env python3
import argparse, pathlib, json, re, datetime, fnmatch, sys


def normalize_line(line):
    return re.sub(r"\s+", " ", line.strip().lower())


def default_config():
    return {
        "weights": {"duplicate": 2, "stale": 1, "contradiction": 5},
        "ignore_patterns": [],
        "threshold": 80,
    }


def load_config(path):
    p = pathlib.Path(path)
    if not p.exists():
        return default_config()
    cfg = json.loads(p.read_text(encoding="utf-8"))
    d = default_config()
    d.update(cfg)
    if "weights" in cfg and isinstance(cfg["weights"], dict):
        d["weights"].update(cfg["weights"])
    return d


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


def config_check(path):
    p = pathlib.Path(path)
    if not p.exists():
        print("Config check: FAIL")
        print(f"- missing config file: {path}")
        return 1
    try:
        cfg = load_config(path)
    except Exception as e:
        print("Config check: FAIL")
        print(f"- invalid JSON: {e}")
        return 1

    errs = []
    w = cfg.get("weights", {})
    for k in ["duplicate", "stale", "contradiction"]:
        if not isinstance(w.get(k), int):
            errs.append(f"weights.{k} must be integer")
    if not isinstance(cfg.get("ignore_patterns", []), list):
        errs.append("ignore_patterns must be array")
    if not isinstance(cfg.get("threshold", 80), int):
        errs.append("threshold must be integer")

    if errs:
        print("Config check: FAIL")
        for e in errs:
            print(f"- {e}")
        return 1

    print("Config check: OK")
    print(f"- threshold: {cfg.get('threshold',80)}")
    print(f"- weights: {cfg.get('weights')}")
    print(f"- ignore_patterns: {len(cfg.get('ignore_patterns',[]))}")
    return 0


def run_audit(args):
    cfg = load_config(args.config)
    weights = cfg.get("weights", {})
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
        "threshold": cfg.get("threshold", 80),
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
        f"Threshold: **{cfg.get('threshold',80)}**",
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

    threshold = cfg.get("threshold", 80)
    if args.strict and score < threshold:
        print(f"STRICT FAIL: score {score} < threshold {threshold}")
        return 3
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=False)

    runp = sub.add_parser("run")
    runp.add_argument("--dir", default="memory")
    runp.add_argument("--out", default="report.md")
    runp.add_argument("--json", default="report.json")
    runp.add_argument("--config", default="audit.config.json")
    runp.add_argument("--include-memory-md", action="store_true", default=True)
    runp.add_argument("--strict", action="store_true")

    cc = sub.add_parser("config-check")
    cc.add_argument("--config", default="audit.config.json")

    args = ap.parse_args()

    # backward compatible: no subcommand => run
    if args.cmd is None:
        class A: pass
        a = A()
        a.dir = "memory"; a.out = "report.md"; a.json = "report.json"; a.config = "audit.config.json"; a.include_memory_md = True; a.strict = False
        raise SystemExit(run_audit(a))

    if args.cmd == "config-check":
        raise SystemExit(config_check(args.config))
    if args.cmd == "run":
        raise SystemExit(run_audit(args))


if __name__ == "__main__":
    main()
