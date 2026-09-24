import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "brain"))

import spotify


def fake_api(responses):
    """_call stand-in: answers by (method, path) and records what was asked."""
    calls = []

    def call(method, path, params=None, body=None, retry=True):
        calls.append((method, path, params, body))
        return responses.get((method, path), {})
    return call, calls


ARTIST = {"name": "Drake", "uri": "spotify:artist:1"}
TRACK = {"name": "Hotline Bling", "uri": "spotify:track:2", "artists": [{"name": "Drake"}]}


class FindTests(unittest.TestCase):
    def setUp(self):
        self.saved = spotify._call

    def tearDown(self):
        spotify._call = self.saved

    def test_an_artist_by_name_plays_the_artist(self):
        spotify._call, _ = fake_api({("GET", "/search"): {"artists": {"items": [ARTIST]}, "tracks": {"items": [TRACK]}}})
        self.assertEqual(spotify.find("drake"), {"title": "Drake", "context": "spotify:artist:1", "shuffle": True})

    def test_a_song_plays_the_song(self):
        spotify._call, _ = fake_api({("GET", "/search"): {"artists": {"items": [ARTIST]}, "tracks": {"items": [TRACK]}}})
        self.assertEqual(spotify.find("hotline bling"),
                         {"title": "Hotline Bling by Drake", "uris": ["spotify:track:2"]})

    def test_song_by_artist_searches_both_fields(self):
        spotify._call, calls = fake_api({("GET", "/search"): {"tracks": {"items": [TRACK]}}})
        spotify.find("hotline bling by drake")
        self.assertEqual(calls[0][2]["q"], "track:hotline bling artist:drake")

    def test_his_own_playlist_first(self):
        spotify._call, calls = fake_api({("GET", "/me/playlists"): {"items": [{"name": "Gym", "uri": "spotify:playlist:9"}]}})
        self.assertEqual(spotify.find("my gym playlist"), {"title": "Gym", "context": "spotify:playlist:9"})
        self.assertNotIn("/search", [c[1] for c in calls])

    def test_liked_songs(self):
        spotify._call, _ = fake_api({("GET", "/me/tracks"): {"items": [{"track": TRACK}]}})
        self.assertEqual(spotify.find("my liked songs")["uris"], ["spotify:track:2"])

    def test_only_spotify_has_his_library(self):
        self.assertTrue(spotify.wants_spotify("my liked songs"))
        self.assertTrue(spotify.wants_spotify("my gym playlist"))
        self.assertFalse(spotify.wants_spotify("drake"))
        self.assertFalse(spotify.wants_spotify("lofi playlist"))

    def test_nothing_found(self):
        spotify._call, _ = fake_api({})
        with self.assertRaises(spotify.SpotifyError) as caught:
            spotify.find("zzzz")
        self.assertEqual(caught.exception.code, "no_match")


class DeviceTests(unittest.TestCase):
    def test_active_then_computer_then_anything(self):
        phone = {"id": "p", "type": "Smartphone"}
        laptop = {"id": "l", "type": "Computer"}
        self.assertIs(spotify.pick_device([phone, dict(laptop, is_active=False)])["id"] == "l", True)
        self.assertEqual(spotify.pick_device([laptop, dict(phone, is_active=True)])["id"], "p")
        self.assertEqual(spotify.pick_device([phone])["id"], "p")
        self.assertIsNone(spotify.pick_device([dict(phone, is_restricted=True)]))


if __name__ == "__main__":
    unittest.main()
