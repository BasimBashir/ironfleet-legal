r"""Vendored IronFleet kernel code — copied, not imported, from the retired tree.

Source of record (read-only, never imported across trees):
  ..\IronFleet\legalai\skills\nz-statutory-demand-validator\scripts\companies_act.py
  ..\IronFleet\legalai\skills\without-prejudice-detector\scripts\without_prejudice_detector.py
  ..\IronFleet\legalai\helpers\nz_calendar.py
  ..\IronFleet\legalai\helpers\court_calendar.py
  ..\IronFleet\legalai\helpers\jurisdiction_loader.py
  ..\IronFleet\legalai\config\jurisdictions\{nz,au,uk}.json + {nz,au,uk}_holidays.json

The data lives at ``vendored/data/config/jurisdictions/`` — the old
``config/jurisdictions/`` nesting is preserved because the JSONs'
``holidays_file`` values carry that prefix. Vendoring required exactly three
kinds of edit and nothing else: `helpers.x` imports became package-relative,
and the two path constants in `court_calendar` / `jurisdiction_loader` were
repointed at ``vendored/data``. Working-day, holiday, and validation logic is
byte-identical to the old tree (modulo CRLF -> LF).
"""
