# src/harness/module_e/kernel_tools.py
from __future__ import annotations
from .vendored.companies_act import validate_statutory_demand
from .vendored.without_prejudice_detector import run as _classify_wp

def statutory_demand(args: dict) -> dict:
    """s 289 Companies Act 1993 validation + s 241(4)(a) compliance deadline.
    Thin wrapper over the vendored kernel: argument marshalling only — NO statute logic of its
    own. Required keys are read by dict indexing, so a missing one fails loudly (KeyError, not
    the TypeError a positional miss would raise) rather than silently degrading the validation."""
    return validate_statutory_demand(
        args["amount"], args["debtor_company"], args["creditor"], args["debt_details"],
        service_date=args.get("service_date"),
        compliance_period=args.get("compliance_period"),
        region=args.get("region"),
        jurisdiction=args.get("jurisdiction", "nz"),
    )

def without_prejudice(args: dict) -> dict:
    """Without-prejudice / WPSATC correspondence classification. Passes the payload straight
    through to the vendored detector's `run`, which owns the marker, injection, and trust-tier
    logic. Returns the Iron Fleet result dict unchanged."""
    return _classify_wp(args)
