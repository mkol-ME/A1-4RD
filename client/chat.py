#!/usr/bin/env python3
"""Type to Alfred and read his answers, with no microphone and no speakers.

The same turn as a spoken one - the same memory, lookups and tools - sent with
the voice left out, so the server skips synthesis and answers in text frames.
Only the standard library: it needs no audio stack and starts in about the time
the SSH tunnel takes.

Runs beside the voice client rather than instead of it. The tunnel forwards a
free local port of its own, so neither holds the other's.
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

REMOTE = "a1-4rd"
REMOTE_PORT = 5051

DIM = "\033[2m"
BOLD = "\033[1m"
RED = "\033[31m"
RESET = "\033[0m"


def pending(wait: float = 0.05) -> bool:
    """Whether more input is already waiting: the rest of a paste arrives at once,
    where a person typing takes far longer than this to start another line."""
    deadline = time.monotonic() + wait
    while True:
        if os.name == "nt":
            import msvcrt
            if msvcrt.kbhit():
                return True
        else:
            import select
            if select.select([sys.stdin], [], [], 0)[0]:
                return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.01)


def read_prompt(marker: str) -> str:
    """One turn's text. A pasted block is one message: pasted a page of eleven
    lines, he got eleven turns, and one of those scraps was saved to memory as a
    fact about him."""
    lines = [input(marker)]
    while pending():
        lines.append(input())
    return "\n".join(lines).strip()


def enable_colour() -> bool:
    """Turn on ANSI escapes in a Windows console; say whether they are safe to use."""
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return False
    if os.name != "nt":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except (AttributeError, OSError):
        return False


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def open_tunnel(remote: str, port: int, wait: float = 45.0) -> subprocess.Popen:
    tunnel = subprocess.Popen(
        ["ssh", "-N", "-o", "ExitOnForwardFailure=yes",
         "-L", f"{port}:127.0.0.1:{REMOTE_PORT}", remote],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        if tunnel.poll() is not None:
            detail = (tunnel.stderr.read() or "").strip()
            raise RuntimeError(f"ssh {remote} failed" + (f": {detail}" if detail else ""))
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
                if response.status == 200:
                    return tunnel
        except (OSError, urllib.error.URLError):
            time.sleep(0.3)
    tunnel.terminate()
    raise RuntimeError(f"Alfred's service on {remote} did not answer within {wait:.0f}s")


class Screen:
    """Lays reply frames out as they arrive.

    Ordinary sentences run on as one paragraph, the way he would say them. A
    reply given as written - a list read out in order - puts each sentence on a
    line of its own. Holding lines are status, not answer, so they are dimmed.
    """

    LABEL = "Alfred: "
    INDENT = " " * len(LABEL)

    def __init__(self, write, colour: bool = False):
        self.write = write
        self.colour = colour
        self.open = False       # a paragraph is on screen without its newline yet
        self.spoke = False      # the label has been printed this turn

    def _style(self, text: str, style: str) -> str:
        return f"{style}{text}{RESET}" if self.colour else text

    def _close(self) -> None:
        if self.open:
            self.write("\n")
            self.open = False

    def _lead(self) -> str:
        if self.spoke:
            return self.INDENT
        self.spoke = True
        return self._style(self.LABEL.rstrip(), BOLD) + " "

    def show(self, frame: dict) -> None:
        if "holding" in frame:
            self._close()
            self.write(self._style(f"({frame['holding']})", DIM) + "\n")
        elif "media" in frame:
            # Nothing plays here; the link is the part a screen can use.
            media = frame["media"]
            link = f"https://youtu.be/{media['id']}" if media.get("id") else ""
            if link and media.get("start"):
                link += f"?t={int(media['start'])}"
            self._close()
            line = f"{self.INDENT}> {media.get('title') or 'video'}  {link}".rstrip()
            self.write(self._style(line, DIM) + "\n")
        elif "text" in frame:
            if frame.get("line"):
                self._close()
                self.write(self._lead() + frame["text"] + "\n")
            elif self.open:
                self.write(" " + frame["text"])
            else:
                self.write(self._lead() + frame["text"])
                self.open = True

    def finish(self) -> None:
        self._close()
        self.spoke = False


def ask(url: str, prompt: str, screen: Screen, timeout: float = 300) -> float:
    """One turn. Returns the seconds until the first sentence arrived."""
    request = urllib.request.Request(
        f"{url}/chat",
        data=json.dumps({"text": prompt, "language": "en", "voice": False}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    first = None
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            for raw in response:
                frame = json.loads(raw)
                if frame.get("done"):
                    break
                if "error" in frame:
                    raise RuntimeError(frame["error"])
                if first is None and "text" in frame:
                    first = time.perf_counter() - started
                screen.show(frame)
    finally:
        screen.finish()
    return first or 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("prompt", nargs="*", help="ask this one thing, print the answer and exit")
    parser.add_argument("--remote", default=REMOTE, help="ssh host running the voice service")
    parser.add_argument("--url", help="use an already-reachable service (e.g. http://127.0.0.1:5061) "
                                      "instead of opening a tunnel")
    parser.add_argument("--timing", action="store_true", help="print seconds to first sentence")
    args = parser.parse_args()

    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    colour = enable_colour()
    screen = Screen(lambda text: (sys.stdout.write(text), sys.stdout.flush()), colour)

    def complain(message: str) -> None:
        print(f"{RED}{message}{RESET}" if colour else message, file=sys.stderr)

    one_shot = " ".join(args.prompt).strip()
    tunnel = None
    if args.url:
        url = args.url.rstrip("/")
    else:
        if not one_shot:
            print(f"Connecting to {args.remote}...", flush=True)
        port = free_port()
        try:
            tunnel = open_tunnel(args.remote, port)
        except RuntimeError as exc:
            complain(str(exc))
            return 1
        url = f"http://127.0.0.1:{port}"

    def turn(prompt: str) -> bool:
        try:
            first = ask(url, prompt, screen)
        except (OSError, urllib.error.URLError, RuntimeError, ValueError) as exc:
            complain(f"That turn failed: {exc}")
            return False
        if args.timing:
            print(f"{DIM}[first sentence {first:.2f}s]{RESET}" if colour else f"[first sentence {first:.2f}s]")
        return True

    try:
        if one_shot:
            return 0 if turn(one_shot) else 1
        print("Type to Alfred. /quit or Ctrl+C to leave.\n")
        while True:
            try:
                prompt = read_prompt(f"{BOLD}>{RESET} " if colour else "> ")
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if prompt.lower() in ("/quit", "/exit", "/q"):
                return 0
            if prompt:
                try:
                    turn(prompt)
                except KeyboardInterrupt:
                    # Stops reading this answer; the server still finishes the turn.
                    screen.finish()
                    print()
                print()
    finally:
        if tunnel is not None:
            tunnel.terminate()


if __name__ == "__main__":
    sys.exit(main())
