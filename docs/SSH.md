# SSH to the A1-4RD server

```
ssh a1-4rd
```

Uses the `a1-4rd` alias in `~/.ssh/config` (host `xxx.xxx.xxx.xxx`, user `<user>`, key `~/.ssh/a1-4rd`).
Key-based; no password is needed to log in. `sudo` still asks for one.

The address comes from the router's DHCP and is not reserved. If `ssh a1-4rd` stops connecting, find the
server by scanning the LAN for port 22, check that its ed25519 host key matches the known one, and update
`HostName` in `~/.ssh/config`. (xxx.xxx.xxx.xxx also answers on port 22 — it is an unrelated device.)

The project lives in `~/a1-4rd/` with the same layout as this repo, plus the git-ignored assets (venvs,
voice models, training data) at the top level.

Copy files back and forth:

```
scp persona/examples.md a1-4rd:~/a1-4rd/persona/
scp a1-4rd:~/a1-4rd/brain/alfred.py brain/
```
