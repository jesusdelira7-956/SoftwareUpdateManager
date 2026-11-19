"""
Zero-Dependency Network Boundary & Intrusion Shield Auditor
===========================================================
Part of Software Update Manager & Intrusion Shield (v2.4.0).
Uses 100% Python Standard Library (zero pip packages).

Core Mission:
- Keep the user's computer fully updated while proactively protecting
  it against unknown network intrusions, exposed local AI/developer ports
  (0.0.0.0 bindings), and malicious payload injection — 100% Free & Open-Source.

Threat Model Addressed:
- Autonomous offensive platforms (e.g. ARTEX) that build Asset & Exploration Graphs,
  scan for open listening ports across the local network (0.0.0.0), exploit unauthenticated
  local AI/MCP endpoints, and leverage Indirect Prompt Injection (IPI).
"""

import csv
import io
import os
import re
import subprocess
from typing import Dict, List, Optional, Tuple

# Well-known local AI inference engines, agent servers, and developer stacks
KNOWN_AI_DEV_PORTS: Dict[int, str] = {
    11434: "Ollama LLM Engine",
    1234: "LM Studio Server",
    8081: "Open WebUI Sovereign Stack",
    8088: "DwarfStar Inference Engine",
    8890: "Antigravity App Hub & MCP Bridge",
    8892: "The Observatory Smart-Home HUD",
    8895: "Link Analyzer Web UI",
    8896: "Spatial Studio Lab (WebXR)",
    49374: "OpenCode Agent Server",
    8188: "ComfyUI Stable Diffusion",
    7860: "Gradio Web UI / Automatic1111",
    3000: "Web App Dev Server (Node/React/Next.js)",
    5000: "Flask / Python API Server",
    8000: "FastAPI / Django Backend",
    8080: "General Web Proxy / Local Service",
    9000: "FastMCP / Portainer / Debug Server",
}

FIREWALL_RULE_NAME = "SoftwareUpdateManager_Block_DevPorts_LAN"


def get_pid_to_process_map() -> Dict[int, str]:
    """Return a mapping of PID -> Process Name using native Windows tasklist."""
    pid_map: Dict[int, str] = {}
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        proc = subprocess.run(
            ["tasklist.exe", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=10,
            startupinfo=startupinfo,
        )
        if proc.returncode == 0 and proc.stdout:
            reader = csv.reader(io.StringIO(proc.stdout))
            for row in reader:
                if len(row) >= 2:
                    try:
                        p_name = row[0].strip()
                        pid_val = int(row[1].strip())
                        pid_map[pid_val] = p_name
                    except ValueError:
                        continue
    except Exception:
        pass
    return pid_map


def audit_listening_ports() -> List[dict]:
    """
    Parse native netstat to identify all listening TCP ports.
    Evaluates whether each local AI or developer service is safely isolated
    to localhost (127.0.0.1 / ::1) or dangerously exposed to the local network (0.0.0.0 / [::]).
    """
    pid_map = get_pid_to_process_map()
    listeners: List[dict] = []

    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        proc = subprocess.run(
            ["netstat.exe", "-ano", "-p", "tcp"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=10,
            startupinfo=startupinfo,
        )
        if proc.returncode != 0 or not proc.stdout:
            return listeners

        for line in proc.stdout.splitlines():
            line_str = line.strip()
            if not line_str.startswith("TCP") or "LISTENING" not in line_str:
                continue

            parts = line_str.split()
            if len(parts) < 5:
                continue

            local_addr = parts[1]
            state = parts[3]
            try:
                pid = int(parts[4])
            except ValueError:
                pid = 0

            if state != "LISTENING":
                continue

            # Parse IP and Port (handles IPv4 and IPv6)
            if ":" not in local_addr:
                continue

            r_idx = local_addr.rfind(":")
            ip_str = local_addr[:r_idx].strip("[]")
            try:
                port_num = int(local_addr[r_idx + 1 :])
            except ValueError:
                continue

            # Evaluate exposure
            # 127.0.0.1, localhost, ::1 are loopback only (safe)
            is_loopback = ip_str in ("127.0.0.1", "localhost", "::1")
            is_wildcard = ip_str in ("0.0.0.0", "::", "")

            # Identify if it is a known AI/Dev service
            service_desc = KNOWN_AI_DEV_PORTS.get(port_num)
            is_dev_range = (
                (3000 <= port_num <= 5050)
                or (7800 <= port_num <= 9050)
                or (port_num in (11434, 1234, 49374))
            )

            if not service_desc and not is_dev_range:
                # Skip non-developer OS ports (e.g. RPC 135, SMB 445, high ephemeral ports)
                continue

            proc_name = pid_map.get(pid, "Unknown")
            desc = service_desc or f"Developer Service (Port {port_num})"

            if is_loopback:
                exposure_badge = "🟢 Localhost (Isolated)"
                exposure_level = "SECURE"
                risk_note = "Bound strictly to 127.0.0.1. Protected from LAN network probes."
            elif is_wildcard:
                exposure_badge = "🔴 Exposed to LAN (0.0.0.0)"
                exposure_level = "HIGH_RISK"
                risk_note = (
                    "Bound to all interfaces (0.0.0.0). Vulnerable to autonomous "
                    "scanners (ARTEX) and unauthorized requests from other devices on Wi-Fi/LAN."
                )
            else:
                exposure_badge = f"🟡 Bound to {ip_str}"
                exposure_level = "CAUTION"
                risk_note = f"Bound to interface {ip_str}. Check subnet exposure."

            listeners.append(
                {
                    "port": port_num,
                    "ip": ip_str,
                    "pid": pid,
                    "process_name": proc_name,
                    "service_desc": desc,
                    "is_loopback": is_loopback,
                    "is_exposed": not is_loopback,
                    "badge": exposure_badge,
                    "level": exposure_level,
                    "risk_note": risk_note,
                }
            )

    except Exception:
        pass

    # Deduplicate by port + IP
    seen = set()
    deduped = []
    for item in listeners:
        key = (item["port"], item["ip"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    return sorted(deduped, key=lambda x: (not x["is_exposed"], x["port"]))


def audit_firewall_shield() -> Tuple[bool, str]:
    """
    Check if the SoftwareUpdateManager Windows Defender Firewall block rule is active.
    This rule blocks inbound LAN probing on developer & AI port ranges across
    Public and Private profiles while preserving seamless 127.0.0.1 loopback access.
    """
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        proc = subprocess.run(
            ["netsh.exe", "advfirewall", "firewall", "show", "rule", f"name={FIREWALL_RULE_NAME}"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=8,
            startupinfo=startupinfo,
        )
        if proc.returncode == 0 and "Enabled:" in proc.stdout:
            is_enabled = "Enabled:                              Yes" in proc.stdout or "Enabled:                              yes" in proc.stdout.lower()
            if is_enabled:
                return True, "Active (Developer & AI ports blocked from LAN probes)"
            return False, "Rule exists but is currently disabled"
        return False, "Not Configured (Developer ports unshielded from LAN)"
    except Exception as e:
        return False, f"Check error: {e}"


def apply_firewall_shield(enable: bool = True) -> Tuple[bool, str]:
    """
    Enable or disable the Windows Firewall intrusion block rule.
    Requires Administrator privileges (which SoftwareUpdateManager requests on launch).
    """
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # 1. Delete existing rule if present
        subprocess.run(
            ["netsh.exe", "advfirewall", "firewall", "delete", "rule", f"name={FIREWALL_RULE_NAME}"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=10,
            startupinfo=startupinfo,
        )

        if not enable:
            return True, "Firewall intrusion shield disabled."

        # 2. Add strict inbound block rule for AI and developer ports
        ports_str = "11434,1234,8081,8088,8890,8892,8895,8896,49374,8188,7860,3000,5000,8000,8080,9000"
        cmd = [
            "netsh.exe",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            f"name={FIREWALL_RULE_NAME}",
            "dir=in",
            "action=block",
            "protocol=TCP",
            f"localport={ports_str}",
            "profile=public,private",
            "description=SoftwareUpdateManager Intrusion Shield: Blocks inbound LAN probes on local AI/dev ports while preserving 127.0.0.1 localhost.",
        ]
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=15,
            startupinfo=startupinfo,
        )
        if res.returncode == 0:
            return True, "Firewall Intrusion Shield successfully activated! Inbound LAN probes on AI & dev ports are now blocked."
        return False, f"Netsh failed (Code {res.returncode}): {res.stderr or res.stdout}"
    except Exception as e:
        return False, f"Failed to configure firewall: {e}"


def sanitize_untrusted_text(text: str, max_length: int = 150) -> str:
    """
    Sanitize untrusted metadata (package names, version strings, release descriptions)
    to prevent Indirect Prompt Injection (IPI) and terminal command injection.
    Strips dangerous characters like command separators (&, |, ;, `, $), control codes,
    and markdown exploit wrappers.
    """
    if not text:
        return ""
    # Strip non-printable / control characters
    cleaned = "".join(c for c in text if c.isprintable())
    # Remove command injection metacharacters
    cleaned = re.sub(r"[;&`$\<\>\|\"]", "", cleaned)
    # Truncate to reasonable length to prevent buffer bloat
    return cleaned[:max_length].strip()
