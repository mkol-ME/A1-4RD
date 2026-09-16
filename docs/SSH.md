# SSH to the A1-4RD server

```
ssh a1-4rd
```

Uses the `a1-4rd` alias in `~/.ssh/config` (host `xxx.xxx.xxx.xxx`, user `<user>`, key `~/.ssh/a1-4rd`).
Key-based; no password is needed to log in. `sudo` still asks for one.

The address comes from the router's DHCP and is not reserved. If `ssh a1-4rd` stops connecting, find the
server by scanning the LAN for port 22, check that its ed25519 host key matches the known one, and update
`HostName` in `~/.ssh/config`. (Another device on the LAN also answers on port 22 — check the host key.)

The project lives in `~/a1-4rd/` with the same layout as this repo, plus the git-ignored assets (venvs,
voice models, training data) at the top level.

Copy files back and forth:

```
scp persona/examples.md a1-4rd:~/a1-4rd/persona/
scp a1-4rd:~/a1-4rd/brain/alfred.py brain/
```

## From another network (Tailscale)

The server only accepts keys, and is on Tailscale as `a1-4rd`
([`ops/remote-access/install.sh`](../ops/remote-access/install.sh)). No router port is open: only devices signed
in to the same Tailscale account can reach it.

On the laptop, install Tailscale (`winget install --id Tailscale.Tailscale -e`), sign in with the same account,
and point the alias at the Tailscale name, keeping the LAN address as a fallback:

```
Host a1-4rd
    HostName a1-4rd
    User <user>
    IdentityFile ~/.ssh/a1-4rd
    IdentitiesOnly yes

Host a1-4rd-lan
    HostName xxx.xxx.xxx.xxx
    User <user>
    IdentityFile ~/.ssh/a1-4rd
    IdentitiesOnly yes
```

`listen.py` and `talk.py` use the `a1-4rd` alias, so they then work from any Wi-Fi unchanged. The Tailscale
name also survives the DHCP address changing. In the Tailscale admin page, disable key expiry for `a1-4rd`, or it
drops off the network after 180 days.
