# Deploying to Oracle Cloud (Always Free)

The app runs on one Always Free **Ampere A1** VM (ARM) as two containers: Streamlit, and Caddy in front of it for
HTTPS. The hostname is `<ip-with-dashes>.sslip.io`, a free wildcard DNS name that resolves to the VM's IP, so
Caddy can get a Let's Encrypt certificate without our own domain. Keep `APP_PASSWORD` set: the index is derived
from copyrighted textbooks and the VM has a public IP.

## 1. In the OCI console (you)
1. **Compute → Instances → Create instance**
   * Image: **Canonical Ubuntu 24.04** (not Oracle Linux — `setup.sh` uses apt)
   * Shape: **VM.Standard.A1.Flex**, 2 OCPU / 12 GB is plenty (Always Free allows up to 4 / 24)
   * "Out of capacity"? Try another availability domain, or retry later; A1 capacity comes and goes.
   * Networking: create a new VCN with a **public subnet**, **assign a public IPv4 address**
   * SSH keys: **paste the public key** from `~/.ssh/eka_oci.pub` (created with `ssh-keygen -t ed25519 -f ~/.ssh/eka_oci`)
2. **Networking → VCN → (subnet) → Default security list → Add ingress rules**
   * Source `0.0.0.0/0`, TCP, destination port **80**
   * Source `0.0.0.0/0`, TCP, destination port **443**
3. Copy the instance's **public IP**.

## 2. Secrets (you)
In `med-rag/.env` add `APP_PASSWORD=<something>` (`DEEPSEEK_API_KEY` is already there). `push.sh` copies only
these two values to the VM (mode 600) and refuses to run without both.

## 3. Deploy (one command)
```bash
deploy/oci/push.sh <public-ip>            # optional 2nd arg: path to your SSH private key
```
It builds the bundle (code, BODHI, compacted index), rsyncs it to `~/eka` on the VM, installs Docker, opens
ports 80/443 in the VM's own iptables (Oracle's Ubuntu image blocks them even when the security list allows them),
and starts the containers. It prints the `https://….sslip.io` URL at the end.

Re-run the same command to redeploy after changes.

## Troubleshooting
| Symptom | Cause |
|---|---|
| `ssh: connection timed out` | no public IP, or the subnet is private |
| site times out but SSH works | security-list ingress for 80/443 missing |
| certificate error for the first ~30 s | Caddy is still getting the certificate |
| "DeepSeek API refused the request" in the app | key or balance; check `.env` on the VM |
| logs | `ssh ubuntu@<ip> 'cd eka && sudo docker compose logs -f app'` |

## Live deployment (2026-11-12)
* URL: **https://mentor.medevolv.in** (backup: https://130-210-60-153.sslip.io); password-gated, password in `.env`, never in git
* Redeploy: `DOMAIN=mentor.medevolv.in deploy/oci/push.sh 130.210.60.153` (omit DOMAIN and Caddy drops the domain cert)
* VM: `eka-study-companion`, Mumbai, **VM.Standard.E5.Flex** 1 OCPU / 12 GB, Ubuntu 24.04 (x86).
  A1 (Always Free) was out of capacity in Mumbai, so this runs on **trial credit** and will stop when the trial
  ends unless the account is upgraded. Recreate on A1 later if capacity frees up.
* The new-VCN wizard created the internet gateway and route but did **not** attach a public IP: add an
  ephemeral one under VNIC → IP administration → ⋯ → Edit (the ⋯ menu opens with Enter if clicks do nothing).
* Never run two `push.sh` at once: each builds a fresh index folder and rsync `--delete` makes them clobber each other.

## Custom domain (e.g. study.medevolv.in)
1. At the medevolv.in DNS provider add an **A record**: `study` → `130.210.60.153` (TTL 300). For the bare
   domain use host `@` instead.
2. Wait until `dig +short study.medevolv.in` prints the IP.
3. `DOMAIN=study.medevolv.in deploy/oci/push.sh 130.210.60.153` — Caddy gets a certificate for the domain and
   keeps serving the sslip.io name too.
