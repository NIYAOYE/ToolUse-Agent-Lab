from dataclasses import dataclass
import json

from tool_use_agent.composition import build_ticket_service
from tool_use_agent.config import Settings
from tool_use_agent.tickets.models import TicketPriority
from tool_use_agent.tickets.repository import TicketAlreadyExists
from tool_use_agent.tickets.service import TicketService


_DEMO_TICKETS = (
    {
        "ticket_id": "DEMO-1001",
        "title": "Checkout latency after provider failover",
        "description": (
            "Synthetic demo: checkout requests exceed the latency SLO after "
            "traffic moves to the secondary payment provider."
        ),
        "environment": "demo-production",
        "service": "checkout-api",
        "priority": TicketPriority.P1,
        "category": "dependency/latency",
    },
    {
        "ticket_id": "DEMO-1002",
        "title": "Worker backlog grows during report export",
        "description": (
            "Synthetic demo: report export jobs remain queued while worker "
            "CPU and memory stay within normal ranges."
        ),
        "environment": "demo-staging",
        "service": "report-worker",
        "priority": TicketPriority.P2,
        "category": "queue/backlog",
    },
    {
        "ticket_id": "DEMO-1003",
        "title": "Intermittent authentication callback failures",
        "description": (
            "Synthetic demo: a subset of OAuth callbacks fail signature "
            "validation after a key rotation."
        ),
        "environment": "demo-production",
        "service": "identity-gateway",
        "priority": TicketPriority.P1,
        "category": "authentication/callback",
    },
    {
        "ticket_id": "DEMO-1004",
        "title": "CI build cannot resolve internal package",
        "description": (
            "Synthetic demo: the build pipeline cannot resolve one internal "
            "package after the registry mirror configuration changes."
        ),
        "environment": "demo-ci",
        "service": "build-pipeline",
        "priority": TicketPriority.P3,
        "category": "build/dependency",
    },
)


@dataclass(frozen=True)
class DemoSeedResult:
    created: int
    existing: int


def seed_demo_tickets(service: TicketService) -> DemoSeedResult:
    created = 0
    existing = 0
    for ticket in _DEMO_TICKETS:
        try:
            service.create_ticket(**ticket)
        except TicketAlreadyExists:
            existing += 1
        else:
            created += 1
    return DemoSeedResult(created=created, existing=existing)


def main() -> None:
    service = build_ticket_service(Settings.from_env())
    try:
        result = seed_demo_tickets(service)
    finally:
        service.close()
    print(json.dumps({"created": result.created, "existing": result.existing}))


if __name__ == "__main__":
    main()
