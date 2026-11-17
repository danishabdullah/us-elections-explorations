"""Validated records. Everything that enters the database passes through one of these."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from midterms.seats import STATES

Office = Literal["sen", "pres", "house", "gov"]
Stage = Literal["gen", "runoff", "pri"]


class _Base(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)


class Source(_Base):
    source_id: str
    kind: Literal["dataset", "web", "document", "derived"]
    publisher: str
    title: str
    url: str | None = None
    retrieved_at: str | None = None
    sha256: str | None = None
    raw_path: str | None = None
    notes: str = ""


class Contest(_Base):
    office: Office
    state: str
    year: int = Field(ge=1976, le=2100)
    stage: Stage = "gen"
    special: bool = False
    district: str | None = None
    seat_id: str | None = None
    seat_method: Literal["calendar", "override"] | None = None
    notes: str = ""

    @model_validator(mode="after")
    def _check(self) -> Contest:
        if self.state not in STATES and not (self.state == "DC" and self.office != "sen"):
            raise ValueError(f"unknown state {self.state!r} for office {self.office}")
        if (self.office == "sen") != (self.seat_id is not None):
            raise ValueError("Senate contests need a seat_id; other offices must not have one")
        if (self.office == "house") != (self.district is not None):
            raise ValueError("House contests need a district; other offices must not have one")
        return self

    @property
    def contest_id(self) -> str:
        parts = [str(self.year), self.office, self.state]
        if self.seat_id:
            parts.append(self.seat_id.split("-")[1])
        if self.district:
            parts.append(self.district)
        if self.special:
            parts.append("special")
        parts.append(self.stage)
        return "-".join(parts)


class ResultRow(_Base):
    contest_id: str
    collection: str
    source_id: str
    candidate: str
    party: str = ""
    party_simplified: str = ""
    writein: bool = False
    votes: int = Field(ge=0)
    round: int = Field(default=1, ge=1)
    status: Literal["official", "certified", "unofficial"] = "official"
    as_of: str = ""


class Total(_Base):
    contest_id: str
    collection: str
    source_id: str
    round: int = Field(default=1, ge=1)
    total_votes: int = Field(gt=0)
    notes: str = ""
