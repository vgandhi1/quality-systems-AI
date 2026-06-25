# Dev LAN Access — WSL2 API from a Remote PC

How to reach `warranty-api` (port **8080**) from another machine on the same Wi‑Fi/LAN when the server runs **inside WSL2**.

**Applies to:** `uv run warranty-api` (binds `0.0.0.0:8080` inside WSL)

---

## Why `172.*` vs `192.*` matters

| Address | What it is | Who can use it |
|---------|------------|----------------|
| `172.x.x.x` | WSL2 virtual NIC (NAT behind Windows) | WSL, sometimes Windows localhost |
| `192.x.x.x` (or `10.x.x.x`) | Windows on your physical LAN | **Other PCs on the network** |

- You **cannot** give a remote PC the WSL `172.*` address — it is not routable on your home/office LAN.
- Remote browsers must use the **Windows LAN IP** (`192.*`).
- Windows must **forward** port 8080 into WSL.

```text
Remote PC  →  http://192.168.1.42:8080  →  Windows  →  WSL 172.28.x.x:8080
```

`0.0.0.0` in the server config means “listen on all interfaces **inside WSL**” — not “automatically visible on the LAN.”

---

## Quick setup

### 1. Start the API (in WSL)

```bash
cd warranty
uv sync --extra api
uv run warranty-api
```

### 2. Get the WSL IP (in WSL)

```bash
hostname -I | awk '{print $1}'
# Example: 172.28.123.45
```

### 3. Port forward on Windows (PowerShell **as Administrator**)

Replace `172.28.123.45` with your WSL IP from step 2.

```powershell
netsh interface portproxy add v4tov4 listenport=8080 listenaddress=0.0.0.0 connectport=8080 connectaddress=172.28.123.45
```

Allow inbound traffic in Windows Firewall:

```powershell
New-NetFirewallRule -DisplayName "Warranty API 8080" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow
```

### 4. Get Windows LAN IP (on Windows)

```powershell
ipconfig
```

Use the **IPv4 Address** of your active adapter (Wi‑Fi or Ethernet), e.g. `192.168.1.42`.

### 5. Open from the remote PC

```text
http://192.168.1.42:8080/health
http://192.168.1.42:8080/docs
```

---

## Verify before testing remote

On **Windows**:

```powershell
curl http://127.0.0.1:8080/health
curl http://192.168.1.42:8080/health
```

| Result | Likely cause |
|--------|----------------|
| `127.0.0.1` fails | API not running in WSL, or wrong port |
| `127.0.0.1` OK, `192.*` fails | Windows Firewall blocking inbound |
| Both OK on Windows, remote fails | Router client isolation, wrong IP, different subnet |

---

## WSL IP changed after reboot

WSL2 often gets a new `172.*` address after restart. Re-run portproxy:

```powershell
# Remove old rule (if exists)
netsh interface portproxy delete v4tov4 listenport=8080 listenaddress=0.0.0.0

# Add with new WSL IP
netsh interface portproxy add v4tov4 listenport=8080 listenaddress=0.0.0.0 connectport=8080 connectaddress=<NEW_WSL_IP>
```

List current rules:

```powershell
netsh interface portproxy show all
```

---

## Alternatives

### WSL mirrored networking (Windows 11)

In `%UserProfile%\.wslconfig`:

```ini
[wsl2]
networkingMode=mirrored
```

Then `wsl --shutdown` and reopen WSL. Mirrored mode can simplify LAN exposure; behavior varies by Windows build — test with `curl` from a remote PC.

### Run API on Windows (skip portproxy)

Install Python/uv on Windows, clone the repo, run `uv run warranty-api` natively on Windows. Bind to `0.0.0.0:8080` and use the Windows `192.*` IP directly.

### SSH tunnel (no firewall hole)

From the remote PC:

```bash
ssh -L 8080:127.0.0.1:8080 user@192.168.1.42
```

Then open `http://localhost:8080` on the remote machine.

---

## Security on a shared LAN

The API enforces auth based on bind address and environment:

| Mode | `WARRANTY_API_KEY` needed? |
|------|----------------------------|
| `127.0.0.1` + `development` | **No** (local dev only) |
| `0.0.0.0` (LAN) | **Yes** — startup fails without it |
| `production` | **Yes** — startup fails without it |

**Generate a key:**

```bash
openssl rand -hex 32
```

**`.env` for LAN access:**

```bash
WARRANTY_ENVIRONMENT=development
WARRANTY_API_HOST=0.0.0.0
WARRANTY_API_PORT=8080
WARRANTY_API_KEY=<paste-output-of-openssl-rand>
# WARRANTY_CORS_ORIGINS=http://192.168.1.10:3000
```

**Remote requests must include:**

```http
X-API-Key: <your-key>
```

Example:

```bash
curl -H "X-API-Key: YOUR_KEY" http://192.168.1.42:8080/health
curl -H "X-API-Key: YOUR_KEY" -H "Content-Type: application/json" \
  -d '{"scenario":"auto_approve"}' \
  http://192.168.1.42:8080/adjudicate/dry-run
```

`/health` and `/docs` work without the key; protected routes (`/adjudicate/*`, `/escalate/*`, `/claim-state`) require it when LAN-bound or in production.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Connection refused | Confirm `uv run warranty-api` is running; check port 8080 |
| Timeout from remote | Firewall rule; router AP isolation (guest Wi‑Fi) |
| Works on Windows, not remote | Use Windows `192.*` IP, not WSL `172.*` |
| Worked yesterday, not today | WSL IP changed — update `portproxy` |
| `0.0.0.0` in browser fails | Use `localhost` or LAN IP — never browse to `0.0.0.0` |

---

## Related

- [README.md](./README.md) — API endpoints  
- [plan.md](./plan.md) — security backlog (P0 LAN items)  
- [../QUALITY-SYSTEMS-GUARDRAILS.md](../QUALITY-SYSTEMS-GUARDRAILS.md) — portfolio guardrails  
