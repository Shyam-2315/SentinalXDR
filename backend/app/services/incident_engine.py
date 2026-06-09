from app.models.alert import Alert
from app.models.incident import Incident
from app.repositories.incidents import IncidentRepository


class IncidentEngine:
    def __init__(self, incidents: IncidentRepository, correlation_window_minutes: int) -> None:
        self.incidents = incidents
        self.correlation_window_minutes = correlation_window_minutes

    async def process_alerts(self, alerts: list[Alert]) -> tuple[list[Incident], list[Incident]]:
        created: list[Incident] = []
        updated: list[Incident] = []

        for alert in alerts:
            incident = await self.incidents.find_matching_open_incident(
                alert=alert,
                correlation_window_minutes=self.correlation_window_minutes,
            )
            if incident is None:
                created.append(await self.incidents.create_from_alert(alert))
                continue
            updated.append(await self.incidents.append_alert(incident=incident, alert=alert))

        return created, updated
