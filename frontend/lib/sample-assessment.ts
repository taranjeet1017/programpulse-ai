import type { DashboardAssessment } from "./types";

// Static illustrative snapshot. No network request and no live AI result.
export const sampleAssessment = {
  "project": "AssessPro Modernization & Feature Expansion",
  "assessment_date": "2026-09-18",
  "assessment_version": "1.0",
  "reported_health": "GREEN",
  "programpulse_health": "AMBER",
  "status_conflict": true,
  "confidence": "HIGH",
  "leadership_attention_required": true,
  "dimension_summary": [
    {
      "dimension": "SCHEDULE",
      "status": "AMBER",
      "headline_reason": "Critical-path milestone Proctoring certification: baseline 2026-09-09, forecast TBC.",
      "evidence_count": 4
    },
    {
      "dimension": "SCOPE",
      "status": "AMBER",
      "headline_reason": "Material scope change remains unassessed: Reporting requirements changed after development began; scope impact assessment overdue.",
      "evidence_count": 1
    },
    {
      "dimension": "QUALITY",
      "status": "AMBER",
      "headline_reason": "11 Severity-2 defects remain open (threshold 5).",
      "evidence_count": 1
    },
    {
      "dimension": "DEPENDENCIES",
      "status": "RED",
      "headline_reason": "Proctoring certification is 9 days overdue with no revised committed resolution date. Affects: End-to-end testing, UAT readiness.",
      "evidence_count": 1
    },
    {
      "dimension": "ACTIONS",
      "status": "AMBER",
      "headline_reason": "Important action overdue since 2026-09-16: Complete reporting scope impact assessment.",
      "evidence_count": 3
    },
    {
      "dimension": "GOVERNANCE",
      "status": "AMBER",
      "headline_reason": "Material exposure has no formal escalation: Proctoring certification.",
      "evidence_count": 3
    }
  ],
  "top_governance_challenges": [
    {
      "challenge_id": "CH-077ded490936371d3d99",
      "reported_claim": "No release impact is currently anticipated.",
      "assessment": "CHALLENGED",
      "reason": "The no-impact claim requires validation against dependency and critical-path exposure. Proctoring certification is 9 days overdue with no revised committed resolution date. Affects: End-to-end testing, UAT readiness. Critical-path milestone Proctoring certification: baseline 2026-09-09, forecast TBC. Critical-path milestone Scoring defect stabilization: baseline 2026-09-18, forecast 2026-09-25.",
      "severity": "RED",
      "supporting_evidence_ids": [
        "EV-12d13cdacd048f5a4dbf",
        "EV-5887ccc6e8aa75a17cdc",
        "EV-6ae45f96465ebc2f2a0d",
        "EV-a3927688d0f57a878a33",
        "EV-f83f3f8e382e56e69ca5"
      ],
      "claim_evidence_ids": [
        "EV-74f8886ce08789d861ce"
      ]
    },
    {
      "challenge_id": "CH-bb3479adc93f95b4345f",
      "reported_claim": "No immediate escalation is required.",
      "assessment": "CHALLENGED",
      "reason": "The escalation position conflicts with unresolved dependency or governance exposure. Proctoring certification is 9 days overdue with no revised committed resolution date. Affects: End-to-end testing, UAT readiness. Material exposure has no formal escalation: Proctoring certification. Material exposure has no formal escalation: 11 Severity-2 defects remain open; three scoring defects have reopened.",
      "severity": "RED",
      "supporting_evidence_ids": [
        "EV-03095cf0fbe7ab3b8979",
        "EV-12d13cdacd048f5a4dbf",
        "EV-252b769e6beb1ce4fe56"
      ],
      "claim_evidence_ids": [
        "EV-c83ee7bf110b56fd7cda"
      ]
    },
    {
      "challenge_id": "CH-2792e041ce211216d443",
      "reported_claim": "Development is broadly on track.",
      "assessment": "CHALLENGED",
      "reason": "Reported delivery confidence requires validation against schedule and quality pressure. Critical-path milestone Proctoring certification: baseline 2026-09-09, forecast TBC. Critical-path milestone Scoring defect stabilization: baseline 2026-09-18, forecast 2026-09-25. Critical-path milestone Performance optimization: baseline 2026-09-18, forecast 2026-10-02.",
      "severity": "AMBER",
      "supporting_evidence_ids": [
        "EV-5887ccc6e8aa75a17cdc",
        "EV-6ae45f96465ebc2f2a0d",
        "EV-a3927688d0f57a878a33",
        "EV-f83f3f8e382e56e69ca5",
        "EV-ff3033fb1352a1a8f133"
      ],
      "claim_evidence_ids": [
        "EV-94922b4e700541e77dcb"
      ]
    },
    {
      "challenge_id": "CH-b40f8f7e1aebc7a7d234",
      "reported_claim": "11 Severity-2 scoring defects remain open.",
      "assessment": "REQUIRES_VALIDATION",
      "reason": "Narrative reports 11 scoring Sev-2 defects; structured quality data records 6. Structured counts drive health rules.",
      "severity": "AMBER",
      "supporting_evidence_ids": [
        "EV-ff3033fb1352a1a8f133"
      ],
      "claim_evidence_ids": [
        "EV-b9929bcd8f744cc1519a"
      ]
    }
  ],
  "top_recommended_actions": [
    {
      "action_id": "ACT-ead739268acaeda4b225",
      "description": "Escalate dependency exposure and obtain owned recovery commitments.",
      "supporting_evidence_ids": [
        "EV-12d13cdacd048f5a4dbf"
      ]
    },
    {
      "action_id": "ACT-3291914a951291d8d3a6",
      "description": "Reforecast the critical path and validate UAT entry feasibility.",
      "supporting_evidence_ids": [
        "EV-5887ccc6e8aa75a17cdc",
        "EV-6ae45f96465ebc2f2a0d",
        "EV-a3927688d0f57a878a33",
        "EV-f83f3f8e382e56e69ca5"
      ]
    },
    {
      "action_id": "ACT-3e2533793325fc2bfab8",
      "description": "Require a defect recovery plan and complete regression and testing readiness checks.",
      "supporting_evidence_ids": [
        "EV-ff3033fb1352a1a8f133"
      ]
    },
    {
      "action_id": "ACT-46564f95aed47ac19586",
      "description": "Complete the material scope impact assessment and approve the resulting plan.",
      "supporting_evidence_ids": [
        "EV-03095cf0fbe7ab3b8979"
      ]
    },
    {
      "action_id": "ACT-b5909911fb19cd3bbbaa",
      "description": "Assign accountable owners and recovery dates to overdue actions.",
      "supporting_evidence_ids": [
        "EV-4c872eb2e57a2bbc6368",
        "EV-65acc8973557b1b33fea",
        "EV-b87cb867ae34d0a8ad67"
      ]
    }
  ],
  "executive_summary": "AssessPro Modernization & Feature Expansion: reported GREEN, evidenced AMBER by ProgramPulse. A critical overdue dependency (proctoring certification), quality remediation, critical-path delays create material delivery exposure. Leadership attention is required to secure recovery commitments and validate UAT readiness.",
  "key_evidence": [
    {
      "evidence_id": "EV-12d13cdacd048f5a4dbf",
      "description": "Proctoring certification",
      "dimensions": [
        "DEPENDENCIES",
        "GOVERNANCE"
      ],
      "evidence_kind": "operational_record",
      "source_type": "RAID_LOG",
      "source_name": "raid_log.json",
      "source_reference": "raid_log.json#/items/0",
      "source_section": "/items/0",
      "source_snippet": null
    },
    {
      "evidence_id": "EV-5887ccc6e8aa75a17cdc",
      "description": "System testing completion",
      "dimensions": [
        "SCHEDULE"
      ],
      "evidence_kind": "operational_record",
      "source_type": "MILESTONE_PLAN",
      "source_name": "milestone_plan.json",
      "source_reference": "milestone_plan.json#/milestones/4",
      "source_section": "/milestones/4",
      "source_snippet": null
    },
    {
      "evidence_id": "EV-03095cf0fbe7ab3b8979",
      "description": "Reporting requirements changed after development began; scope impact assessment overdue",
      "dimensions": [
        "SCOPE",
        "GOVERNANCE"
      ],
      "evidence_kind": "operational_record",
      "source_type": "RAID_LOG",
      "source_name": "raid_log.json",
      "source_reference": "raid_log.json#/items/2",
      "source_section": "/items/2",
      "source_snippet": null
    },
    {
      "evidence_id": "EV-ff3033fb1352a1a8f133",
      "description": "11 open Sev-2 defects; 3 reopened; regression NOT STARTED; accessibility NOT STARTED.",
      "dimensions": [
        "QUALITY"
      ],
      "evidence_kind": "operational_record",
      "source_type": "QUALITY_DATA",
      "source_name": "defect_summary.json",
      "source_reference": "defect_summary.json",
      "source_section": "/",
      "source_snippet": null
    },
    {
      "evidence_id": "EV-4c872eb2e57a2bbc6368",
      "description": "Complete reporting scope impact assessment",
      "dimensions": [
        "ACTIONS"
      ],
      "evidence_kind": "operational_record",
      "source_type": "RAID_LOG",
      "source_name": "raid_log.json",
      "source_reference": "raid_log.json#/items/3",
      "source_section": "/items/3",
      "source_snippet": null
    },
    {
      "evidence_id": "EV-6ae45f96465ebc2f2a0d",
      "description": "Scoring defect stabilization",
      "dimensions": [
        "SCHEDULE"
      ],
      "evidence_kind": "operational_record",
      "source_type": "MILESTONE_PLAN",
      "source_name": "milestone_plan.json",
      "source_reference": "milestone_plan.json#/milestones/1",
      "source_section": "/milestones/1",
      "source_snippet": null
    },
    {
      "evidence_id": "EV-a3927688d0f57a878a33",
      "description": "Proctoring certification",
      "dimensions": [
        "SCHEDULE"
      ],
      "evidence_kind": "operational_record",
      "source_type": "MILESTONE_PLAN",
      "source_name": "milestone_plan.json",
      "source_reference": "milestone_plan.json#/milestones/0",
      "source_section": "/milestones/0",
      "source_snippet": null
    },
    {
      "evidence_id": "EV-f83f3f8e382e56e69ca5",
      "description": "Performance optimization",
      "dimensions": [
        "SCHEDULE"
      ],
      "evidence_kind": "operational_record",
      "source_type": "MILESTONE_PLAN",
      "source_name": "milestone_plan.json",
      "source_reference": "milestone_plan.json#/milestones/3",
      "source_section": "/milestones/3",
      "source_snippet": null
    }
  ]
} satisfies DashboardAssessment;
