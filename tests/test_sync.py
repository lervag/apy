"""Test collection synchronization."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Self

import pytest
from anki.sync import SyncOutput
from click import Abort

from apyanki.anki import Anki
from apyanki.config import cfg


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


class RecordingProgress:
    """Minimal progress implementation that records its live state."""

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.running = False
        self.events: list[str] = []

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.stop()

    def add_task(self, *_args: Any, **_kwargs: Any) -> int:
        return 1

    def update(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def start(self) -> None:
        self.running = True
        self.events.append("start")

    def stop(self) -> None:
        self.running = False
        self.events.append("stop")


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
    monkeypatch.setattr("apyanki.anki.console.confirm", lambda *_args, **_kwargs: True)

    anki.sync()

    backup = ("backup", (str(tmp_path / "backups"), True, True))
    full_download = ("full", (False, None, "https://sync.example.test/"))
    assert backup in collection.operations
    assert full_download in collection.operations
    assert collection.operations.index(backup) < collection.operations.index(
        full_download
    )
    assert ("reopen", True) in collection.operations
    assert ("media", "https://sync.example.test/") in collection.operations


@pytest.mark.parametrize(
    ("profile", "message"),
    [(None, "profile"), ({"syncKey": ""}, "sync key")],
)
def test_explicit_sync_without_credentials_fails(
    capsys: pytest.CaptureFixture[str],
    profile: dict[str, str] | None,
    message: str,
) -> None:
    anki: Any = Anki.__new__(Anki)
    anki._profile = profile

    with pytest.raises(Abort):
        anki.sync()

    assert message in capsys.readouterr().out.lower()


def test_sync_uploads_when_only_full_upload_is_allowed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = SyncOutput(required=SyncOutput.FULL_UPLOAD)
    collection = FakeCollection(tmp_path, output)
    anki: Any = Anki.__new__(Anki)
    anki._profile = {"syncKey": "key"}
    anki.col = collection
    monkeypatch.setattr("apyanki.anki.console.confirm", lambda *_args, **_kwargs: True)

    anki.sync()

    assert ("full", (True, None, "")) in collection.operations
    assert not any(name == "backup" for name, _ in collection.operations)


def test_sync_conflict_can_be_cancelled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = SyncOutput(required=SyncOutput.FULL_SYNC)
    collection = FakeCollection(tmp_path, output)
    anki: Any = Anki.__new__(Anki)
    anki._profile = {"syncKey": "key"}
    anki.col = collection
    monkeypatch.setattr(
        "apyanki.anki.console.prompt", lambda *_args, **_kwargs: "cancel"
    )

    with pytest.raises(Abort):
        anki.sync()

    assert not any(name == "full" for name, _ in collection.operations)


@pytest.mark.parametrize(
    ("profile", "message"),
    [(None, "Anki profile"), ({"syncKey": ""}, "sync key")],
)
def test_auto_sync_without_credentials_warns_and_preserves_mutation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    profile: dict[str, str] | None,
    message: str,
) -> None:
    operations: list[str] = []
    anki: Any = Anki.__new__(Anki)
    anki.modified = True
    anki._profile = profile
    anki.col = SimpleNamespace(close=lambda: operations.append("close"))
    monkeypatch.setitem(cfg, "auto_sync", True)

    anki.__exit__(None, None, None)

    assert operations == ["close"]
    assert f"auto-sync skipped: no {message.lower()}" in capsys.readouterr().out.lower()


@pytest.mark.parametrize(
    ("required", "response", "upload"),
    [
        (SyncOutput.FULL_DOWNLOAD, "y", False),
        (SyncOutput.FULL_UPLOAD, "y", True),
        (SyncOutput.FULL_SYNC, "upload", True),
    ],
)
def test_full_sync_prompts_pause_live_progress(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    required: Any,
    response: str,
    upload: bool,
) -> None:
    collection = FakeCollection(tmp_path, SyncOutput(required=required))
    anki: Any = Anki.__new__(Anki)
    anki._profile = {"syncKey": "key"}
    anki.col = collection
    progress = RecordingProgress()
    prompt_states: list[bool] = []

    monkeypatch.setattr("apyanki.anki.Progress", lambda *_args, **_kwargs: progress)

    def respond(*_args: Any) -> str:
        prompt_states.append(progress.running)
        return response

    monkeypatch.setattr("builtins.input", respond)

    anki.sync()

    assert prompt_states == [False]
    assert progress.events == ["start", "stop", "start", "stop"]
    assert ("full", (upload, None, "")) in collection.operations


def test_full_sync_prompt_restarts_progress_after_exception(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    collection = FakeCollection(tmp_path, SyncOutput(required=SyncOutput.FULL_DOWNLOAD))
    anki: Any = Anki.__new__(Anki)
    anki._profile = {"syncKey": "key"}
    anki.col = collection
    progress = RecordingProgress()
    monkeypatch.setattr("apyanki.anki.Progress", lambda *_args, **_kwargs: progress)

    def fail_prompt(*_args: Any, **_kwargs: Any) -> bool:
        raise RuntimeError("prompt failed")

    monkeypatch.setattr("apyanki.anki.console.confirm", fail_prompt)

    with pytest.raises(RuntimeError, match="prompt failed"):
        anki.sync()

    assert progress.events == ["start", "stop", "start", "stop"]


def test_unexpected_normal_sync_response_fails_without_full_sync(
    tmp_path: Path,
) -> None:
    collection = FakeCollection(tmp_path, SyncOutput(required=SyncOutput.NORMAL_SYNC))
    anki: Any = Anki.__new__(Anki)
    anki._profile = {"syncKey": "key"}
    anki.col = collection

    with pytest.raises(Abort):
        anki.sync()

    assert not any(name == "full" for name, _ in collection.operations)


def test_backup_failure_prevents_full_download(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = SyncOutput(required=SyncOutput.FULL_DOWNLOAD)
    collection = FakeCollection(tmp_path, output)
    anki: Any = Anki.__new__(Anki)
    anki._profile = {"syncKey": "key"}
    anki.col = collection
    monkeypatch.setattr("apyanki.anki.console.confirm", lambda *_args, **_kwargs: True)

    def fail_backup(**_kwargs: Any) -> bool:
        collection.operations.append(("backup failed", None))
        raise RuntimeError("backup failed")

    monkeypatch.setattr(collection, "create_backup", fail_backup)

    with pytest.raises(RuntimeError, match="backup failed"):
        anki.sync()

    assert ("backup failed", None) in collection.operations
    assert not any(name == "full" for name, _ in collection.operations)


def test_failed_full_sync_reopens_collection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = SyncOutput(required=SyncOutput.FULL_UPLOAD)
    collection = FakeCollection(tmp_path, output)
    anki: Any = Anki.__new__(Anki)
    anki._profile = {"syncKey": "key"}
    anki.col = collection
    monkeypatch.setattr("apyanki.anki.console.confirm", lambda *_args, **_kwargs: True)

    def fail_full_sync(**_kwargs: Any) -> None:
        collection.operations.append(("full failed", None))
        raise RuntimeError("full sync failed")

    monkeypatch.setattr(collection, "full_upload_or_download", fail_full_sync)

    with pytest.raises(RuntimeError, match="full sync failed"):
        anki.sync()

    assert ("full failed", None) in collection.operations
    assert ("reopen", True) in collection.operations
