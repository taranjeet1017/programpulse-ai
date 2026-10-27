"""Associate events, retaining individual records, claims and all provenance."""
from app.models.normalized_evidence import ConsolidatedEvidence, EvidenceGroup, NormalizedEvidence, SourceType
from app.services.evidence_adapters import event_key, stable_id


def consolidate(evidence: list[NormalizedEvidence]) -> ConsolidatedEvidence:
    unique: dict[str, NormalizedEvidence] = {}
    for item in evidence:
        if item.evidence_id in unique and unique[item.evidence_id] != item:
            # Identical extraction repetitions can have different array locations.
            old = unique[item.evidence_id]
            if old.model_dump(exclude={"source_reference"}) != item.model_dump(exclude={"source_reference"}):
                raise ValueError("Conflicting evidence identifiers")
            # Preserve each occurrence's location, even for otherwise identical items.
            item = item.model_copy(update={"evidence_id": stable_id("EV", item.evidence_id, item.source_reference)})
        unique[item.evidence_id] = item
    records = list(unique.values())
    operational_keys = {event_key(item.evidence_key) for item in records
                        if item.source_type != SourceType.AI_STATUS_REPORT and item.evidence_key}
    groups: dict[tuple[str, str], list[NormalizedEvidence]] = {}
    for item in records:
        key = event_key(item.evidence_key) if item.evidence_key else None
        if item.source_type == SourceType.AI_STATUS_REPORT:
            # Narrow identity matching: explicit key, or one unambiguous complete
            # operational event label in the source quote. Never fuzzy similarity.
            candidates = [candidate for candidate in operational_keys
                          if (key and key.removesuffix("-delay").removesuffix("-overdue") == candidate)
                          or (len(candidate.split("-")) >= 2 and
                              f" {candidate.replace('-', ' ')} " in
                              f" {' '.join((item.source_snippet or '').lower().split())} ")]
            if len(candidates) == 1:
                key = candidates[0]
        group_key = (item.project_id, key or item.evidence_id)
        groups.setdefault(group_key, []).append(item)
    return ConsolidatedEvidence(evidence=records, groups=[
        EvidenceGroup(group_id=stable_id("EG", project, key),
                      evidence_key=key if items[0].evidence_key or len(items) > 1 else None,
                      evidence_ids=[item.evidence_id for item in items],
                      dimensions=sorted({dimension for item in items for dimension in item.dimensions}))
        for (project, key), items in sorted(groups.items())
    ])
