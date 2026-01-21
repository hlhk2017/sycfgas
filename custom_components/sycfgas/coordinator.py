"""Data update coordinator for Sanya Changfeng Gas."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import SycfgasAPIClient
from .const import DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class SycfgasCoordinator(DataUpdateCoordinator):
    """Coordinator for Sanya Changfeng Gas data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.entry = entry
        self.api_client = SycfgasAPIClient(
            meter_uuid=entry.data["meter_uuid"],
            user_token=entry.data["user_token"],
        )
        self.meter_uuid = entry.data["meter_uuid"]
        self.user_name = entry.data.get("user_name", "未知用户")  # Fallback value
        self.meter_no = entry.data.get("meter_no", "")

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            # Get account balance and payment records in parallel
            account_info_task = self.api_client.get_account_info()
            pay_record_task = self.api_client.get_pay_record()
            
            account_info, pay_record = await asyncio.gather(
                account_info_task,
                pay_record_task,
                return_exceptions=True,
            )
            
            # Handle account_info exception
            if isinstance(account_info, Exception):
                _LOGGER.warning("Failed to get account info: %s", account_info)
                account_info = {}
            else:
                # Update user_name from account info if available
                if account_info and account_info.get("responseCode") == "100000":
                    result = account_info.get("result", {})
                    meter_info = result.get("meterInfo", {})
                    cust_name = meter_info.get("custName")
                    if cust_name and cust_name != "未知用户":
                        old_name = self.user_name
                        self.user_name = cust_name
                        if old_name != cust_name:
                            _LOGGER.info("Updated user_name from '%s' to '%s'", old_name, cust_name)
            
            # Handle payment record exception
            if isinstance(pay_record, Exception):
                _LOGGER.warning("Failed to get payment record: %s", pay_record)
                pay_record = {}
            
            # Query yearly usage for all years from 2016 to current year
            current_year = int(datetime.now().strftime("%Y"))
            start_year = 2016
            years = [str(year) for year in range(start_year, current_year + 1)]
            
            # Query all years in parallel
            yearly_tasks = [
                self.api_client.get_monthly_usage(year) for year in years
            ]
            yearly_results = await asyncio.gather(*yearly_tasks, return_exceptions=True)
            
            # Build yearly_usage dict, only include years with data
            yearly_usage = {}
            for year, result in zip(years, yearly_results):
                if isinstance(result, Exception):
                    _LOGGER.debug("No data for year %s: %s", year, result)
                    continue
                # Check if the response has data
                if result and result.get("responseCode") == "100000":
                    usage_data = result.get("result", {}).get("data", [])
                    # Only include if data exists and has actual usage records
                    if usage_data and isinstance(usage_data, list) and len(usage_data) > 0:
                        # Double check: verify at least one record has valid volume
                        has_valid_data = False
                        for month_data in usage_data:
                            volume = month_data.get("cycleTotalVolume", "0.0")
                            try:
                                if float(volume) > 0:
                                    has_valid_data = True
                                    break
                            except (ValueError, TypeError):
                                pass
                        if has_valid_data:
                            yearly_usage[year] = result
                            _LOGGER.debug("Found data for year %s: %d months", year, len(usage_data))
                        else:
                            _LOGGER.debug("Year %s has no valid usage data", year)
                    else:
                        _LOGGER.debug("Year %s returned empty data array", year)
                else:
                    _LOGGER.debug("Year %s returned invalid response: %s", year, result.get("responseCode") if result else "None")
            
            # Get last 12 months of daily usage in parallel
            current_date = datetime.now()
            monthly_tasks = []
            year_months = []
            for i in range(12):
                date = current_date - relativedelta(months=i)
                year_month = date.strftime("%Y-%m")
                year_months.append(year_month)
                monthly_tasks.append(self.api_client.get_daily_usage(year_month))
            
            # Execute all monthly requests in parallel
            monthly_results = await asyncio.gather(*monthly_tasks, return_exceptions=True)
            
            # Build monthly_data dict, handling exceptions
            monthly_data = {}
            for year_month, result in zip(year_months, monthly_results):
                if isinstance(result, Exception):
                    _LOGGER.warning("Failed to get daily usage for %s: %s", year_month, result)
                    continue
                monthly_data[year_month] = result

            return {
                "account_info": account_info,
                "yearly_usage": yearly_usage,
                "monthly_data": monthly_data,
                "pay_record": pay_record if not isinstance(pay_record, Exception) else {},
            }
        except Exception as err:
            # On error, return existing data to preserve state
            if self.data:
                _LOGGER.warning("Error updating data, preserving existing data: %s", err)
                return self.data
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def async_shutdown(self) -> None:
        """Shutdown coordinator."""
        await self.api_client.close()
