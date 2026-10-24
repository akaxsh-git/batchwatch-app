"""Role-based access control, enforced in the backend (not only in the UI).

Every protected function calls require(actor, permission). A denied attempt
is written to the audit log and raises PermissionError.
"""

PERMISSIONS = {
    "admin": {
        "ingest_alerts", "approve_ingest", "view_all_audit", "view_alerts",
        "compliance_report_any",
    },
    "pharmacist": {
        "check_stock", "quarantine", "draft_supplier_return", "decide_own_actions",
        "view_org_audit", "compliance_report_org", "view_alerts", "batch_search",
    },
    "household": {
        "scan_label", "manage_cabinet", "draft_controller_report", "decide_own_actions",
        "view_own_audit", "batch_search",
    },
    # the agent itself, when it acts on a schedule (monthly re-check)
    "system": {"recheck", "notify", "ingest_alerts"},
}


def can(actor: dict, permission: str) -> bool:
    return permission in PERMISSIONS.get(actor.get("role"), set())


def require(actor: dict, permission: str):
    if not can(actor, permission):
        from .audit import log  # local import avoids a cycle
        log(actor, f"denied:{permission}", status="denied",
            output={"reason": f"role '{actor.get('role')}' lacks '{permission}'"})
        raise PermissionError(f"{actor.get('name')} ({actor.get('role')}) is not allowed to {permission}")
