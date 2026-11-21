import json
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles and CI environments
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BLOCKLIST_FILE = Path("pup_blocklist.json")

REQUIRED_KEYS = {
    "schema_version": str,
    "last_updated": str,
    "blocked_publishers": list,
    "blocked_name_patterns": list,
    "blocked_winget_ids": list,
    "high_risk_paths": list,
}

# Critical system/vendor names that must never be accidentally blocked
PROTECTED_ALLOWLIST = {
    "microsoft",
    "windows",
    "google",
    "mozilla",
    "apple",
    "nvidia",
    "amd",
    "intel",
    "python",
    "github",
    "valve",
    "steam",
}

MIN_PATTERN_LENGTH = 4


def fail(message: str) -> None:
    print(f"::error file=pup_blocklist.json::{message}")
    sys.exit(1)


def main() -> None:
    if not BLOCKLIST_FILE.exists():
        fail("pup_blocklist.json is missing from the repository root.")

    # 1. Verify valid UTF-8 JSON syntax
    try:
        raw_text = BLOCKLIST_FILE.read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON syntax at line {exc.lineno}, column {exc.colno}: {exc.msg}")
    except Exception as exc:
        fail(f"Failed to read pup_blocklist.json: {exc}")

    if not isinstance(data, dict):
        fail("Root element of pup_blocklist.json must be a JSON object.")

    # 2. Check for missing or unknown top-level keys
    for key, expected_type in REQUIRED_KEYS.items():
        if key not in data:
            fail(f"Missing required top-level key: '{key}'")
        if not isinstance(data[key], expected_type):
            fail(f"Key '{key}' must be of type {expected_type.__name__}, got {type(data[key]).__name__}.")

    extra_keys = set(data.keys()) - set(REQUIRED_KEYS.keys())
    if extra_keys:
        fail(f"Unknown top-level keys found: {', '.join(sorted(extra_keys))}")

    # 3. Validate each list section
    list_keys = [
        "blocked_publishers",
        "blocked_name_patterns",
        "blocked_winget_ids",
        "high_risk_paths",
    ]

    for key in list_keys:
        seen = set()
        for idx, item in enumerate(data[key]):
            if not isinstance(item, str):
                fail(f"Entry #{idx + 1} in '{key}' must be a string.")

            stripped = item.strip()
            if not stripped:
                fail(f"Entry #{idx + 1} in '{key}' cannot be empty or whitespace-only.")

            if item != stripped:
                fail(f"Entry '{item}' in '{key}' contains leading or trailing whitespace.")

            normalized = stripped.lower()
            if normalized in seen:
                fail(f"Duplicate entry found in '{key}': '{item}'")
            seen.add(normalized)

            # Guard against overly broad or dangerous patterns
            if key in ("blocked_publishers", "blocked_name_patterns"):
                if len(stripped) < MIN_PATTERN_LENGTH:
                    fail(
                        f"Entry '{item}' in '{key}' is too short ({len(stripped)} chars). "
                        f"Minimum length is {MIN_PATTERN_LENGTH} to prevent false positives."
                    )
                if normalized in PROTECTED_ALLOWLIST:
                    fail(f"Entry '{item}' in '{key}' is a protected core vendor/system name.")

            # Validate WinGet ID format (Publisher.Package)
            if key == "blocked_winget_ids":
                if "." not in stripped or " " in stripped:
                    fail(
                        f"Invalid WinGet Package ID '{item}' in '{key}'. "
                        "Expected format: 'Publisher.PackageName' with no spaces."
                    )

            # Validate Windows path format
            if key == "high_risk_paths":
                if not stripped.startswith("\\") or not stripped.endswith("\\"):
                    fail(
                        f"Path '{item}' in '{key}' must start and end with a backslash '\\' "
                        "(e.g., '\\\\appdata\\\\local\\\\temp\\\\')."
                    )

    try:
        print("✅ pup_blocklist.json passed all schema, safety, and duplicate checks!")
    except UnicodeEncodeError:
        print("[OK] pup_blocklist.json passed all schema, safety, and duplicate checks!")


if __name__ == "__main__":
    main()
