"""API client for Sanya Changfeng Gas."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import API_BASE_URL, API_ACCT_INFO, API_IOT_USAGE, API_PAY_RECORD

_LOGGER = logging.getLogger(__name__)


class SycfgasAPIClient:
    """Client for Sanya Changfeng Gas API."""

    def __init__(self, meter_uuid: str, user_token: str) -> None:
        """Initialize the API client.

        Args:
            meter_uuid: Meter UUID
            user_token: User token
        """
        self.meter_uuid = meter_uuid
        self.user_token = user_token
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_account_info(self) -> dict[str, Any]:
        """Get account balance information."""
        session = await self._get_session()
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
            "content-type": "application/x-www-form-urlencoded",
            "accept": "*/*",
            "origin": "https://selfhelp-h5.mps.sycfgas.cn",
            "referer": f"https://selfhelp-h5.mps.sycfgas.cn/iotusage?userToken={self.user_token}",
        }

        data = {
            "meterUuid": self.meter_uuid,
            "clientType": "1",
            "pagePath": "pages/index/index",
            "clientVersion": "1.0.16",
            "channelType": "0",
            "tenantId": "005600",
            "userToken": self.user_token,
        }

        try:
            async with session.post(
                f"{API_BASE_URL}{API_ACCT_INFO}",
                headers=headers,
                data=data,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                result = await response.json()
                return result
        except aiohttp.ClientError as err:
            _LOGGER.error("Error getting account info: %s", err)
            raise

    async def get_monthly_usage(self, year: str) -> dict[str, Any]:
        """Get monthly usage for a year.

        Args:
            year: Year in format "YYYY"

        Returns:
            API response with monthly usage data
        """
        session = await self._get_session()
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
            "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
            "accept": "application/json",
            "origin": "https://selfhelp-h5.mps.sycfgas.cn",
            "referer": f"https://selfhelp-h5.mps.sycfgas.cn/iotusage?userToken={self.user_token}",
        }

        data = {
            "meterUUID": self.meter_uuid,
            "query": year,
            "type": "1",  # 1 for monthly, 0 for daily
            "userToken": self.user_token,
        }

        try:
            async with session.post(
                f"{API_BASE_URL}{API_IOT_USAGE}",
                headers=headers,
                data=data,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                result = await response.json()
                return result
        except aiohttp.ClientError as err:
            _LOGGER.error("Error getting monthly usage: %s", err)
            raise

    async def get_daily_usage(self, year_month: str) -> dict[str, Any]:
        """Get daily usage for a month.

        Args:
            year_month: Year and month in format "YYYY-MM"

        Returns:
            API response with daily usage data
        """
        session = await self._get_session()
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
            "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
            "accept": "application/json",
            "origin": "https://selfhelp-h5.mps.sycfgas.cn",
            "referer": f"https://selfhelp-h5.mps.sycfgas.cn/iotusage?userToken={self.user_token}",
        }

        data = {
            "meterUUID": self.meter_uuid,
            "query": year_month,
            "type": "0",  # 0 for daily, 1 for monthly
            "userToken": self.user_token,
        }

        try:
            async with session.post(
                f"{API_BASE_URL}{API_IOT_USAGE}",
                headers=headers,
                data=data,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                result = await response.json()
                return result
        except aiohttp.ClientError as err:
            _LOGGER.error("Error getting daily usage: %s", err)
            raise

    async def get_pay_record(self) -> dict[str, Any]:
        """Get payment records."""
        session = await self._get_session()
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
            "content-type": "application/x-www-form-urlencoded",
            "accept": "*/*",
            "origin": "https://selfhelp-h5.mps.sycfgas.cn",
            "referer": f"https://selfhelp-h5.mps.sycfgas.cn/iotusage?userToken={self.user_token}",
        }

        params = {
            "meterUUID": self.meter_uuid,
            "clientType": "1",
            "pagePath": "query/payRecordQuery/payRecordQuery",
            "clientVersion": "1.0.16",
            "channelType": "0",
            "tenantId": "005600",
            "userToken": self.user_token,
        }

        try:
            async with session.get(
                f"{API_BASE_URL}{API_PAY_RECORD}",
                headers=headers,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                result = await response.json()
                return result
        except aiohttp.ClientError as err:
            _LOGGER.error("Error getting pay record: %s", err)
            raise
