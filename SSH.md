# SSH to the A1-4RD dev box

```
ssh a1-4rd
```

Uses the `a1-4rd` alias in `~/.ssh/config` (host `xxx.xxx.xxx.xxx`, user `<user>`,
key `~/.ssh/a1-4rd`). Key-based, no password needed.

Project files: `~/a1-4rd/` (`alfred.py`, `alfred.md`, `examples.md`, `Modelfile`).

Copy files back and forth:

```
scp alfred.md a1-4rd:~/a1-4rd/
scp a1-4rd:~/a1-4rd/examples.md .
```

