"""Constants for Sanya Changfeng Gas integration."""
from __future__ import annotations

DOMAIN = "sycfgas"

# API endpoints
API_BASE_URL = "https://selfhelp-h5.mps.sycfgas.cn"
API_ACCT_INFO = "/prod-api/acct/queryAcctInfo"
API_IOT_USAGE = "/prod-api/query/iotUsage"
API_PAY_RECORD = "/prod-api/query/v1/front/payRecord"

# Update interval
SCAN_INTERVAL_SECONDS = 300  # 5 minutes

# Sensor types
SENSOR_BALANCE = "balance"
SENSOR_YEARLY_USAGE = "yearly_usage"
SENSOR_MONTHLY_USAGE = "monthly_usage"
