#!/bin/bash
# Run once, from the project root on the box:  sudo bash ops/remote-access/install.sh
#
# 1. SSH accepts keys only. A password can be guessed; the laptop's key cannot.
# 2. Tailscale, so the laptop reaches the box from any network (a demo on campus
#    Wi-Fi) without opening a port on the router. Nothing is exposed to the
#    internet: only devices signed in to the same Tailscale account can connect.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
OWNER="${SUDO_USER:?run with sudo from your own account, not as root}"
OWNER_HOME="$(getent passwd "$OWNER" | cut -d: -f6)"

echo "== 1/2 SSH: keys only"
# Refuse to lock the door without a key in hand.
if ! grep -qE '^(ssh-ed25519|ssh-rsa|ecdsa-sha2-)' "$OWNER_HOME/.ssh/authorized_keys" 2>/dev/null; then
  echo "   no key in $OWNER_HOME/.ssh/authorized_keys; leaving passwords on"; exit 1
fi
# sshd keeps the first value it reads, and 50-cloud-init.conf says
# "PasswordAuthentication yes", so this file has to sort before it.
cat > /etc/ssh/sshd_config.d/01-keys-only.conf <<'CONF'
# Installed by ops/remote-access/install.sh
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
CONF
sshd -t
systemctl reload ssh
# Read into a variable first: `sshd -T | grep -q` under pipefail fails even on a
# match, because grep exits early and sshd dies of SIGPIPE.
EFFECTIVE="$(sshd -T)"
if grep -qx 'passwordauthentication no' <<<"$EFFECTIVE"; then
  echo "   passwords off (sessions already open stay open)"
else
  echo "   sshd still reports password authentication on:"; grep -i passwordauthentication <<<"$EFFECTIVE"; exit 1
fi

echo "== 2/2 Tailscale"
if ! command -v tailscale >/dev/null; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
systemctl enable --now tailscaled
# Named a1-4rd, so the laptop can reach it as "a1-4rd" from anywhere.
tailscale up --hostname=a1-4rd
echo "   tailscale address: $(tailscale ip -4)"
echo
echo "Done. In the Tailscale admin page, open a1-4rd and choose 'Disable key expiry',"
echo "or the box drops off the network in 180 days and needs a sudo login to rejoin."
