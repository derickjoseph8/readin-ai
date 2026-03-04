"""
Business hours calculation service for SLA tracking.

Provides functionality to calculate business hours between dates,
add business hours to a datetime, and check if a datetime falls
within business hours.
"""

from datetime import datetime, timedelta, time, date
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
import pytz


@dataclass
class BusinessHoursConfig:
    """Configuration for business hours calculations."""

    # Working hours (24-hour format)
    start_hour: int = 9
    start_minute: int = 0
    end_hour: int = 17
    end_minute: int = 0

    # Working days (0=Monday, 6=Sunday)
    working_days: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])

    # Holidays as list of date strings (YYYY-MM-DD format)
    holidays: List[str] = field(default_factory=list)

    # Timezone
    timezone: str = "UTC"

    @property
    def start_time(self) -> time:
        """Get start time as time object."""
        return time(self.start_hour, self.start_minute)

    @property
    def end_time(self) -> time:
        """Get end time as time object."""
        return time(self.end_hour, self.end_minute)

    @property
    def daily_hours(self) -> float:
        """Get total business hours per day."""
        start_minutes = self.start_hour * 60 + self.start_minute
        end_minutes = self.end_hour * 60 + self.end_minute
        return (end_minutes - start_minutes) / 60.0

    @property
    def tz(self) -> pytz.timezone:
        """Get timezone object."""
        return pytz.timezone(self.timezone)

    @classmethod
    def from_organization(cls, org: Any) -> "BusinessHoursConfig":
        """Create config from organization model."""
        if org is None:
            return cls()

        # Parse business hours start/end if available
        start_hour = 9
        start_minute = 0
        end_hour = 17
        end_minute = 0

        if hasattr(org, 'business_hours_start') and org.business_hours_start:
            start_parts = org.business_hours_start.split(':')
            start_hour = int(start_parts[0])
            start_minute = int(start_parts[1]) if len(start_parts) > 1 else 0

        if hasattr(org, 'business_hours_end') and org.business_hours_end:
            end_parts = org.business_hours_end.split(':')
            end_hour = int(end_parts[0])
            end_minute = int(end_parts[1]) if len(end_parts) > 1 else 0

        working_days = [0, 1, 2, 3, 4]  # Mon-Fri default
        if hasattr(org, 'business_days') and org.business_days:
            working_days = org.business_days

        holidays = []
        if hasattr(org, 'holidays') and org.holidays:
            holidays = org.holidays

        timezone = "UTC"
        if hasattr(org, 'business_timezone') and org.business_timezone:
            timezone = org.business_timezone

        return cls(
            start_hour=start_hour,
            start_minute=start_minute,
            end_hour=end_hour,
            end_minute=end_minute,
            working_days=working_days,
            holidays=holidays,
            timezone=timezone
        )


class BusinessHoursService:
    """Service for calculating business hours for SLA tracking."""

    def __init__(self, config: Optional[BusinessHoursConfig] = None):
        """
        Initialize the business hours service.

        Args:
            config: Business hours configuration. Uses defaults if not provided.
        """
        self.config = config or BusinessHoursConfig()
        self._holidays_cache: set = set()
        self._parse_holidays()

    def _parse_holidays(self) -> None:
        """Parse holiday strings into date objects for faster lookup."""
        self._holidays_cache = set()
        for holiday_str in self.config.holidays:
            try:
                holiday_date = datetime.strptime(holiday_str, "%Y-%m-%d").date()
                self._holidays_cache.add(holiday_date)
            except ValueError:
                # Skip invalid date formats
                continue

    def _to_local(self, dt: datetime) -> datetime:
        """Convert datetime to configured timezone."""
        if dt.tzinfo is None:
            # Assume UTC if no timezone
            dt = pytz.UTC.localize(dt)
        return dt.astimezone(self.config.tz)

    def _to_utc(self, dt: datetime) -> datetime:
        """Convert datetime to UTC."""
        if dt.tzinfo is None:
            # Assume it's in local timezone
            dt = self.config.tz.localize(dt)
        return dt.astimezone(pytz.UTC)

    def is_holiday(self, dt: datetime) -> bool:
        """
        Check if a date is a holiday.

        Args:
            dt: The datetime to check

        Returns:
            True if the date is a holiday
        """
        local_dt = self._to_local(dt)
        return local_dt.date() in self._holidays_cache

    def is_working_day(self, dt: datetime) -> bool:
        """
        Check if a date is a working day (not weekend, not holiday).

        Args:
            dt: The datetime to check

        Returns:
            True if the date is a working day
        """
        local_dt = self._to_local(dt)
        weekday = local_dt.weekday()

        if weekday not in self.config.working_days:
            return False

        if self.is_holiday(dt):
            return False

        return True

    def is_business_hour(self, dt: datetime) -> bool:
        """
        Check if a datetime falls within business hours.

        Args:
            dt: The datetime to check

        Returns:
            True if the datetime is within business hours
        """
        if not self.is_working_day(dt):
            return False

        local_dt = self._to_local(dt)
        current_time = local_dt.time()

        return self.config.start_time <= current_time < self.config.end_time

    def get_next_business_hour(self, dt: datetime) -> datetime:
        """
        Get the next datetime that falls within business hours.

        If the input datetime is already within business hours, returns it unchanged.
        Otherwise, returns the start of the next business day.

        Args:
            dt: The starting datetime

        Returns:
            The next datetime within business hours (in UTC)
        """
        local_dt = self._to_local(dt)

        # If already in business hours, return as-is
        if self.is_business_hour(dt):
            return self._to_utc(local_dt).replace(tzinfo=None)

        current_time = local_dt.time()

        # Check if we're before business hours on a working day
        if self.is_working_day(dt) and current_time < self.config.start_time:
            next_dt = local_dt.replace(
                hour=self.config.start_hour,
                minute=self.config.start_minute,
                second=0,
                microsecond=0
            )
            return self._to_utc(next_dt).replace(tzinfo=None)

        # Move to next day and find next working day
        next_day = local_dt.date() + timedelta(days=1)
        max_days = 365  # Safety limit

        for _ in range(max_days):
            next_dt = datetime.combine(
                next_day,
                time(self.config.start_hour, self.config.start_minute)
            )
            next_dt = self.config.tz.localize(next_dt)

            if self.is_working_day(next_dt):
                return self._to_utc(next_dt).replace(tzinfo=None)

            next_day += timedelta(days=1)

        # Fallback (should never reach here)
        return dt

    def _get_business_end(self, dt: datetime) -> datetime:
        """Get the end of business hours for a given date."""
        local_dt = self._to_local(dt)
        end_dt = local_dt.replace(
            hour=self.config.end_hour,
            minute=self.config.end_minute,
            second=0,
            microsecond=0
        )
        return end_dt

    def _get_business_start(self, dt: datetime) -> datetime:
        """Get the start of business hours for a given date."""
        local_dt = self._to_local(dt)
        start_dt = local_dt.replace(
            hour=self.config.start_hour,
            minute=self.config.start_minute,
            second=0,
            microsecond=0
        )
        return start_dt

    def calculate_business_hours(
        self,
        start: datetime,
        end: datetime
    ) -> float:
        """
        Calculate the number of business hours between two datetimes.

        Args:
            start: The start datetime
            end: The end datetime

        Returns:
            The number of business hours between start and end
        """
        if end <= start:
            return 0.0

        # Convert to local timezone
        start_local = self._to_local(start)
        end_local = self._to_local(end)

        total_minutes = 0.0
        current = start_local

        while current < end_local:
            if self.is_working_day(current):
                # Get business hours boundaries for this day
                day_start = self._get_business_start(current)
                day_end = self._get_business_end(current)

                # Determine effective start and end for this day
                effective_start = max(current, day_start)
                effective_end = min(end_local, day_end)

                if effective_start < effective_end:
                    # Only count time within business hours
                    if effective_start.time() >= self.config.start_time and \
                       effective_end.time() <= self.config.end_time:
                        minutes = (effective_end - effective_start).total_seconds() / 60
                        total_minutes += minutes

            # Move to start of next day
            current = (current + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        return total_minutes / 60.0

    def add_business_hours(
        self,
        start: datetime,
        hours: float
    ) -> datetime:
        """
        Add business hours to a datetime.

        Args:
            start: The starting datetime
            hours: The number of business hours to add

        Returns:
            The resulting datetime after adding business hours (in UTC)
        """
        if hours <= 0:
            return start

        remaining_minutes = hours * 60
        current = self.get_next_business_hour(start)
        current_local = self._to_local(current)

        max_iterations = 365 * 24  # Safety limit
        iterations = 0

        while remaining_minutes > 0 and iterations < max_iterations:
            iterations += 1

            if self.is_working_day(current_local):
                # Get end of business hours for current day
                day_end = self._get_business_end(current_local)

                # Calculate minutes remaining in current business day
                minutes_left_today = (day_end - current_local).total_seconds() / 60

                if minutes_left_today > 0:
                    if remaining_minutes <= minutes_left_today:
                        # We can finish within today
                        result = current_local + timedelta(minutes=remaining_minutes)
                        return self._to_utc(result).replace(tzinfo=None)
                    else:
                        # Use all remaining time today
                        remaining_minutes -= minutes_left_today

            # Move to next working day
            next_day = current_local.date() + timedelta(days=1)
            current_local = datetime.combine(
                next_day,
                time(self.config.start_hour, self.config.start_minute)
            )
            current_local = self.config.tz.localize(current_local)

            # Skip non-working days
            while not self.is_working_day(current_local):
                next_day += timedelta(days=1)
                current_local = datetime.combine(
                    next_day,
                    time(self.config.start_hour, self.config.start_minute)
                )
                current_local = self.config.tz.localize(current_local)

        # Return result
        return self._to_utc(current_local).replace(tzinfo=None)

    def get_sla_deadline(
        self,
        start: datetime,
        sla_minutes: int,
        use_business_hours: bool = True
    ) -> datetime:
        """
        Calculate SLA deadline from a start time.

        Args:
            start: The start datetime (e.g., ticket creation time)
            sla_minutes: The SLA duration in minutes
            use_business_hours: If True, count only business hours

        Returns:
            The SLA deadline datetime (in UTC)
        """
        if not use_business_hours:
            # Simple calendar time calculation
            return start + timedelta(minutes=sla_minutes)

        # Business hours calculation
        hours = sla_minutes / 60.0
        return self.add_business_hours(start, hours)

    def time_until_breach(
        self,
        deadline: datetime,
        current: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate time remaining until SLA breach.

        Args:
            deadline: The SLA deadline
            current: Current time (defaults to now)

        Returns:
            Dict with total_minutes, business_minutes, and is_breached
        """
        now = current or datetime.utcnow()

        if now >= deadline:
            return {
                "total_minutes": 0,
                "business_minutes": 0,
                "is_breached": True,
                "breach_at": deadline
            }

        total_minutes = (deadline - now).total_seconds() / 60
        business_hours = self.calculate_business_hours(now, deadline)

        return {
            "total_minutes": total_minutes,
            "business_minutes": business_hours * 60,
            "is_breached": False,
            "breach_at": deadline
        }


def create_business_hours_service(
    organization: Any = None,
    config: Optional[BusinessHoursConfig] = None
) -> BusinessHoursService:
    """
    Factory function to create a BusinessHoursService.

    Args:
        organization: Optional organization model with business hours settings
        config: Optional explicit configuration (takes precedence over organization)

    Returns:
        Configured BusinessHoursService instance
    """
    if config:
        return BusinessHoursService(config)

    if organization:
        config = BusinessHoursConfig.from_organization(organization)
        return BusinessHoursService(config)

    return BusinessHoursService()
