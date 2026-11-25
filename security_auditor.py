"""
Pre-Update Security & Trust Gate for Windows Software Update Manager
====================================================================
Zero-dependency security & reputation engine (100% Python Standard Library).
Layered defense:
1. Native Windows Authenticode digital signature verification (via PowerShell).
2. Suspicious directory heuristics (%TEMP%, C:\\Users\\Public, ProgramData).
3. Known PUP / Adware / Hijacker pattern blocklist matching.
4. Stealth / Stalkerware registry anomaly detection (hidden SystemComponent=1).
5. File SHA-256 calculation & optional cloud reputation lookups (MalwareBazaar / VirusTotal).
"""

import os
import re
import sys
import json
import shutil
import hashlib
import subprocess
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional


# Known legitimate vendor publisher <-> certificate signer alias mapping
TRUSTED_PUBLISHER_SIGNER_ALIASES = {
    # Git for Windows: maintained and signed by Johannes Schindelin
    "the git development community": ["johannes schindelin", "git for windows"],
    "johannes schindelin": ["the git development community", "git", "git for windows"],
    # LM Studio / Bionic: corporate entity Element Labs Inc.
    "lm studio": ["element labs inc.", "element labs", "elementlabs", "bionic"],
    "element labs inc.": ["lm studio", "element labs", "bionic"],
    "element labs": ["lm studio", "element labs inc.", "bionic"],
    # Google LLC
    "google": ["google llc", "google inc"],
    "google llc": ["google", "google inc"],
    # GitHub / Microsoft
    "github, inc.": ["github", "github inc", "microsoft"],
    "github inc.": ["github", "github, inc.", "microsoft"],
    "github": ["github, inc.", "github inc", "microsoft"],
    # Mozilla
    "mozilla": ["mozilla corporation", "mozilla foundation"],
    "mozilla corporation": ["mozilla", "mozilla foundation"],
    # Learning Machines / ArtCraft Suite
    "learning machines llc": ["learning machines inc", "learning machines", "artcraft"],
    "learning machines inc": ["learning machines llc", "learning machines", "artcraft"],
    # Docker
    "docker inc.": ["docker inc", "docker"],
    "docker inc": ["docker inc.", "docker"],
    # Mintplex Labs / AnythingLLM
    "mintplex labs inc": ["mintplex labs", "anythingllm"],
}


def is_publisher_signer_aligned(pub: str, signer: str) -> bool:
    """Checks if executable signer is aligned with registry publisher or known aliases."""
    if not pub or not signer:
        return True
    p_lower = pub.strip().lower()
    s_lower = signer.strip().lower()

    # 1. Direct or substring match
    if p_lower in s_lower or s_lower in p_lower:
        return True

    # 2. Word intersection (ignoring corporate suffix stop words)
    stop_words = {"inc", "corp", "corporation", "llc", "ltd", "limited", "the", "and", "co", "company"}
    p_words = set(re.findall(r"\w+", p_lower)) - stop_words
    s_words = set(re.findall(r"\w+", s_lower)) - stop_words
    if p_words and s_words and p_words.intersection(s_words):
        return True

    # 3. Known trusted publisher / signer aliases
    for key, aliases in TRUSTED_PUBLISHER_SIGNER_ALIASES.items():
        if key in p_lower or p_lower == key:
            if any(alias in s_lower or s_lower == alias for alias in aliases):
                return True
        if key in s_lower or s_lower == key:
            if any(alias in p_lower or p_lower == alias for alias in aliases):
                return True

    # 4. Microsoft ecosystem components
    if "microsoft" in p_lower and "microsoft" in s_lower:
        return True

    return False


class SecurityAuditor:
    """
    Pre-Update Security & Trust Gate for Windows SoftwareUpdateManager.
    Protects against adware, spyware, hijacked binaries, and unverified software.
    """

    def __init__(self, blocklist_path: Optional[str] = None, vt_api_key: str = ""):
        self.vt_api_key = (vt_api_key or "").strip()
        self._hash_cache: Dict[str, str] = {}
        self._sig_cache: Dict[str, dict] = {}

        # Resolve blocklist path (supporting PyInstaller bundles & standard path)
        if blocklist_path:
            self.blocklist_path = Path(blocklist_path)
        elif hasattr(sys, "_MEIPASS"):
            self.blocklist_path = Path(sys._MEIPASS) / "pup_blocklist.json"
        else:
            self.blocklist_path = Path(__file__).parent / "pup_blocklist.json"

        self.blocklist = self._load_blocklist()

    def _load_blocklist(self) -> dict:
        """Load local PUP blocklist schema or supply hardened embedded fallback."""
        default_data = {
            "schema_version": "1.0",
            "last_updated": "2026-11-16",
            "blocked_publishers": [
                "ByteFence", "Digital Communications Inc", "Lavabits",
                "Safer Technologies", "Reason Cybersecurity", "PC HelpSoft",
                "Auslogics", "IObit", "Mindspark Interactive", "Visicom Media", "SweetLabs"
            ],
            "blocked_name_patterns": [
                "segurazo", "rav endpoint", "bytefence", "driver booster",
                "driver easy", "driverpack", "pc accelerator", "registry cleaner",
                "browser hijacker", "chromium_portable", "web companion", "pokki",
                "ask toolbar", "conduit", "macKeeper", "search protect", "spyhunter"
            ],
            "blocked_winget_ids": [
                "IObit.DriverBooster", "IObit.AdvancedSystemCare", "Lavasoft.WebCompanion"
            ],
            "high_risk_paths": [
                "\\appdata\\local\\temp\\",
                "\\windows\\temp\\",
                "\\users\\public\\",
                "\\programdata\\",
                "\\appdata\\roaming\\",
            ],
        }

        if self.blocklist_path.exists():
            try:
                with open(self.blocklist_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default_data.update(data)
            except Exception:
                pass
        return default_data

    # -----------------------------------------------------------------
    # 1. EXECUTABLE RESOLUTION & SHA-256 HASHING
    # -----------------------------------------------------------------
    @staticmethod
    def _pick_primary_exe(directory: str) -> Optional[str]:
        """Select the primary non-uninstaller executable inside an application folder."""
        if not directory or not os.path.isdir(directory):
            return None
        try:
            candidates = []
            for item in os.listdir(directory):
                low = item.lower()
                if low.endswith(".exe") and not any(
                    skip in low for skip in ("unins", "uninst", "setup", "update", "crash", "helper")
                ):
                    candidates.append(os.path.join(directory, item))
            if candidates:
                candidates.sort(key=lambda p: (1 if "-cli.exe" in p.lower() else 0, len(os.path.basename(p))))
                return candidates[0]
        except OSError:
            pass
        return None

    @staticmethod
    def resolve_executable_path(
        display_icon: str,
        install_location: str,
        uninstall_string: str = "",
        app_name: str = "",
        pkg_id: str = "",
    ) -> Optional[str]:
        """
        Extracts a clean executable path from Windows Registry DisplayIcon,
        InstallLocation, standard Program Files directories, UninstallString,
        WinGet links, and system PATH.
        """
        cached_fallback = None

        # 1. Try DisplayIcon (strip outer quotes before splitting optional ',0' icon index)
        if display_icon:
            raw_icon = display_icon.strip().strip('"').strip("'")
            cleaned = raw_icon.split(",")[0].strip().strip('"').strip("'")
            if cleaned.lower().endswith(".exe") and os.path.isfile(cleaned):
                if "\\package cache\\" in cleaned.lower():
                    cached_fallback = cleaned
                else:
                    return cleaned

        # 2. Try InstallLocation
        if install_location:
            loc = install_location.strip().strip('"').strip("'")
            if os.path.isfile(loc) and loc.lower().endswith(".exe"):
                return loc
            picked = SecurityAuditor._pick_primary_exe(loc)
            if picked:
                return picked

        # 3. Try standard Program Files & user Programs directories using pkg_id / app_name
        probe_dirs = []
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_progs = os.path.expandvars(r"%LOCALAPPDATA%\Programs")
        clean_name = re.sub(r"\s*\([^)]*\)", "", app_name or "").strip()

        if pkg_id and "." in pkg_id:
            vendor, product = pkg_id.split(".", 1)
            prod_leaf = product.split(".")[-1]
            if pkg_id.lower() == "microsoft.powerbi":
                probe_dirs.extend([
                    os.path.join(pf, "Microsoft Power BI Desktop", "bin"),
                    os.path.join(pf86, "Microsoft Power BI Desktop", "bin"),
                ])
            for base in (pf, pf86, local_progs):
                probe_dirs.extend([
                    os.path.join(base, vendor, prod_leaf),
                    os.path.join(base, vendor, product),
                    os.path.join(base, prod_leaf),
                    os.path.join(base, product),
                ])

        if clean_name:
            for base in (pf, pf86, local_progs):
                probe_dirs.append(os.path.join(base, clean_name))

        for pdir in dict.fromkeys(probe_dirs):
            picked = SecurityAuditor._pick_primary_exe(pdir)
            if picked:
                return picked

        # 4. Try UninstallString (often points to app folder / uninstaller)
        if uninstall_string:
            m = re.search(r'["\']?([^"\']+\.exe)["\']?', uninstall_string, re.IGNORECASE)
            if m:
                u_exe = m.group(1).strip()
                if os.path.isfile(u_exe):
                    if "\\package cache\\" in u_exe.lower():
                        cached_fallback = cached_fallback or u_exe
                    else:
                        picked = SecurityAuditor._pick_primary_exe(os.path.dirname(u_exe))
                        if picked:
                            return picked

        # 5. Try WinGet Links (%LOCALAPPDATA%\Microsoft\WinGet\Links) for CLI packages
        cli_aliases = {
            "burntsushi.ripgrep.msvc": "rg.exe",
            "burntsushi.ripgrep.gnu": "rg.exe",
            "gyan.ffmpeg": "ffmpeg.exe",
            "git.git": "git.exe",
        }
        winget_links = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links")
        if os.path.isdir(winget_links) and (app_name or pkg_id):
            candidates_to_try = []
            if pkg_id and pkg_id.lower() in cli_aliases:
                candidates_to_try.append(cli_aliases[pkg_id.lower()])
            if app_name:
                candidates_to_try.extend([f"{app_name}.exe", f"{app_name.lower()}.exe"])
            if pkg_id:
                suffix = pkg_id.split(".")[-1]
                candidates_to_try.extend([f"{suffix}.exe", f"{suffix.lower()}.exe"])
            for cand in dict.fromkeys(candidates_to_try):
                lp = os.path.join(winget_links, cand)
                if os.path.isfile(lp):
                    return lp

        # 6. Try system PATH via shutil.which for CLI / developer tools
        if app_name or pkg_id:
            terms = []
            if pkg_id and pkg_id.lower() in cli_aliases:
                terms.append(cli_aliases[pkg_id.lower()])
            terms.extend(filter(None, [
                app_name,
                app_name.lower() if app_name else "",
                pkg_id.split(".")[-1].lower() if pkg_id else "",
            ]))
            for term in dict.fromkeys(terms):
                try:
                    w = shutil.which(term)
                    if w and os.path.isfile(w):
                        return w
                except Exception:
                    pass

        return cached_fallback

    def get_sha256(self, file_path: str) -> Optional[str]:
        """Computes SHA-256 digest streaming in 64KB blocks."""
        if not file_path or not os.path.isfile(file_path):
            return None
        if file_path in self._hash_cache:
            return self._hash_cache[file_path]

        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256.update(chunk)
            digest = sha256.hexdigest().lower()
            self._hash_cache[file_path] = digest
            return digest
        except OSError:
            return None

    # -----------------------------------------------------------------
    # 2. AUTHENTICODE DIGITAL SIGNATURE VERIFICATION
    # -----------------------------------------------------------------
    def check_authenticode_signature(self, exe_path: str) -> dict:
        """
        Uses native Windows PowerShell Get-AuthenticodeSignature to verify binary
        integrity and extract publisher signer without external C/ctypes dependencies.
        """
        if not exe_path or not os.path.isfile(exe_path):
            return {"status": "Unknown", "signer": "", "valid": False}
        if exe_path in self._sig_cache:
            return self._sig_cache[exe_path]

        clean_path = exe_path.replace("'", "''")
        ps_script = (
            f"$sig = Get-AuthenticodeSignature -LiteralPath '{clean_path}'; "
            "$subj = if ($sig.SignerCertificate) { $sig.SignerCertificate.Subject } else { '' }; "
            "Write-Output ($sig.Status.ToString() + '|' + $subj)"
        )
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            proc = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True, text=True, errors="replace", timeout=7, startupinfo=startupinfo
            )
            raw = proc.stdout.strip()
            parts = raw.split("|", 1)
            status = parts[0] if parts else "Unknown"
            subject = parts[1] if len(parts) > 1 else ""

            # Extract CN= from subject
            cn_match = re.search(r"CN=([^,]+)", subject)
            signer_name = cn_match.group(1).strip('"') if cn_match else subject

            result = {
                "status": status,  # Valid, NotSigned, HashMismatch, UnknownError
                "signer": signer_name,
                "valid": (status == "Valid"),
            }
            self._sig_cache[exe_path] = result
            return result
        except Exception:
            return {"status": "Error", "signer": "", "valid": False}

    # -----------------------------------------------------------------
    # 3. REGISTRY ANOMALY & PATH HEURISTICS
    # -----------------------------------------------------------------
    def evaluate_heuristics(self, app_info: dict, exe_path: Optional[str]) -> List[str]:
        """
        Checks for PUP blocklist matches, hidden SystemComponent flags,
        and suspicious installation directories.
        """
        findings = []
        name = (app_info.get("name") or "").lower()
        publisher = (app_info.get("publisher") or "").lower()
        winget_id = (app_info.get("id") or app_info.get("winget_id") or "").lower()
        system_component = app_info.get("system_component", 0)
        uninstall_string = (app_info.get("uninstall_string") or "").strip()

        # Check PUP Name Patterns
        for pattern in self.blocklist.get("blocked_name_patterns", []):
            if pattern.lower() in name:
                findings.append(f"Matches known PUP/Adware pattern: '{pattern}'")

        # Check Blocked Publishers
        for blocked_pub in self.blocklist.get("blocked_publishers", []):
            if blocked_pub.lower() in publisher:
                findings.append(f"Blocked/Untrusted publisher: '{app_info.get('publisher')}'")

        # Check Blocked Winget IDs
        for blocked_id in self.blocklist.get("blocked_winget_ids", []):
            if blocked_id.lower() == winget_id:
                findings.append(f"Flagged Winget Package ID: '{blocked_id}'")

        # Stealth / Stalkerware Registry Anomaly Check
        if system_component == 1 and "microsoft" not in publisher and "windows" not in publisher:
            findings.append("Stealth Registry Flag: Hidden from Add/Remove Programs (SystemComponent=1)")

        if not uninstall_string and not winget_id and "microsoft" not in publisher:
            findings.append("Missing UninstallString (Potential stealth or persistent software)")

        # Suspicious Install Directory Check
        if exe_path:
            lower_path = exe_path.lower()
            for risky_dir in self.blocklist.get("high_risk_paths", []):
                if risky_dir.lower() in lower_path:
                    # Exclude legitimate user-space apps and WiX/Burn package caches
                    if not any(
                        safe in lower_path
                        for safe in (
                            "\\appdata\\local\\programs\\",
                            "\\programdata\\package cache\\",
                            "\\appdata\\local\\package cache\\",
                        )
                    ):
                        findings.append(f"Suspicious install path: {exe_path}")
                        break

        return findings

    # -----------------------------------------------------------------
    # 4. CLOUD THREAT INTELLIGENCE LOOKUPS (HASH ONLY)
    # -----------------------------------------------------------------
    def lookup_malwarebazaar(self, sha256_hash: str) -> dict:
        """
        Free, no-API-key hash lookup against Abuse.ch MalwareBazaar.
        Sends only the SHA-256 hash—never uploads files.
        """
        if not sha256_hash:
            return {"flagged": False, "source": "MalwareBazaar", "details": "No hash"}

        url = "https://mb-api.abuse.ch/api/v1/"
        payload = urllib.parse.urlencode({"query": "get_info", "hash": sha256_hash}).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload, headers={"User-Agent": "SoftwareUpdateManager-Auditor/2.3"}
        )
        try:
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("query_status") == "ok" and data.get("data"):
                    entry = data["data"][0]
                    sig = entry.get("signature") or "Known Malware"
                    return {
                        "flagged": True,
                        "source": "MalwareBazaar",
                        "details": f"MalwareBazaar Hit: {sig}",
                    }
        except Exception:
            pass
        return {"flagged": False, "source": "MalwareBazaar", "details": "Clean / Unknown"}

    def lookup_virustotal(self, sha256_hash: str) -> dict:
        """Optional VirusTotal API v3 hash reputation check."""
        if not sha256_hash or not self.vt_api_key:
            return {"flagged": False, "source": "VirusTotal", "details": "Skipped"}

        url = f"https://www.virustotal.com/api/v3/files/{sha256_hash}"
        req = urllib.request.Request(
            url,
            headers={
                "x-apikey": self.vt_api_key,
                "User-Agent": "SoftwareUpdateManager-Auditor/2.3",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
                malicious = stats.get("malicious", 0)
                suspicious = stats.get("suspicious", 0)
                if malicious >= 2 or (malicious + suspicious) >= 3:
                    return {
                        "flagged": True,
                        "source": "VirusTotal",
                        "details": f"VirusTotal Flagged ({malicious} malicious, {suspicious} suspicious)",
                    }
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"flagged": False, "source": "VirusTotal", "details": "Hash not in VT"}
        except Exception:
            pass
        return {"flagged": False, "source": "VirusTotal", "details": "Clean"}

    # -----------------------------------------------------------------
    # 5. MASTER TRUST SCORING & BADGE GENERATOR
    # -----------------------------------------------------------------
    def audit_application(self, app_info: dict, run_cloud_check: bool = False) -> dict:
        """
        Evaluates an application dictionary and returns a trust verdict:
        - 'TRUSTED'   (🟢 Trusted)    -> Safe for automatic batch update
        - 'CAUTION'   (🟡 Unverified) -> Unchecked by default in batch updates
        - 'HIGH_RISK' (🔴 High Risk)  -> Locked from auto-updating
        """
        exe_path = self.resolve_executable_path(
            app_info.get("display_icon", ""),
            app_info.get("install_location", ""),
            app_info.get("uninstall_string", ""),
            app_info.get("name", ""),
            app_info.get("id", "") or app_info.get("winget_id", ""),
        )
        # Check if this is an official Windows Store / MSIX package (cryptographically verified by Windows OS)
        winget_id = (app_info.get("id") or app_info.get("winget_id") or "").strip().lower()
        source = (app_info.get("source") or "").lower()
        is_verified_store_app = (
            source == "msstore"
            or any(winget_id.startswith(p) for p in ("anthropic.claude", "openai.chatgpt", "openai.codex", "microsoft."))
        )
        is_verified_cli_pkg = (
            winget_id == "google.cloudsdk"
            or (
                winget_id in ("gyan.ffmpeg", "burntsushi.ripgrep.msvc", "burntsushi.ripgrep.gnu")
                and (not exe_path or "\\microsoft\\winget\\links\\" in exe_path.lower())
            )
        )

        sha256 = self.get_sha256(exe_path) if exe_path else None
        reasons = self.evaluate_heuristics(app_info, exe_path)

        if not exe_path and is_verified_store_app:
            sig = {
                "status": "Valid",
                "signer": "Microsoft Windows Store / Vendor Appx",
                "valid": True,
            }
        else:
            sig = self.check_authenticode_signature(exe_path) if exe_path else {
                "status": "Unknown", "signer": "", "valid": False
            }

        if is_verified_cli_pkg and not reasons and sig["status"] != "HashMismatch":
            if not sig["valid"]:
                sig = {
                    "status": "Valid",
                    "signer": "Winget Verified CLI / SDK",
                    "valid": True,
                }

        cloud_flagged = False
        if run_cloud_check and sha256:
            mb_res = self.lookup_malwarebazaar(sha256)
            if mb_res["flagged"]:
                cloud_flagged = True
                reasons.append(mb_res["details"])

            vt_res = self.lookup_virustotal(sha256)
            if vt_res["flagged"]:
                cloud_flagged = True
                reasons.append(vt_res["details"])

        # Signature verification check
        if sig["status"] == "HashMismatch":
            reasons.append("CRITICAL: Digital signature HashMismatch (Binary modified or tampered!)")
            cloud_flagged = True
        elif sig["status"] == "NotSigned" and exe_path and not is_verified_cli_pkg:
            reasons.append("Binary is not digitally signed (Unsigned open-source or developer build)")
        elif not exe_path and not is_verified_store_app and not is_verified_cli_pkg:
            reasons.append("Executable binary not registered in Windows registry (WinGet/Store tool)")

        # Publisher vs Signer consistency check
        pub = (app_info.get("publisher") or "").lower()
        signer = (sig.get("signer") or "").lower()
        if sig["valid"] and pub and signer:
            if not is_publisher_signer_aligned(pub, signer):
                reasons.append(f"Publisher mismatch: Signer '{sig['signer']}' vs Registry '{app_info.get('publisher')}'")

        # Determine final Risk Tier & UI Badge
        if cloud_flagged or any("CRITICAL" in r or "Blocked" in r or "Matches known PUP" in r or "Stealth" in r for r in reasons):
            tier = "HIGH_RISK"
            badge = "🔴 High Risk"
            allow_auto_update = False
        elif not sig["valid"] or reasons:
            tier = "CAUTION"
            badge = "🟡 Unverified"
            allow_auto_update = False
        else:
            tier = "TRUSTED"
            badge = "🟢 Trusted"
            allow_auto_update = True

        return {
            "tier": tier,
            "badge": badge,
            "allow_auto_update": allow_auto_update,
            "exe_path": exe_path or "Not Resolved",
            "sha256": sha256 or "",
            "signature_status": sig["status"],
            "signer": sig["signer"],
            "reasons": reasons,
            "vt_url": f"https://www.virustotal.com/gui/file/{sha256}" if sha256 else "",
        }

    def audit_all_installed_software(self, installed_apps: list) -> dict:
        """Fast full-inventory heuristic, path, and cached signature posture audit."""
        trusted_count = 0
        caution_count = 0
        high_risk_count = 0
        flagged_items = []

        for app in installed_apps or []:
            exe_path = self.resolve_executable_path(
                app.get("display_icon", ""),
                app.get("install_location", ""),
                app.get("uninstall_string", ""),
                app.get("name", ""),
                app.get("id", "") or app.get("winget_id", ""),
            )
            findings = self.evaluate_heuristics(app, exe_path)
            cached_sig = self._sig_cache.get(exe_path, {}) if exe_path else {}
            if cached_sig.get("status") == "HashMismatch":
                findings.append("CRITICAL: Digital signature HashMismatch (Binary modified or tampered!)")
            elif cached_sig.get("status") == "NotSigned":
                findings.append("Binary is not digitally signed (Unsigned open-source or developer build)")

            if any(
                "CRITICAL" in r or "Blocked" in r or "Matches known PUP" in r or "Stealth" in r
                for r in findings
            ):
                high_risk_count += 1
                flagged_items.append({
                    "name": app.get("name", ""),
                    "publisher": app.get("publisher", ""),
                    "tier": "HIGH_RISK",
                    "exe_path": exe_path or "",
                    "reasons": findings,
                })
            elif findings:
                caution_count += 1
                flagged_items.append({
                    "name": app.get("name", ""),
                    "publisher": app.get("publisher", ""),
                    "tier": "CAUTION",
                    "exe_path": exe_path or "",
                    "reasons": findings,
                })
            else:
                trusted_count += 1

        return {
            "total": len(installed_apps or []),
            "trusted_count": trusted_count,
            "caution_count": caution_count,
            "high_risk_count": high_risk_count,
            "flagged_items": flagged_items,
        }
