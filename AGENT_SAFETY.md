# 🛡️ AI Agent Integration, Permission Safety & Best Practices

## ⚠️ Third-Party AI Autonomy & Responsibility Notice

> **Connecting external AI agents (such as Microsoft Copilot, Claude Desktop, or local models) to your system is an advanced, optional capability. While Software Update Manager enforces strict local permission boundaries and approval gates, the internal decision-making, reasoning, and outputs of third-party AI models remain entirely outside our control. By enabling live agent integration, you acknowledge and assume full responsibility for actions initiated by your chosen AI assistant.**

Software Update Manager provides this capability to empower advanced users and developers, but we believe in giving you the education, tools, and guardrails necessary to explore agentic AI safely without risking your system integrity.

---

## 🛡️ Quick-Start: How to Connect Your AI Agent Safely

Follow this 4-step protocol whenever connecting an AI model to your workstation:

### 1. Start at Level 1 (Read-Only Diagnostic)
Leave the permission tier set to **Level 1** for your initial runs. This allows your AI assistant to audit hardware specs, check for available Winget updates, and scan for exposed network ports (`0.0.0.0`) **without modifying a single file, package, or registry hive**.

### 2. Use Local STDIO (Zero Open Ports)
Connect desktop clients (such as Claude Desktop, Antigravity IDE, or local Ollama scripts) via the local standard input/output (`stdio`) transport (`python agent_bridge.py --mcp`) rather than opening an HTTP port over your local Wi-Fi or LAN. Stdio connections are bound strictly to the local parent process and cannot be reached by external network scanners.

### 3. Review Every Level 2 Approval Prompt
If you elevate to **Level 2 (Supervised Remediation)**, always inspect the target package name, version, and command inside the pop-up approval dialog before clicking **Approve**. Never approve updates or actions on `🟡 Unverified` or `🔴 High Risk` packages.

### 4. Create a Windows System Restore Point First
Before authorizing **Level 3 (Autonomous Maintenance)** for sequential batch updates, let Software Update Manager automatically create a Windows System Restore Point. This ensures you can roll back your system state with one click if an installer misbehaves.

---

## 🎥 Curated Video Tutorials & Learning Resources

To better understand how the Model Context Protocol (MCP) works on Windows, how prompt injection is prevented, and why least-privilege architecture is essential, we recommend these short guides:

1. 🎥 **[Easy Connect Claude AI Desktop to MCP Servers (For Windows)](https://www.youtube.com/watch?v=A151Nk_nN_U)**  
   *By Saeed Esmaeelinejad (9 mins)*  
   Step-by-step walkthrough showing how to edit `claude_desktop_config.json` on Windows to connect an AI client to local developer tools without opening network ports.

2. 🎥 **[Securing the MCP Server: What You Need to Know](https://www.youtube.com/watch?v=KYWr454hGF0)**  
   *By Box Engineering*  
   Explains prompt injection risks, untrusted metadata isolation, and why human-in-the-loop approval gates are critical for securing local agent runtimes.

3. 🎥 **[What Should an AI Agent Access? | Least Privilege for AI](https://www.youtube.com/watch?v=4HiuiYIJRTU)**  
   *By Ambilio (7 mins)*  
   A clear, plain-English breakdown of starting AI agents in read-only mode to "shrink the blast radius" before granting mutating write permissions.

4. 📖 **[Official Model Context Protocol Security Best Practices](https://modelcontextprotocol.io/docs/draft/tutorials/security/security_best_practices)**  
   The authoritative security architecture specification for MCP server developers and host applications.

5. 📖 **[Anthropic Claude Desktop Local MCP Server Documentation](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop)**  
   Official setup guide for configuring local tool servers in Claude Desktop.

---

## 4-Tier Permission Architecture Summary

| Tier | Name | Allowed Capabilities | Safety & Enforcement Mechanism |
| :--- | :--- | :--- | :--- |
| **Level 0** | **Off / Air-Gapped** | No agent listener active. Zero IPC responses. | Complete isolation. Zero attack surface. |
| **Level 1** | **Read-Only Diagnostic** *(Default)* | Hardware specs, inventory, listening sockets, security audits. | Read-only whitelist. Strings sanitized against Indirect Prompt Injection (IPI). |
| **Level 2** | **Supervised Remediation** | Single-package upgrades, firewall toggling, browser updates. | **Interactive UI Approval Modal:** Every write action pauses and prompts the user. High-risk packages permanently locked out. |
| **Level 3** | **Autonomous Maintenance** | Sequential batch updates of trusted packages. | **System Restore Point mandatory.** Unverified/PUP packages blocked. Auto-downgrades to Level 1 after 30 minutes. |
