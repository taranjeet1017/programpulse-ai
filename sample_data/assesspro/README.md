# AssessPro evidence snapshot

Project: **AssessPro Modernization & Feature Expansion**  
Reporting date: **2026-09-18**  
Target production release: **2026-11-30**

These illustrative files are loaded on every demo assessment request:

- `weekly_status_report.md` contains PM narrative and required `Project`,
  `Reporting date`, `Reported overall health`, and `Target production release`
  metadata labels. Labels must occur once and dates use ISO format.
- `raid_log.json` contains uniquely identified risks, dependencies, scope changes,
  and actions, including materiality, escalation, and explicit release blockers.
- `milestone_plan.json` contains baseline and forecast dates. `null` means TBC.
- `defect_summary.json` contains test and defect counts and testing states.

All files must agree on project and reporting date. The initial rules calculate
AMBER against reported GREEN, with Dependencies RED and the other five dimensions
AMBER. The critical dependency is nine days overdue on the reporting date; its
unknown date affects E2E testing and UAT readiness. No explicit release blocker is
asserted, and no formal escalation has been initiated.

The PM describes 11 scoring Sev-2 defects, while the structured quality record
lists 11 total and 6 scoring Sev-2 defects. This discrepancy is deliberate to
preserve the supplied narrative. The rules use structured quality counts. Three
scoring defects have reopened. The sample execution metric includes blocked
attempts: 731 passed + 89 failed + 22 blocked = 842 executed of 1240 (~68%).

Evidence references use source-relative filenames and JSON Pointer fragments.
The application reads these files; it does not modify them. These are sample
facts, not independently verified project findings. See the root README for rule
thresholds, aggregation policy, and confidence limitations.

Reporting Development is not a critical-path milestone. Its forecast slip is retained
as evidence but does not trigger the critical-path Schedule rule; proctoring, scoring
stabilization, performance optimization and system-testing delays still do.

## Data safety

The AssessPro scenario and all associated project evidence are synthetic and created solely for demonstration purposes.
