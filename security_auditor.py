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
import hashlib
import subprocess
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional


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
    def resolve_executable_path(display_icon: str, install_location: str, uninstall_string: str = "") -> Optional[str]:
        """
        Extracts a clean executable path from Windows Registry DisplayIcon,
        InstallLocation, or UninstallString.
        """
        # 1. Try DisplayIcon
        if display_icon:
            cleaned = display_icon.split(",")[0].strip().strip('"').strip("'")
            if cleaned.lower().endswith(".exe") and os.path.isfile(cleaned):
                return cleaned

        # 2. Try InstallLocation
        if install_location:
            loc = install_location.strip().strip('"').strip("'")
            if os.path.isfile(loc) and loc.lower().endswith(".exe"):
                return loc
            if os.path.isdir(loc):
                try:
                    candidates = []
                    for item in os.listdir(loc):
                        if item.lower().endswith(".exe") and not any(
                            skip in item.lower() for skip in ("unins", "uninst", "setup", "update", "crash", "helper")
                        ):
                            candidates.append(os.path.join(loc, item))
                    if candidates:
                        return candidates[0]
                except OSError:
                    pass

        # 3. Try UninstallString (often points to app folder / uninstaller)
        if uninstall_string:
            m = re.search(r'["\']?([^"\']+\.exe)["\']?', uninstall_string, re.IGNORECASE)
            if m:
                u_exe = m.group(1).strip()
                if os.path.isfile(u_exe):
                    d = os.path.dirname(u_exe)
                    try:
                        for item in os.listdir(d):
                            if item.lower().endswith(".exe") and not any(
                                skip in item.lower() for skip in ("unins", "uninst", "setup")
                            ):
                                return os.path.join(d, item)
                    except OSError:
                        pass

        return None

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

        if not uninstall_string and "microsoft" not in publisher:
            findings.append("Missing UninstallString (Potential stealth or persistent software)")

        # Suspicious Install Directory Check
        if exe_path:
            lower_path = exe_path.lower()
            for risky_dir in self.blocklist.get("high_risk_paths", []):
                if risky_dir.lower() in lower_path:
                    # Exclude legitimate user-space apps in standard AppData\Local\Programs
                    if "\\appdata\\local\\programs\\" not in lower_path:
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
        )
        sha256 = self.get_sha256(exe_path) if exe_path else None
        sig = self.check_authenticode_signature(exe_path) if exe_path else {
            "status": "Unknown", "signer": "", "valid": False
        }
        reasons = self.evaluate_heuristics(app_info, exe_path)

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
        elif sig["status"] == "NotSigned" and exe_path:
            reasons.append("Binary is not digitally signed (Unsigned executable)")
        elif not exe_path:
            reasons.append("Executable path not found in registry (WinGet source only)")

        # Publisher vs Signer consistency check
        pub = (app_info.get("publisher") or "").lower()
        signer = (sig.get("signer") or "").lower()
        if sig["valid"] and pub and signer:
            # Check if signer name roughly aligns with publisher
            p_words = set(re.findall(r"\w+", pub))
            s_words = set(re.findall(r"\w+", signer))
            if not p_words.intersection(s_words) and "microsoft" not in pub:
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
