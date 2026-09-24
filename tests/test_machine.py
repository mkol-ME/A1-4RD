import calendar
import json
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "brain"))
import machine  # noqa: E402

NOW = calendar.timegm(time.strptime("2026-09-24T12:00:00Z", "%Y-%m-%dT%H:%M:%SZ"))


def _write(entries):
    handle = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    for entry in entries:
        handle.write((entry if isinstance(entry, str) else json.dumps(entry)) + "\n")
    handle.close()
    return handle.name


class Alerts(unittest.TestCase):
    def setUp(self):
        self.saved = machine.ALERTS

    def tearDown(self):
        machine.ALERTS = self.saved

    def test_no_file_means_no_monitor(self):
        machine.ALERTS = os.path.join(tempfile.gettempdir(), "no-such-alerts.jsonl")
        self.assertIsNone(machine.alerts(NOW))

    def test_recent_real_alerts_newest_first(self):
        machine.ALERTS = _write([
            {"time": "2026-07-01T00:00:00Z", "message": "RAID Fail on /dev/md0 (/dev/sdc1)"},   # too old
            {"time": "2026-09-20T03:00:00Z", "message": "RAID TestMessage on /dev/md0", "test": True},
            {"time": "2026-09-21T05:00:00Z", "message": "Device: /dev/sda, 8 pending sectors"},
            "not json",
            {"time": "2026-09-23T04:00:00Z", "message": "RAID DegradedArray on /dev/md0"},
        ])
        self.assertEqual(machine.alerts(NOW), ["Sep 23: RAID DegradedArray on /dev/md0",
                                               "Sep 21: Device: /dev/sda, 8 pending sectors"])
        os.unlink(machine.ALERTS)

    def test_quiet_month_is_an_empty_list(self):
        machine.ALERTS = _write([{"time": "2026-09-20T03:00:00Z", "message": "test", "test": True}])
        self.assertEqual(machine.alerts(NOW), [])
        os.unlink(machine.ALERTS)


if __name__ == "__main__":
    unittest.main()
