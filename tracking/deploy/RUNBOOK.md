# Tracking server — deployment runbook

One-shot deployment of `ww-tracking` to the Hostinger VPS. Run these steps in
order from a fresh SSH session. Everything is idempotent — re-running steps is
safe.

**Prerequisites**

- DNS `track.richbondgroup.eu` CNAME to `srv1553383.hstgr.cloud` is live.
  Quick check from your laptop: `dig +short track.richbondgroup.eu` should
  return the Hostinger hostname (or its IP).
- SSH access to the VPS as a sudo-capable user.
- A git remote URL you can clone the repo from on the VPS.

---

## 1. SSH in

```
ssh root@srv1553383.hstgr.cloud
```

(Or as your sudo user if root login is disabled.)

## 2. Create a dedicated service user (recommended)

Running long-lived services as root is bad hygiene. One-time setup:

```
adduser --disabled-password --gecos "" ww
usermod -aG sudo ww
```

Then switch to that user for everything below:

```
su - ww
```

If you'd rather just run as root for a no-frills first deploy, skip this and
substitute `root` everywhere `ww` appears below — everything else still works.

## 3. Install base packages

```
sudo apt update
sudo apt install -y git curl ca-certificates
```

## 4. Install uv (as the service user)

```
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
uv --version    # confirm
```

`uv` handles Python interpreter installation automatically — no `apt install
python3.11` step needed.

## 5. Clone the repo

```
cd ~
git clone https://github.com/dtazi/winston-wolf.git
cd winston-wolf
git checkout 002-outreach-campaign-engine
```

If the repo is private, set up GitHub auth on the VPS first (personal access
token via HTTPS, or an SSH key added to the `dtazi` account).

## 6. Initialize the database

```
cd ~/winston-wolf/core
uv sync
uv run ww-core init       # creates data/leads.db, seeds source_channels (idempotent)
```

## 7. Install tracking dependencies

```
cd ~/winston-wolf/tracking
uv sync
```

## 8. Install the systemd unit

```
sudo cp deploy/ww-tracking.service /etc/systemd/system/ww-tracking.service
sudo sed -i "s|YOUR_USER|ww|g" /etc/systemd/system/ww-tracking.service
sudo systemctl daemon-reload
sudo systemctl enable --now ww-tracking
sudo systemctl status ww-tracking    # expect: active (running)
```

If you skipped step 2 and are running as root, substitute `root` for `ww` in
the `sed` command. Adjust the paths inside `ww-tracking.service` accordingly
(`/root/winston-wolf/...`).

## 9. Install Caddy

```
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install -y caddy
```

## 10. Install the Caddyfile

```
sudo cp ~/winston-wolf/tracking/deploy/Caddyfile /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Caddy will reach out to Let's Encrypt and obtain an HTTPS certificate for
`track.richbondgroup.eu` automatically. First request can take 30–60 seconds.
Tail Caddy logs to watch:

```
sudo journalctl -u caddy -f
```

## 11. Open the firewall (if active)

```
sudo ufw status
# If active:
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

If `ufw` is not installed or inactive, skip — Hostinger images often ship with
the firewall off, in which case ports 80/443 are already reachable.

## 12. End-to-end verification

**From the VPS** (loopback — confirms the app is up):

```
curl http://127.0.0.1:8000/healthz
# expected: {"status":"ok"}
```

**From your laptop** (full stack — confirms DNS + HTTPS + reverse proxy):

```
curl https://track.richbondgroup.eu/healthz
# expected: {"status":"ok"} over HTTPS, valid certificate
```

If both pass, the tracking server is production-live.

---

## Operations

**Tail logs:**

```
sudo journalctl -u ww-tracking -f       # the tracking app
sudo journalctl -u caddy -f             # Caddy + certificate events
```

**Restart after a code change:**

```
cd ~/winston-wolf
git pull
cd tracking
uv sync                                  # in case deps changed
sudo systemctl restart ww-tracking
```

**Restart after a Caddyfile change:**

```
sudo cp ~/winston-wolf/tracking/deploy/Caddyfile /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

**Revoke (in case of doubt):**

```
sudo systemctl stop ww-tracking
sudo systemctl disable ww-tracking
```

Plus removing the CNAME on Richbond's DNS side fully decommissions the
endpoint — no traffic can reach the VPS at `track.richbondgroup.eu` anymore.
