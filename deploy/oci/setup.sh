#!/usr/bin/env bash
# Runs ON the VM (Ubuntu, Always Free Ampere A1). Installs Docker, opens 80/443, starts the app with HTTPS.
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v docker >/dev/null; then
  sudo apt-get update -y
  sudo apt-get install -y docker.io docker-compose-v2 netfilter-persistent
  sudo usermod -aG docker "$USER"
fi

# Oracle's Ubuntu images ship iptables rules that drop everything except SSH, even when the VCN security list allows it
# Insert the ACCEPT rules just above the image's catch-all REJECT (or at the top if there is none)
POS=$(sudo iptables -L INPUT --line-numbers -n | awk '$2=="REJECT"{print $1; exit}')
for port in 80 443; do
  sudo iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null \
    || sudo iptables -I INPUT "${POS:-1}" -p tcp --dport "$port" -j ACCEPT
done
sudo netfilter-persistent save >/dev/null

IP=$(curl -s https://ifconfig.me)
SSLIP="${IP//./-}.sslip.io"                     # free hostname that resolves to this IP, so Caddy can get a cert
# DOMAIN (optional, e.g. study.medevolv.in): needs a DNS A record pointing at $IP first. Both names stay served.
export SITE_ADDRESS="${DOMAIN:+$DOMAIN, }$SSLIP"
echo "SITE_ADDRESS=$SITE_ADDRESS" > .compose.env

sudo SITE_ADDRESS="$SITE_ADDRESS" docker compose --env-file .compose.env up -d --build
# The Caddyfile is a single-file bind mount and rsync replaces it with a new inode, so a running container keeps
# reading the old file. Recreate Caddy so it mounts the new one (certificates persist in the caddy_data volume).
sudo SITE_ADDRESS="$SITE_ADDRESS" docker compose --env-file .compose.env up -d --force-recreate --no-deps caddy
echo
echo "Deployed: https://${DOMAIN:-$SSLIP}  (first HTTPS request can take ~30 s while the certificate is issued)"
