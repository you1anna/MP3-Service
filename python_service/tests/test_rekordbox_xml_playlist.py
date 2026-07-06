"""Tests for the Rekordbox XML writer's playlist population.

Regression: register() added tracks to <COLLECTION> but never to a playlist,
so the "mp3service" playlist in Rekordbox stayed empty.
"""

import tempfile
import unittest
from pathlib import Path

from src.rekordbox_xml import RekordboxXMLWriter, PLAYLIST_NAME
from pyrekordbox.rbxml import RekordboxXml


def _make_audio(root: Path, name: str) -> Path:
    p = root / name
    p.write_bytes(b"ID3....audio")
    return p


def _playlist_track_ids(xml_path: Path) -> list[int]:
    xml = RekordboxXml(xml_path)
    for node in xml.get_playlist().get_playlists():
        if node.is_playlist and node.name == PLAYLIST_NAME:
            return [int(k) for k in node.get_tracks()]
    return []


class PlaylistPopulationTests(unittest.TestCase):
    def test_registered_track_is_added_to_playlist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            xml_path = root / "rb.xml"
            audio = _make_audio(root, "Artist - Song.aiff")

            writer = RekordboxXMLWriter(xml_path)
            writer.register(audio, "Artist", "Song", 120)

            # Track is in the collection...
            xml = RekordboxXml(xml_path)
            locations = [t["Location"] for t in xml.get_tracks()]
            self.assertEqual(len(locations), 1)
            track_id = int(xml.get_tracks()[0]["TrackID"])

            # ...and in the mp3service playlist.
            self.assertEqual(_playlist_track_ids(xml_path), [track_id])

    def test_backfills_preexisting_collection_track_into_playlist(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            xml_path = root / "rb.xml"
            old = _make_audio(root, "Old - Track.aiff")
            new = _make_audio(root, "New - Track.aiff")

            # Simulate an XML written by the OLD code: track in COLLECTION,
            # no playlist node at all.
            xml = RekordboxXml(name="MP3-Service", version="1.0.0", company="macmini")
            xml.add_track(str(old.resolve()), Name="Track", Artist="Old",
                          Kind="AIFF File", TrackID=1)
            xml.save(path=xml_path)
            self.assertEqual(_playlist_track_ids(xml_path), [])  # pre-condition

            # Registering a new track should also backfill the old one.
            writer = RekordboxXMLWriter(xml_path)
            writer.register(new, "New", "Track", 120)

            ids = sorted(_playlist_track_ids(xml_path))
            all_collection_ids = sorted(
                int(t["TrackID"]) for t in RekordboxXml(xml_path).get_tracks()
            )
            self.assertEqual(len(ids), 2)
            self.assertEqual(ids, all_collection_ids)

    def test_no_duplicate_playlist_on_repeated_registers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            xml_path = root / "rb.xml"
            a = _make_audio(root, "A - One.aiff")
            b = _make_audio(root, "B - Two.aiff")

            writer = RekordboxXMLWriter(xml_path)
            writer.register(a, "A", "One", 100)
            writer.register(b, "B", "Two", 110)
            writer.register(a, "A", "One", 100)  # idempotent re-register

            xml = RekordboxXml(xml_path)
            playlists = [
                n for n in xml.get_playlist().get_playlists()
                if n.is_playlist and n.name == PLAYLIST_NAME
            ]
            self.assertEqual(len(playlists), 1)          # exactly one playlist
            self.assertEqual(len(_playlist_track_ids(xml_path)), 2)  # no dup tracks


if __name__ == "__main__":
    unittest.main()
