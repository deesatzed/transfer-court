import pytest
from pydantic import ValidationError
from transfer_court.panel import Panel


def test_panel_requires_all_ten_meaning_contract_fields():
    with pytest.raises(ValidationError):
        Panel(capability="expose web actions as agent tools")


def test_panel_accepts_minimal_valid_instance():
    panel = Panel(
        capability="expose web actions as agent tools",
        applicability=["app has one shared action authority"],
        evidence=["ChordShapeLicks WebMCP contract tests, commit c17399c"],
        actions=["register tools inside route lifecycle"],
        seams=["TableRoute lifecycle"],
        bindings={"authority": "GameConnection"},
        exclusions=["guitar-domain vocabulary", "local-sync assumptions"],
        proofs=["cleanup", "fallback", "parity", "privacy", "headed"],
        risks=["ack != committed state"],
        hardening="locally proven, cross-repo candidate, not cross-repo hardened",
    )
    assert panel.capability == "expose web actions as agent tools"
    assert panel.bindings["authority"] == "GameConnection"


def test_panel_rejects_empty_exclusions_when_bindings_present():
    # Design principle 6 ("target authority wins") + the safety gate require
    # that anything bound to a target also documents what was excluded.
    with pytest.raises(ValidationError):
        Panel(
            capability="x",
            applicability=["y"],
            evidence=["z"],
            actions=["a"],
            seams=["b"],
            bindings={"authority": "GameConnection"},
            exclusions=[],
            proofs=["p"],
            risks=["r"],
            hardening="draft",
        )
