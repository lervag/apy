"""Test batch editing"""

import os
import pytest

from common import testDir, AnkiSimple, collection
from apyanki.anki import Anki

pytestmark = pytest.mark.filterwarnings("ignore")


def test_change_tags():
    """Test empty collection"""
    with AnkiSimple() as a:
        a.add_notes_from_file(testDir + "/" + "data/deck.md")

        query = "tag:test"
        n_original = len(list(a.find_notes(query)))

        a.change_tags(query, "testendret")
        assert len(list(a.find_notes("tag:testendret"))) == n_original

        a.change_tags(query, "test", add=False)
        assert len(list(a.find_notes(query))) == 0


def test_add_from_file(collection):
    """Test adding a note from a Markdown file."""
    with open("test.md", "w") as f:
        f.write(
            """model: Basic
tags: marked

# Note 1
## Front
Question?

## Back
Answer.
"""
        )

    with Anki(collection_db_path=collection) as a:
        # Add note
        note = a.add_notes_from_file("test.md")[0]
        assert note.n is not None
        assert note.model_name == "Basic"
        assert note.n.tags == ["marked"]
        assert "Question?" in note.n.fields[0]
        assert "Answer." in note.n.fields[1]

    # Clean up
    os.remove("test.md")


def test_update_from_file(collection):
    """Test updating a note from a Markdown file."""
    # First create a note
    with open("test.md", "w") as f:
        f.write(
            """model: Basic
tags: marked

# Note 1
## Front
Original question?

## Back
Original answer.
"""
        )

    with Anki(collection_db_path=collection) as a:
        # Add initial note
        note = a.add_notes_from_file("test.md")[0]
        note_id = note.n.id

        # Now create update file with the note ID
        with open("test_update.md", "w") as f:
            f.write(
                f"""model: Basic
tags: marked updated
nid: {note_id}

# Note 1
## Front
Updated question?

## Back
Updated answer.
"""
            )

        # Update the note
        updated_note = a.update_notes_from_file("test_update.md")[0]

        # Verify it's the same note but updated
        assert updated_note.n.id == note_id
        assert updated_note.model_name == "Basic"
        assert sorted(updated_note.n.tags) == ["marked", "updated"]
        assert "Updated question?" in updated_note.n.fields[0]
        assert "Updated answer." in updated_note.n.fields[1]

    # Clean up
    os.remove("test.md")
    os.remove("test_update.md")


def test_update_from_file_by_cid(collection):
    """Test updating a note from a Markdown file using card ID."""
    # First create a note
    with open("test.md", "w") as f:
        f.write(
            """model: Basic
tags: marked

# Note 1
## Front
Original question?

## Back
Original answer.
"""
        )

    with Anki(collection_db_path=collection) as a:
        # Add initial note
        note = a.add_notes_from_file("test.md")[0]
        card_id = note.n.cards()[0].id

        # Now create update file with the card ID
        with open("test_update_cid.md", "w") as f:
            f.write(
                f"""model: Basic
tags: marked card-updated
cid: {card_id}

# Note 1
## Front
Updated by card ID!

## Back
Updated answer via card ID.
"""
            )

        # Update the note
        updated_note = a.update_notes_from_file("test_update_cid.md")[0]

        # Verify it's the same note but updated
        assert updated_note.n.id == note.n.id
        assert sorted(updated_note.n.tags) == ["card-updated", "marked"]
        assert "Updated by card ID!" in updated_note.n.fields[0]
        assert "Updated answer via card ID." in updated_note.n.fields[1]

    # Clean up
    os.remove("test.md")
    os.remove("test_update_cid.md")


def test_update_from_file_new_and_existing(collection):
    """Test updating a file with both new and existing notes."""
    # First create a note
    with open("test.md", "w") as f:
        f.write(
            """model: Basic
tags: marked

# Note 1
## Front
Original question?

## Back
Original answer.
"""
        )

    with Anki(collection_db_path=collection) as a:
        # Add initial note
        note = a.add_notes_from_file("test.md")[0]
        note_id = note.n.id

        # Now create update file with both the existing note and a new note
        with open("test_mixed.md", "w") as f:
            f.write(
                f"""model: Basic
tags: common-tag

# Existing Note
nid: {note_id}
tags: existing-updated

## Front
Updated existing note.

## Back
Updated content.

# New Note
tags: new-note

## Front
This is a new note.

## Back
Brand new content.
"""
            )

        # Update the note
        updated_notes = a.update_notes_from_file("test_mixed.md")

        # Verify we have two notes
        assert len(updated_notes) == 2

        # Find the existing and new notes
        existing_note = next((n for n in updated_notes if n.n.id == note_id), None)
        new_note = next((n for n in updated_notes if n.n.id != note_id), None)

        # Verify existing note was updated
        assert existing_note is not None
        assert sorted(existing_note.n.tags) == ["common-tag", "existing-updated"]
        assert "Updated existing note." in existing_note.n.fields[0]
        assert "Updated content." in existing_note.n.fields[1]

        # Verify new note was created
        assert new_note is not None
        assert sorted(new_note.n.tags) == ["common-tag", "new-note"]
        assert "This is a new note." in new_note.n.fields[0]
        assert "Brand new content." in new_note.n.fields[1]

    # Clean up
    os.remove("test.md")
    os.remove("test_mixed.md")
