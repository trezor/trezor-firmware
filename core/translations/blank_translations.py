"""Blank translation values based on layout-specific rules.

Processes locale JSON files (e.g., en_Bolt.json) and blanks translation keys
that should not appear on certain hardware layouts, as defined by a rules config.

Usage:
    python blank_translations.py --config rules.json --locales-dir ./locales
    python blank_translations.py --config rules.json --locales-dir ./locales --dry-run
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import click


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def infer_layout(file_path: Path) -> str:
    # Expect pattern <lang>_<Layout>.json
    stem = file_path.stem  # en_Bolt
    parts = stem.split("_", 1)
    if len(parts) != 2:
        raise ValueError(f"Cannot infer layout from filename: {file_path.name}")
    return parts[1]


def compile_rules(raw_rules: List[Dict[str, Any]]):
    compiled = []
    for r in raw_rules:
        kinds = [k for k in ("exact", "prefix", "regex") if k in r]
        if len(kinds) != 1:
            raise ValueError(f"Rule must have exactly one of exact/prefix/regex: {r}")
        matcher_type = kinds[0]
        raw_pattern = r[matcher_type]

        pattern = None
        patterns = None  # used for exact list-of-keys
        regex = None

        if matcher_type == "regex":
            if not isinstance(raw_pattern, str):
                raise ValueError(f"Regex pattern must be a string: {r}")
            regex = re.compile(raw_pattern)
            pattern = raw_pattern
        elif matcher_type == "prefix":
            if not isinstance(raw_pattern, str):
                raise ValueError(f"Prefix must be a string: {r}")
            pattern = raw_pattern
        elif matcher_type == "exact":
            if isinstance(raw_pattern, list):
                if not raw_pattern:
                    raise ValueError("Exact list cannot be empty.")
                if not all(isinstance(x, str) for x in raw_pattern):
                    raise ValueError("Exact list must contain only strings.")
                patterns = set(raw_pattern)
            elif isinstance(raw_pattern, str):
                pattern = raw_pattern
            else:
                raise ValueError("Exact must be a string or a list of strings.")

        compiled.append(
            {
                "type": matcher_type,
                "pattern": pattern,  # string for exact/prefix/regex, None for exact-list
                "patterns": patterns,  # set for exact-list, else None
                "regex": regex,  # compiled for regex, else None
                "allowed": set(r.get("allowedLayouts", [])),
                "denied": set(r.get("denyLayouts", [])),
                "ignore": set(r.get("ignoreLayouts", [])),
                "stop": r.get("stopAfterMatch", True),
                "description": r.get("description", ""),
            }
        )
    return compiled


def match_rule(key: str, rules):
    matches = []
    for rule in rules:
        t = rule["type"]
        matched = False
        if t == "exact":
            if rule.get("patterns") is not None:
                matched = key in rule["patterns"]
            else:
                matched = key == rule["pattern"]
        elif t == "prefix":
            matched = key.startswith(rule["pattern"])
        elif t == "regex":
            matched = bool(rule["regex"].search(key))

        if matched:
            matches.append(rule)
            if rule["stop"]:
                break
    return matches


def process_file(file_path: Path, rules, dry_run: bool = False):
    data = load_json(file_path)
    if "translations" not in data or not isinstance(data["translations"], dict):
        raise ValueError(f"No 'translations' object in {file_path}")
    translations = data["translations"]
    layout = infer_layout(file_path)

    if not translations:
        return {
            "file": file_path.name,
            "layout": layout,
            "changed": 0,
            "total": 0,
            "blanked": [],
        }

    changed = 0
    total = len(translations)
    blanked_keys: List[str] = []
    for key, value in list(translations.items()):
        if not isinstance(value, str):
            continue
        matches = match_rule(key, rules)
        if not matches:
            continue
        rule = matches[0]
        if layout in rule["ignore"]:
            continue
        allowed = rule["allowed"]
        denied = rule["denied"]
        blank = False
        if allowed and layout not in allowed:
            blank = True
        elif denied and layout in denied:
            blank = True
        if blank and value != "":
            changed += 1
            blanked_keys.append(key)
            if not dry_run:
                translations[key] = ""
    if not dry_run:
        save_json(file_path, data)
    return {
        "file": file_path.name,
        "layout": layout,
        "changed": changed,
        "total": total,
        "blanked": blanked_keys,
    }


def write_blanked_file(out_dir: Path, original_filename: str, blanked_keys: List[str]):
    if not blanked_keys:
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / original_filename
    payload = {"translations": {k: "" for k in blanked_keys}}
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def run_cleanup(
    config_path: Path,
    locales_dir: Path,
    *,
    lang: str = "en",
    dry_run: Optional[bool] = None,
    only: Optional[List[str]] = None,
    blanked_out_dir: Optional[Path] = None,
):
    """
    Execute cleanup using rules. Returns a dict with a summary and counts.
    Does not print or exit; raises exceptions on fatal errors.
    """
    config = load_json(config_path)
    if not isinstance(config, list):
        raise ValueError("Config file must contain a list of rules.")
    rules = compile_rules(config)
    effective_dry = bool(dry_run)

    if not locales_dir.is_dir():
        raise FileNotFoundError(f"Locales directory not found: {locales_dir}")

    lang = lang.lower()
    files = sorted(locales_dir.glob(f"{lang}_*.json"))
    if not files:
        raise FileNotFoundError("No locale files found.")

    if blanked_out_dir:
        blanked_out_dir.mkdir(parents=True, exist_ok=True)

    summary = []
    total_blanked_keys = 0

    for f in files:
        layout = infer_layout(f)
        if only and layout not in set(only):
            continue
        result = process_file(f, rules, dry_run=effective_dry)
        summary.append(result)
        total_blanked_keys += len(result["blanked"])
        if blanked_out_dir and result["blanked"]:
            write_blanked_file(blanked_out_dir, result["file"], result["blanked"])

    return {
        "summary": summary,
        "total_blanked_keys": total_blanked_keys,
        "dry_run": effective_dry,
        "blanked_out_dir": str(blanked_out_dir) if blanked_out_dir else None,
    }


@click.command(name="cleanup-translations")
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to layout_rules.json",
)
@click.option(
    "--locales-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory containing locale JSON files",
)
@click.option(
    "--lang", default="en", show_default=True, help="Language code to process"
)
@click.option(
    "--dry-run", is_flag=True, help="Do not write changes to original locale files"
)
@click.option(
    "--only",
    multiple=True,
    help="Limit to specific layouts (repeatable, e.g. --only Bolt --only Caesar)",
)
@click.option(
    "--blanked-out-dir",
    type=click.Path(file_okay=False, path_type=Path),
    help="Directory to write JSON files containing only blanked keys (for Crowdin)",
)
def click_cleanup(
    config_path: Path,
    locales_dir: Path,
    lang: str,
    dry_run: bool,
    only: tuple[str, ...],
    blanked_out_dir: Optional[Path],
):
    """
    Standalone CLI entrypoint using click. Also usable programmatically via run_cleanup().
    """
    try:
        result = run_cleanup(
            config_path=config_path,
            locales_dir=locales_dir,
            lang=lang,
            dry_run=dry_run,
            only=list(only) if only else None,
            blanked_out_dir=blanked_out_dir,
        )
    except Exception as e:
        raise click.ClickException(str(e)) from e

    for r in result["summary"]:
        click.echo(
            f"[{r['layout']}] {r['file']}: blanked {r['changed']} of {r['total']}"
        )
    click.echo("Done.")
    if result["dry_run"]:
        click.echo("Dry run: no original files modified.")
    if result["blanked_out_dir"] is not None:
        click.echo(
            f"Total blanked keys exported: {result['total_blanked_keys']} -> {result['blanked_out_dir']}"
        )


if __name__ == "__main__":
    click_cleanup()
