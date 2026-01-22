# 三亚长丰燃气 Home Assistant 集成
# 本集成由AI生成，使用了Cusor
这是一个用于 Home Assistant 的自定义集成，用于查询和监控三亚长丰海洋天然气供气有限公司的燃气使用情况、账户余额和缴费记录。
## 效果如图：
<img width="824" height="994" alt="image" src="https://github.com/user-attachments/assets/399cc055-3565-459e-bd83-1c27bd19fd2d" />

## 功能特性

- **账户余额查询**：实时显示账户余额、剩余气量等信息
- **年度用气量统计**：自动查询 2016 年至今的所有年度用气量数据
- **月度用气量统计**：显示最近 12 个月的月度用气量，包含每日明细
- **缴费记录查询**：显示最近缴费金额和历史缴费记录
- **自动数据更新**：每 5 分钟自动更新数据

## 安装方法

### 方法一：手动安装

1. 将 `sycfgas` 文件夹复制到 Home Assistant 的 `custom_components` 目录
   ```
   config/custom_components/sycfgas/
   ```

2. 重启 Home Assistant

3. 在 Home Assistant 中：
   - 进入 **设置** → **设备与服务**
   - 点击右下角的 **添加集成**
   - 搜索并选择 **三亚长丰燃气**

### 方法二：通过 HACS 安装（推荐）

1. 在 HACS 中添加自定义仓库
2. 搜索并安装 **三亚长丰燃气** 集成
3. 重启 Home Assistant

## 配置说明

### 获取 meterUUID 和 userToken
电脑Reqable，微信小程序，然后找到如图的数据

<img width="1120" height="568" alt="ScreenShot_2026-01-21_144100_760" src="https://github.com/user-attachments/assets/20024bd2-fdac-4e48-956b-3e7b3d8f6419" />


### 配置步骤

1. 在 Home Assistant 中添加集成时，输入以下信息：
   - **Meter UUID**：您的燃气表 UUID
   - **User Token**：您的用户令牌

2. 点击 **提交**，系统会自动验证连接并创建实体

## 实体说明

### 传感器实体

#### 1. 账户余额 (`sensor.账户余额`)
- **主值**：账户余额（元）
- **属性**：
  - `remain_qty`：剩余气量
  - `fee_totals`：费用总额
  - `industry_type`：行业类型
  - `is_gas_meter`：是否为燃气表

#### 2. 年度用气量 (`sensor.XXXX年用气量`)
- **说明**：为每个有数据的年份自动创建实体（2016-当前年份）
- **主值**：该年度累计用气量（立方米）
- **属性**：
  - `monthly_breakdown`：每月用气量明细
    - 格式：`YYYY-MM` → `{volume: 用气量, bill_amount: 费用}`
  - `industry_type`：行业类型

#### 3. 月度用气量 (`sensor.XXXX年XX月用气量`)
- **说明**：为最近 12 个月自动创建实体
- **主值**：该月累计用气量（立方米）
- **属性**：
  - `daily_breakdown`：每日用气量明细
    - 格式：`YYYY-MM-DD` → `{volume: 用气量, bill_amount: 费用}`
  - `industry_type`：行业类型

#### 4. 最近缴费 (`sensor.最近缴费`)
- **主值**：最近一次缴费金额（元）
- **属性**：
  - `payment_history`：历史缴费记录列表
    - `pay_amount`：缴费金额
    - `pay_time`：缴费时间
    - `pay_status`：缴费状态
    - `pay_status_desc`：缴费状态描述
    - `pay_way`：缴费方式代码
    - `pay_way_desc`：缴费方式描述
    - `pay_serial_no`：缴费流水号
    - `meter_no`：表号
    - `user_name`：用户名
    - `user_address`：用户地址
  - `total_records`：总记录数
  - `user_no`：用户编号
  - `meter_no`：表号
  - `start_date`：查询开始日期
  - `end_date`：查询结束日期

## 使用示例

### 在 Lovelace 中显示用气量

```yaml
type: entities
title: 燃气使用情况
entities:
  - entity: sensor.账户余额
  - entity: sensor.2026年用气量
  - entity: sensor.2025年用气量
  - entity: sensor.最近缴费
```

### 创建用气量图表

```yaml
type: history-graph
title: 年度用气量趋势
entities:
  - sensor.2026年用气量
  - sensor.2025年用气量
  - sensor.2024年用气量
hours_to_show: 8760
refresh_interval: 300
```

### 使用模板获取月度明细

```yaml
type: markdown
content: |
  ## 2025年用气量明细
  
  {% for month, data in state_attr('sensor.2025年用气量', 'monthly_breakdown').items() %}
  - {{ month }}: {{ data.volume }} m³ ({{ data.bill_amount }} 元)
  {% endfor %}
```

### 自动化：余额不足提醒

```yaml
alias: 燃气余额不足提醒
trigger:
  - platform: numeric_state
    entity_id: sensor.账户余额
    below: 100
condition:
  - condition: state
    entity_id: sensor.账户余额
    state: "unknown"
    for:
      minutes: 5
action:
  - service: notify.mobile_app
    data:
      title: "燃气余额不足"
      message: "当前余额：{{ states('sensor.账户余额') }} 元"
```

## 故障排除

### 实体显示"未知"

- **原因**：该年份或月份没有用气数据
- **解决**：这是正常现象，系统只为有数据的年份/月份创建实体

### 无法连接到服务器

- **检查**：确认 `meterUUID` 和 `userToken` 是否正确
- **检查**：确认网络连接正常
- **检查**：确认 API 服务是否可用

### 数据不更新

- **检查**：查看 Home Assistant 日志，查找错误信息
- **解决**：尝试重新加载集成
- **解决**：检查 `userToken` 是否过期（可能需要重新获取）

### 某些年份没有实体

- **原因**：该年份没有用气数据或所有月份的用气量都为 0
- **解决**：这是正常现象，系统只为有有效数据的年份创建实体

## 技术细节

### API 端点

- 账户信息：`POST /prod-api/acct/queryAcctInfo`
- 用气量查询：`POST /prod-api/query/iotUsage`
- 缴费记录：`GET /prod-api/query/v1/front/payRecord`

### 数据更新间隔

- 默认更新间隔：300 秒（5 分钟）
- 可在 `const.py` 中修改 `SCAN_INTERVAL_SECONDS`

### 依赖项

- `aiohttp >= 3.8.0`：异步 HTTP 客户端
- `python-dateutil >= 2.8.0`：日期处理

## 版本历史

### v1.0.0
- 初始版本
- 支持账户余额查询
- 支持年度和月度用气量统计
- 支持缴费记录查询
- 自动查询 2016 年至今的历史数据

## 许可证

本项目仅供个人学习和研究使用。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 支持

如有问题或建议，请通过以下方式联系：
- 提交 GitHub Issue
- 查看 Home Assistant 日志获取详细错误信息

---

**注意**：本集成需要有效的 `meterUUID` 和 `userToken`。请妥善保管这些凭证，不要泄露给他人。
