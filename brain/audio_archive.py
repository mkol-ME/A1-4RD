"""Every utterance he hears, kept on the array with what Whisper made of it.

Transcripts are lossy and one-way: once a clip is gone, a better Whisper cannot
be run over it and there is nothing to learn a voice from. The array has
terabytes free and speech is small — an hour of 16 kHz mono is about 115 MB — so
the audio is kept and the transcript stored beside it.

What it is for: re-transcribing old conversations when the model improves, and
telling the user's voice from anyone else's in the room, which per-person memory
needs before it can be enforced (the user, 2026-09-17).

Nothing leaves the box. A cap on total size keeps it from ever filling the
array: when the archive grows past it, the oldest clips go first.
"""

import os
import sqlite3
import time
import wave
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_ROOT = Path("/srv/storage/alfred/audio")
CAP_BYTES = int(float(os.environ.get("ALFRED_AUDIO_CAP_GB", "100")) * 1024 ** 3)


def _wav_seconds(audio: bytes) -> float:
    try:
        import io
        with wave.open(io.BytesIO(audio), "rb") as handle:
            return handle.getnframes() / float(handle.getframerate() or 1)
    except Exception:
        return 0.0


class Archive:
    """Clips on disk, one row each in an index beside them.

    The index is its own database, not Alfred's memory: it is written on every
    utterance and read by later training runs, and it has no business competing
    for that file's write lock.
    """

    def __init__(self, root: Path | None = None, cap_bytes: int = CAP_BYTES):
        self.root = Path(root) if root is not None else DEFAULT_ROOT
        self.cap_bytes = cap_bytes
        self.db = None
        if not self.root.parent.is_dir():
            return                      # no array here: a checkout on the laptop
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / "index.sqlite3", check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS clips ("
            "id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL, "
            "seconds REAL NOT NULL, bytes INTEGER NOT NULL, language TEXT NOT NULL, "
            "source TEXT NOT NULL, text TEXT NOT NULL, speaker TEXT)")
        self.db.commit()

    @property
    def enabled(self) -> bool:
        return self.db is not None

    def keep(self, audio: bytes, text: str, language: str = "en", source: str = "voice") -> Path | None:
        """Write one clip and index it. Returns its path, or None when disabled."""
        if self.db is None or not audio:
            return None
        now = datetime.now(timezone.utc)
        folder = self.root / f"{now:%Y}" / f"{now:%m}" / f"{now:%d}"
        folder.mkdir(parents=True, exist_ok=True)
        # Milliseconds and a counter: two utterances can land in the same second.
        stem = f"{now:%H%M%S}-{now.microsecond // 1000:03d}"
        path = folder / f"{stem}.wav"
        count = 1
        while path.exists():
            path = folder / f"{stem}-{count}.wav"
            count += 1
        path.write_bytes(audio)
        self.db.execute(
            "INSERT INTO clips(path, created_at, seconds, bytes, language, source, text) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(path.relative_to(self.root)).replace("\\", "/"), now.isoformat(timespec="seconds"),
             round(_wav_seconds(audio), 2), len(audio), language, source, text))
        self.db.commit()
        self.prune()
        return path

    def total_bytes(self) -> int:
        if self.db is None:
            return 0
        return self.db.execute("SELECT COALESCE(SUM(bytes), 0) FROM clips").fetchone()[0]

    def prune(self) -> int:
        """Drop the oldest clips until the archive fits under the cap. Returns how many went."""
        if self.db is None:
            return 0
        total = self.total_bytes()
        if total <= self.cap_bytes:
            return 0
        removed = 0
        for clip_id, relative, size in self.db.execute(
                "SELECT id, path, bytes FROM clips ORDER BY id").fetchall():
            if total <= self.cap_bytes:
                break
            (self.root / relative).unlink(missing_ok=True)
            self.db.execute("DELETE FROM clips WHERE id = ?", (clip_id,))
            total -= size
            removed += 1
        self.db.commit()
        return removed

    def stats(self) -> dict:
        if self.db is None:
            return {"enabled": False}
        clips, seconds, size = self.db.execute(
            "SELECT COUNT(*), COALESCE(SUM(seconds), 0), COALESCE(SUM(bytes), 0) FROM clips").fetchone()
        return {"enabled": True, "clips": clips, "hours": round(seconds / 3600, 2),
                "gigabytes": round(size / 1024 ** 3, 3), "cap_gigabytes": round(self.cap_bytes / 1024 ** 3, 1)}

    def close(self) -> None:
        if self.db is not None:
            self.db.close()
            self.db = None


if __name__ == "__main__":
    import json
    print(json.dumps(Archive().stats(), indent=2))
