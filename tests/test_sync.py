"""Test collection synchronization."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from anki.sync import SyncOutput
from click import Abort

from apyanki.anki import Anki
from apyanki.config import cfg
from apyanki.console import console


class FakeCollection:
    """Record sync operations without contacting AnkiWeb."""

    def __init__(self, media_dir: Path, output: SyncOutput) -> None:
        self.media = SimpleNamespace(dir=lambda: str(media_dir))
        self.path = str(media_dir / "collection.anki2")
        self.output = output
        self.operations: list[tuple[str, Any]] = []

    def create_backup(
        self, *, backup_folder: str, force: bool, wait_for_completion: bool
    ) -> bool:
        self.operations.append(("backup", (backup_folder, force, wait_for_completion)))
        return True

    def sync_collection(self, auth: Any, sync_media: bool) -> SyncOutput:
        self.operations.append(("normal", sync_media))
        return self.output

    def close_for_full_sync(self) -> None:
        self.operations.append(("close", None))

    def full_upload_or_download(
        self, *, auth: Any, server_usn: int | None, upload: bool
    ) -> None:
        self.operations.append(("full", (upload, server_usn, auth.endpoint)))

    def reopen(self, after_full_sync: bool = False) -> None:
        self.operations.append(("reopen", after_full_sync))

    def sync_media(self, auth: Any) -> None:
        self.operations.append(("media", auth.endpoint))

    def media_sync_status(self) -> SimpleNamespace:
        return SimpleNamespace(active=False, progress=None)


def test_sync_downloads_when_server_requires_full_download(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = SyncOutput(
        required=SyncOutput.FULL_DOWNLOAD,
        new_endpoint="https://sync.example.test/",
        server_media_usn=42,
    )
    collection = FakeCollection(tmp_path, output)
    anki: Any = Anki.__new__(Anki)
    anki._profile = {"syncKey": "key"}
    anki.col = collection

    monkeypatch.setattr(console, "confirm", lambda *_args, **_kwargs: True)

    anki.sync()

    assert collection.operations == [
        ("normal", True),
        ("backup", (str(tmp_path / "backups"), True, True)),
        ("close", None),
        ("full", (False, None, "https://sync.example.test/")),
        ("reopen", True),
        ("media", "https://sync.example.test/"),
    ]


def test_sync_without_key_fails_instead_of_reporting_success(
    capsys: pytest.CaptureFixture[str],
) -> None:
    anki: Any = Anki.__new__(Anki)
    anki._profile = {"syncKey": ""}

    with pytest.raises(Abort):
        anki.sync()

    assert "sync key" in capsys.readouterr().out.lower()


def test_sync_uploads_when_only_full_upload_is_allowed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = SyncOutput(required=SyncOutput.FULL_UPLOAD)
    collection = FakeCollection(tmp_path, output)
    anki: Any = Anki.__new__(Anki)
    anki._profile = {"syncKey": "key"}
    anki.col = collection

    monkeypatch.setattr(console, "confirm", lambda *_args, **_kwargs: True)

    anki.sync()

    assert ("full", (True, None, "")) in collection.operations
    assert all(operation != "backup" for operation, _ in collection.operations)


def test_sync_conflict_can_be_cancelled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = SyncOutput(required=SyncOutput.FULL_SYNC)
    collection = FakeCollection(tmp_path, output)
    anki: Any = Anki.__new__(Anki)
    anki._profile = {"syncKey": "key"}
    anki.col = collection

    monkeypatch.setattr(console, "prompt", lambda *_args, **_kwargs: "cancel")

    with pytest.raises(Abort):
        anki.sync()

    assert collection.operations == [("normal", True)]


def test_context_manager_closes_collection_when_auto_sync_has_no_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operations: list[str] = []
    anki: Any = Anki.__new__(Anki)
    anki.modified = True
    anki._profile = {"syncKey": ""}
    anki.col = SimpleNamespace(close=lambda: operations.append("close"))
    monkeypatch.setitem(cfg, "auto_sync", True)

    with pytest.raises(Abort):
        anki.__exit__(None, None, None)

    assert operations == ["close"]


def test_backup_failure_prevents_full_download(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = SyncOutput(required=SyncOutput.FULL_DOWNLOAD)
    collection = FakeCollection(tmp_path, output)
    anki: Any = Anki.__new__(Anki)
    anki._profile = {"syncKey": "key"}
    anki.col = collection

    monkeypatch.setattr(console, "confirm", lambda *_args, **_kwargs: True)

    def fail_backup(**_kwargs: Any) -> bool:
        collection.operations.append(("backup failed", None))
        raise RuntimeError("backup failed")

    monkeypatch.setattr(collection, "create_backup", fail_backup)

    with pytest.raises(RuntimeError, match="backup failed"):
        anki.sync()

    assert collection.operations == [
        ("normal", True),
        ("backup failed", None),
    ]


def test_failed_full_sync_reopens_collection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = SyncOutput(required=SyncOutput.FULL_UPLOAD)
    collection = FakeCollection(tmp_path, output)
    anki: Any = Anki.__new__(Anki)
    anki._profile = {"syncKey": "key"}
    anki.col = collection

    monkeypatch.setattr(console, "confirm", lambda *_args, **_kwargs: True)

    def fail_full_sync(**_kwargs: Any) -> None:
        collection.operations.append(("full failed", None))
        raise RuntimeError("full sync failed")

    monkeypatch.setattr(collection, "full_upload_or_download", fail_full_sync)

    with pytest.raises(RuntimeError, match="full sync failed"):
        anki.sync()

    assert collection.operations == [
        ("normal", True),
        ("close", None),
        ("full failed", None),
        ("reopen", True),
    ]
