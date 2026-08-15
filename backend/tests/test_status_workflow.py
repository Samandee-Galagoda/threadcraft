import pytest

from app.services.orders import InvalidStatusTransition, next_valid_statuses, validate_transition

ALL_STATUSES = ["received", "fabric_cut", "stitching", "qc", "dispatched", "cancelled"]


@pytest.mark.parametrize(
    "current,target",
    [
        ("received", "fabric_cut"),
        ("fabric_cut", "stitching"),
        ("stitching", "qc"),
        ("qc", "dispatched"),
        ("received", "cancelled"),
        ("fabric_cut", "cancelled"),
        ("stitching", "cancelled"),
        ("qc", "cancelled"),
    ],
)
def test_valid_transitions_do_not_raise(current, target):
    validate_transition(current, target)  # should not raise


@pytest.mark.parametrize(
    "current,target",
    [
        ("received", "stitching"),  # skips a stage
        ("received", "qc"),
        ("received", "dispatched"),
        ("fabric_cut", "dispatched"),  # the exact bug found during manual testing
        ("stitching", "received"),  # backwards
        ("qc", "fabric_cut"),  # backwards
        ("dispatched", "received"),  # terminal -> anything
        ("dispatched", "cancelled"),  # terminal -> anything
        ("cancelled", "received"),  # terminal -> anything
        ("cancelled", "fabric_cut"),
    ],
)
def test_invalid_transitions_raise(current, target):
    with pytest.raises(InvalidStatusTransition):
        validate_transition(current, target)


def test_terminal_states_have_no_next_statuses():
    assert next_valid_statuses("dispatched") == []
    assert next_valid_statuses("cancelled") == []


def test_every_non_terminal_status_can_reach_cancelled():
    for status in ["received", "fabric_cut", "stitching", "qc"]:
        assert "cancelled" in next_valid_statuses(status)
