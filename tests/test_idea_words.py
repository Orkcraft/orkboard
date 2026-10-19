"""realm/idea_words.py: the words New idea completes with."""
from __future__ import annotations

from orkboard.realm import idea_words


def test_titles_first_then_words_by_use_in_any_script_names_of_code_kept_common_words_left_out():
    got = idea_words.words(["Офлайн режим для телефона: офлайн очередь. Также нужно чтобы SyncQueue и sync_queue.py работали.",
                            "Offline mode keeps the edits; offline first."], ["Офлайн режим", "Offline mode"])
    assert got[:2] == ["Офлайн режим", "Offline mode"]
    assert got[2:4] == ["offline", "офлайн"]                      # twice each; a tie is written in lower case
    assert {"SyncQueue", "sync_queue.py", "очередь", "телефона"} <= set(got)
    assert not {"также", "нужно", "чтобы", "the", "для", "и"} & {w.lower() for w in got}


def test_the_same_word_is_one_written_as_most_and_a_long_title_is_not_a_phrase():
    got = idea_words.words(["Sync sync sync Sync"], ["x" * 61, "Sync"])
    assert got == ["Sync"]                                         # the title already says it
    assert idea_words.words(["sync Sync Sync"]) == ["Sync"]
