"""Test collection synchronization against a local Anki sync server."""

import os
import pickle
import socket
import sqlite3
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from anki.collection import Collection
from typer import Abort

from apyanki.anki import Anki

PROFILE = "User 1"


@dataclass
class SyncServer:
    endpoint: str
    hkey: str
    root: Path


@pytest.fixture
def sync_server(tmp_path: Path) -> Iterator[SyncServer]:
    """Start a local Anki sync server with one user."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    log_path = tmp_path / "syncserver.log"
    env = {
        **os.environ,
        "SYNC_BASE": str(tmp_path / "server"),
        "SYNC_USER1": "user:pass",
        "SYNC_HOST": "127.0.0.1",
        "SYNC_PORT": str(port),
    }
    with log_path.open("w") as log:
        server = subprocess.Popen(
            [sys.executable, "-m", "anki.syncserver"],
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )

    try:
        deadline = time.monotonic() + 10
        while True:
            if server.poll() is not None:
                pytest.fail(f"Sync server exited:\n{log_path.read_text()}")
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.1).close()
                break
            except OSError:
                if time.monotonic() > deadline:
                    pytest.fail(f"Sync server did not start:\n{log_path.read_text()}")
                time.sleep(0.05)

        endpoint = f"http://127.0.0.1:{port}/"
        login_dir = tmp_path / "login"
        login_dir.mkdir()
        col = Collection(str(login_dir / "collection.anki2"))
        try:
            hkey = col.sync_login("user", "pass", endpoint).hkey
        finally:
            col.close()

        yield SyncServer(endpoint=endpoint, hkey=hkey, root=tmp_path)
    finally:
        server.terminate()
        server.wait(timeout=10)


def add_notes(col: Collection, prefix: str, count: int) -> None:
    model = col.models.by_name("Basic")
    deck_id = col.decks.id("Default")
    assert model is not None
    assert deck_id is not None
    for i in range(count):
        note = col.new_note(model)
        note["Front"] = f"{prefix} {i}"
        _ = col.add_note(note, deck_id)


def make_base(server: SyncServer, name: str, notes: int) -> Path:
    """Create an Anki base folder whose profile is logged in to the server."""
    base = server.root / name
    (base / PROFILE).mkdir(parents=True)

    col = Collection(str(base / PROFILE / "collection.anki2"))
    try:
        add_notes(col, name, notes)
    finally:
        col.close()

    profile = {"syncKey": server.hkey, "customSyncUrl": server.endpoint}
    conn = sqlite3.connect(base / "prefs21.db")
    try:
        _ = conn.execute(
            "create table profiles (name text primary key, data blob not null)"
        )
        _ = conn.executemany(
            "insert into profiles values (?, ?)",
            [
                ("_global", pickle.dumps({"last_loaded_profile_name": PROFILE})),
                (PROFILE, pickle.dumps(profile)),
            ],
        )
        conn.commit()
    finally:
        conn.close()

    return base


def note_fronts(base: Path) -> set[str]:
    col = Collection(str(base / PROFILE / "collection.anki2"))
    try:
        return {col.get_note(nid)["Front"] for nid in col.find_notes("")}
    finally:
        col.close()


def seed_server(server: SyncServer, notes: int) -> set[str]:
    """Upload a collection to the server and return its note fronts."""
    base = make_base(server, "seed", notes)
    fronts = note_fronts(base)
    col = Collection(str(base / PROFILE / "collection.anki2"))
    try:
        auth = col.sync_login("user", "pass", server.endpoint)
        col.close_for_full_sync()
        try:
            col.full_upload_or_download(auth=auth, server_usn=None, upload=True)
        finally:
            col.reopen(after_full_sync=True)
    finally:
        col.close()
    return fronts


def answer_prompts(monkeypatch: pytest.MonkeyPatch, answer: str | bool) -> None:
    monkeypatch.setattr(
        "apyanki.anki.console.confirm", lambda *_args, **_kwargs: answer
    )
    monkeypatch.setattr("apyanki.anki.console.prompt", lambda *_args, **_kwargs: answer)


def test_sync_downloads_into_new_collection(
    sync_server: SyncServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The scenario from issue #159: a new machine with an empty collection."""
    server_notes = seed_server(sync_server, 3)
    base = make_base(sync_server, "local", 0)
    answer_prompts(monkeypatch, True)

    with Anki(base_path=str(base)) as anki:
        anki.sync()

    assert note_fronts(base) == server_notes
    assert any((base / PROFILE / "backups").iterdir())


def test_sync_uploads_to_empty_server(
    sync_server: SyncServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = make_base(sync_server, "local", 3)
    local_notes = note_fronts(base)
    answer_prompts(monkeypatch, True)

    with Anki(base_path=str(base)) as anki:
        anki.sync()

    other = make_base(sync_server, "other", 0)
    with Anki(base_path=str(other)) as anki:
        anki.sync()

    assert note_fronts(other) == local_notes


def test_sync_conflict_can_be_cancelled(
    sync_server: SyncServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    server_notes = seed_server(sync_server, 3)
    base = make_base(sync_server, "local", 2)
    local_notes = note_fronts(base)
    answer_prompts(monkeypatch, "cancel")

    with pytest.raises(Abort), Anki(base_path=str(base)) as anki:
        anki.sync()

    assert note_fronts(base) == local_notes

    other = make_base(sync_server, "other", 0)
    answer_prompts(monkeypatch, True)
    with Anki(base_path=str(other)) as anki:
        anki.sync()

    assert note_fronts(other) == server_notes


def test_sync_conflict_can_download(
    sync_server: SyncServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    server_notes = seed_server(sync_server, 3)
    base = make_base(sync_server, "local", 2)
    answer_prompts(monkeypatch, "download")

    with Anki(base_path=str(base)) as anki:
        anki.sync()

    assert note_fronts(base) == server_notes
