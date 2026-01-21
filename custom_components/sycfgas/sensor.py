"""Sensor entities for Sanya Changfeng Gas."""
from __future__ import annotations

import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import UnitOfVolume

from .const import DOMAIN
from .coordinator import SycfgasCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sanya Changfeng Gas sensor entities."""
    coordinator: SycfgasCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        SycfgasBalanceSensor(coordinator, entry),
    ]

    # Add yearly usage sensors for all years with data
    # Data should already be available from async_config_entry_first_refresh in __init__.py
    data = coordinator.data or {}
    yearly_usage = data.get("yearly_usage", {})
    # Only create entities for years that actually have data
    for year in sorted(yearly_usage.keys(), reverse=True):  # Most recent first
        # Double check that the year has valid data before creating entity
        year_data = yearly_usage.get(year, {})
        usage_data = year_data.get("result", {}).get("data", [])
        if usage_data and len(usage_data) > 0:
            # Verify at least one month has valid volume > 0
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
                entities.append(SycfgasYearlyUsageSensor(coordinator, entry, year))
            else:
                _LOGGER.debug("Skipping year %s - no valid usage data (all volumes are 0)", year)
        else:
            _LOGGER.debug("Skipping year %s - no data array", year)

    # Add payment record sensor
    entities.append(SycfgasPaymentSensor(coordinator, entry))

    # Add monthly usage sensors for last 12 months
    current_date = datetime.now()
    for i in range(12):
        date = current_date - relativedelta(months=i)
        year_month = date.strftime("%Y-%m")
        entities.append(SycfgasMonthlyUsageSensor(coordinator, entry, year_month))

    async_add_entities(entities)


class SycfgasBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for Sanya Changfeng Gas sensor entities."""

    def __init__(
        self,
        coordinator: SycfgasCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor entity."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.meter_uuid)},
            name="三亚长丰燃气",
            manufacturer="三亚长丰海洋天然气供气有限公司",
            model="燃气表",
            serial_number=self.coordinator.meter_no,
        )


class SycfgasBalanceSensor(SycfgasBaseSensor):
    """Sensor for account balance."""

    _attr_unique_id = "sycfgas_balance"
    _attr_name = "账户余额"
    _attr_native_unit_of_measurement = "元"
    _attr_icon = "mdi:currency-cny"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: SycfgasCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the balance sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{coordinator.meter_uuid}_balance"

    @property
    def native_value(self) -> float | None:
        """Return the current balance."""
        data = self.coordinator.data or {}
        account_info = data.get("account_info", {})
        result = account_info.get("result", {})
        account_balance = result.get("accountBalance", "0.0")
        
        try:
            return float(account_balance)
        except (ValueError, TypeError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        data = self.coordinator.data or {}
        account_info = data.get("account_info", {})
        result = account_info.get("result", {})
        
        return {
            "remain_qty": result.get("remainQty", "0.0"),
            "fee_totals": result.get("feeTotals", "0.0"),
            "industry_type": result.get("industryType", 0),
            "is_gas_meter": result.get("isGasMeter", False),
        }


class SycfgasYearlyUsageSensor(SycfgasBaseSensor):
    """Sensor for yearly gas usage."""

    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_icon = "mdi:fire"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(
        self,
        coordinator: SycfgasCoordinator,
        entry: ConfigEntry,
        year: str,
    ) -> None:
        """Initialize the yearly usage sensor."""
        super().__init__(coordinator, entry)
        self.year = year
        self._attr_unique_id = f"{coordinator.meter_uuid}_yearly_{year}"
        self._attr_name = f"{year}年用气量"

    @property
    def native_value(self) -> float | None:
        """Return the total yearly usage."""
        data = self.coordinator.data or {}
        yearly_usage = data.get("yearly_usage", {})
        year_data = yearly_usage.get(self.year, {})
        result = year_data.get("result", {})
        usage_data = result.get("data", [])
        
        total = 0.0
        for month_data in usage_data:
            volume = month_data.get("cycleTotalVolume", "0.0")
            try:
                total += float(volume)
            except (ValueError, TypeError):
                pass
        
        return total if total > 0 else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes with monthly breakdown."""
        data = self.coordinator.data or {}
        yearly_usage = data.get("yearly_usage", {})
        year_data = yearly_usage.get(self.year, {})
        result = year_data.get("result", {})
        usage_data = result.get("data", [])
        
        monthly_breakdown = {}
        for month_data in usage_data:
            reading_time = month_data.get("readingTime", "")
            volume = month_data.get("cycleTotalVolume", "0.0")
            bill_amt = month_data.get("billAmt", "0.0")
            monthly_breakdown[reading_time] = {
                "volume": float(volume) if volume else 0.0,
                "bill_amount": float(bill_amt) if bill_amt else 0.0,
            }
        
        return {
            "monthly_breakdown": monthly_breakdown,
            "industry_type": result.get("industryType", 0),
        }


class SycfgasMonthlyUsageSensor(SycfgasBaseSensor):
    """Sensor for monthly gas usage."""

    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_icon = "mdi:fire"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(
        self,
        coordinator: SycfgasCoordinator,
        entry: ConfigEntry,
        year_month: str,
    ) -> None:
        """Initialize the monthly usage sensor."""
        super().__init__(coordinator, entry)
        self.year_month = year_month
        self._attr_unique_id = f"{coordinator.meter_uuid}_monthly_{year_month}"
        # Format name like "2025年01月用气量"
        year, month = year_month.split("-")
        self._attr_name = f"{year}年{month}月用气量"

    @property
    def native_value(self) -> float | None:
        """Return the total monthly usage."""
        data = self.coordinator.data or {}
        monthly_data = data.get("monthly_data", {})
        month_data = monthly_data.get(self.year_month, {})
        result = month_data.get("result", {})
        usage_data = result.get("data", [])
        
        total = 0.0
        for day_data in usage_data:
            volume = day_data.get("cycleTotalVolume", "0.0")
            try:
                total += float(volume)
            except (ValueError, TypeError):
                pass
        
        return total if total > 0 else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes with daily breakdown."""
        data = self.coordinator.data or {}
        monthly_data = data.get("monthly_data", {})
        month_data = monthly_data.get(self.year_month, {})
        result = month_data.get("result", {})
        usage_data = result.get("data", [])
        
        daily_breakdown = {}
        for day_data in usage_data:
            reading_time = day_data.get("readingTime", "")
            volume = day_data.get("cycleTotalVolume", "0.0")
            bill_amt = day_data.get("billAmt", "0.0")
            daily_breakdown[reading_time] = {
                "volume": float(volume) if volume else 0.0,
                "bill_amount": float(bill_amt) if bill_amt else 0.0,
            }
        
        return {
            "daily_breakdown": daily_breakdown,
            "industry_type": result.get("industryType", 0),
        }


class SycfgasPaymentSensor(SycfgasBaseSensor):
    """Sensor for recent payment record."""

    _attr_unique_id = "sycfgas_recent_payment"
    _attr_name = "最近缴费"
    _attr_native_unit_of_measurement = "元"
    _attr_icon = "mdi:credit-card"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: SycfgasCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the payment sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{coordinator.meter_uuid}_recent_payment"

    @property
    def native_value(self) -> float | None:
        """Return the most recent payment amount."""
        data = self.coordinator.data or {}
        pay_record = data.get("pay_record", {})
        result = pay_record.get("result", {})
        payment_list = result.get("list", [])
        
        if not payment_list or len(payment_list) == 0:
            return None
        
        # Get the most recent payment (first item in list, sorted by payTime)
        # Sort by payTime descending to get most recent first
        sorted_payments = sorted(
            payment_list,
            key=lambda x: x.get("payTime", ""),
            reverse=True
        )
        
        most_recent = sorted_payments[0]
        pay_amount = most_recent.get("payAmount", "0.0")
        
        try:
            return float(pay_amount)
        except (ValueError, TypeError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes with payment history."""
        data = self.coordinator.data or {}
        pay_record = data.get("pay_record", {})
        result = pay_record.get("result", {})
        payment_list = result.get("list", [])
        
        # Format payment history
        payment_history = []
        if payment_list:
            # Sort by payTime descending
            sorted_payments = sorted(
                payment_list,
                key=lambda x: x.get("payTime", ""),
                reverse=True
            )
            
            for payment in sorted_payments:
                payment_history.append({
                    "pay_amount": float(payment.get("payAmount", "0.0")),
                    "pay_time": payment.get("payTime", ""),
                    "pay_status": payment.get("payStatus", ""),
                    "pay_status_desc": payment.get("payStatusDesc", ""),
                    "pay_way": payment.get("payWayCode", ""),
                    "pay_way_desc": payment.get("payWayDesc", ""),
                    "pay_serial_no": payment.get("paySerialNo", ""),
                    "meter_no": payment.get("meterNo", ""),
                    "user_name": payment.get("userName", ""),
                    "user_address": payment.get("userAddress", ""),
                })
        
        return {
            "payment_history": payment_history,
            "total_records": len(payment_history),
            "user_no": result.get("userNo", ""),
            "meter_no": result.get("meterNo", ""),
            "start_date": result.get("startDate", ""),
            "end_date": result.get("endDate", ""),
        }
