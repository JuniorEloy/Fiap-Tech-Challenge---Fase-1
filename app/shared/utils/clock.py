from datetime import datetime, timezone


class DateTimeProvider:
    def agora(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def agora_utc(self) -> datetime:
        return datetime.now(timezone.utc)
