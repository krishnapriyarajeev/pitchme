from types import SimpleNamespace

from ai.rehearsal.transcript import CallTurn, Transcript, to_lines, turn_from_message

START = 1_000.0


def message(role, text, created_at, metrics=None, interrupted=False):
    return SimpleNamespace(
        role=role,
        text_content=text,
        created_at=created_at,
        metrics=metrics or {},
        interrupted=interrupted,
    )


def test_spoken_turn_uses_speech_timing():
    turn = turn_from_message(
        role="user",
        text=" Hi Jo, thanks for the time. ",
        created_at=START + 9,
        metrics={"started_speaking_at": START + 4.2, "stopped_speaking_at": START + 7.5},
        interrupted=False,
        call_start=START,
    )
    assert turn == CallTurn("seller", "Hi Jo, thanks for the time.", 4200, 7500)


def test_typed_turn_sits_at_the_moment_it_was_added():
    turn = turn_from_message(
        role="assistant", text="Go on.", created_at=START + 2, metrics={}, interrupted=True,
        call_start=START,
    )  # fmt: skip
    assert turn == CallTurn("buyer", "Go on.", 2000, 2000, interrupted=True)


def test_system_and_empty_messages_are_dropped():
    for role, text in [("system", "You are Jo"), ("user", "  "), ("assistant", None)]:
        assert turn_from_message(
            role=role, text=text, created_at=START, metrics={}, interrupted=False, call_start=START
        ) is None  # fmt: skip


def test_times_before_the_call_clamp_to_zero():
    turn = turn_from_message(
        role="assistant", text="Hello?", created_at=START - 1, metrics={}, interrupted=False,
        call_start=START,
    )  # fmt: skip
    assert (turn.start_ms, turn.end_ms) == (0, 0)


def test_turns_are_ordered_by_when_they_were_spoken():
    transcript = Transcript(START)
    transcript.add(message("assistant", "Yes, who is this?", START + 1,
                           {"started_speaking_at": START + 0.5, "stopped_speaking_at": START + 1.5}))  # fmt: skip
    # Answer arrives before the seller's turn is transcribed.
    transcript.add(message("assistant", "Sure, go ahead.", START + 6,
                           {"started_speaking_at": START + 6, "stopped_speaking_at": START + 7}))  # fmt: skip
    transcript.add(message("user", "Sam from PitchMe.", START + 6.5,
                           {"started_speaking_at": START + 2, "stopped_speaking_at": START + 4}))  # fmt: skip
    transcript.add(message("system", "ignored", START))
    assert [t.role for t in transcript.turns] == ["buyer", "seller", "buyer"]
    assert transcript.turns[1].to_dict() == {
        "role": "seller", "text": "Sam from PitchMe.", "start_ms": 2000, "end_ms": 4000,
        "interrupted": False,
    }  # fmt: skip


def test_content_lines_call_the_seller_the_agent():
    lines = to_lines([CallTurn("seller", "Hi", 0, 500), CallTurn("buyer", "Hello", 600, 900)])
    assert [(line.role, line.start_ms) for line in lines] == [("agent", 0), ("customer", 600)]
