"""Consolidate only explicit conflict identities or exact claim/evidence matches."""
import json

from app.models.program_assessment import ChallengeProvenance, GovernanceChallenge
from app.services.evidence_adapters import stable_id


def consolidate_challenges(challenges: list[GovernanceChallenge]) -> list[GovernanceChallenge]:
    groups: dict[str, list[GovernanceChallenge]] = {}
    for challenge in challenges:
        # No fuzzy paraphrase matching: distinct numeric claims or counterpart
        # evidence remain different unless a deterministic policy supplies a key.
        key = challenge.conflict_key or json.dumps([
            " ".join(challenge.reported_claim.casefold().split()),
            " ".join(challenge.reason.casefold().split()),
            sorted(challenge.supporting_evidence_ids),
        ])
        groups.setdefault(key, []).append(challenge)
    result = []
    for key, items in groups.items():
        provenance = {}
        for item in items:
            originals = item.provenance or [ChallengeProvenance.model_validate(
                item.model_dump(exclude={"conflict_key", "provenance"}))]
            for original in originals:
                provenance[original.model_dump_json()] = original
        originals = sorted(provenance.values(), key=lambda p: (p.challenge_id, p.reported_source))
        # Prefer the explicit numeric policy explanation over a generic narrative
        # contradiction, while keeping every original explanation in provenance.
        representative = sorted(items, key=lambda item: (
            "structured quality data records" not in item.reason, item.challenge_id))[0]
        merged = representative.model_copy(update={
            "challenge_id": stable_id("CH", key) if len(originals) > 1 else representative.challenge_id,
            "claim_evidence_ids": sorted({identifier for p in originals for identifier in p.claim_evidence_ids}),
            "supporting_evidence_ids": sorted({identifier for p in originals for identifier in p.supporting_evidence_ids}),
            "severity": "RED" if any(p.severity == "RED" for p in originals) else "AMBER",
            "assessment": "CHALLENGED" if any(p.assessment == "CHALLENGED" for p in originals) else "REQUIRES_VALIDATION",
            "provenance": originals,
        })
        result.append(merged)
    return sorted(result, key=lambda c: (c.severity != "RED", c.challenge_id))
