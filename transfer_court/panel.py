"""Representation-agnostic Panel: the common meaning contract from
RepoWeaver's Experiment 0 design (shthnd/docs/plans/2026-08-31-repoweaver-
language-experiment-design.md, "Common Panel meaning contract"), not any one
candidate syntax (Stitchbook, compact prose, typed tuples). Whichever
representation Experiment 0 selects, its Decode output must fill these ten
fields before Transfer Court will accept it onto a docket.
"""
from pydantic import BaseModel, Field, model_validator


class Panel(BaseModel):
    capability: str = Field(..., min_length=1)
    applicability: list[str] = Field(..., min_length=1)
    evidence: list[str] = Field(..., min_length=1)
    actions: list[str] = Field(..., min_length=1)
    seams: list[str] = Field(..., min_length=1)
    bindings: dict[str, str] = Field(default_factory=dict)
    exclusions: list[str] = Field(default_factory=list)
    proofs: list[str] = Field(..., min_length=1)
    risks: list[str] = Field(..., min_length=1)
    hardening: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def bindings_require_exclusions(self) -> "Panel":
        if self.bindings and not self.exclusions:
            raise ValueError(
                "a Panel with target bindings must document exclusions "
                "(RepoWeaver design principle 6: target authority wins)"
            )
        return self
