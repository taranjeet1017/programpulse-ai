# AssessPro enterprise evidence

These four files reproduce the existing 2026-09-18 AssessPro snapshot:

- weekly_status_report.docx — narrative plus a two-column snapshot header table.
- raid_log.xlsx — first worksheet RAID; heading row plus six operational entries.
- milestone_plan.xlsx — first worksheet Milestones; genuine critical-path delays,
  with Reporting Development not on the critical path.
- defect_summary.xlsx — first worksheet Quality; one wide metrics row.

Spreadsheets use recognizable aliases and typed Excel dates. Blank committed or
forecast dates mean unknown. Project and reporting date inherit the report headers.

Expected outcome: reported GREEN, ProgramPulse AMBER, Dependencies RED, conflict
true. The PM narrative's 11 scoring defects and operational count of 6 scoring
among 11 total defects deliberately remain distinct.

Select these four files in Analyze Project Evidence. Clicking Run Assessment
sends one paid extraction request; selecting the files does not call AI.
See docs/enterprise_ingestion.md for formats, mappings and limitations.

## Data safety

The AssessPro scenario and all associated project evidence are synthetic and created solely for demonstration purposes.
