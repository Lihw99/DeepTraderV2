# jq_trader 架构文档

> 本文档描述 jq_trader 的系统架构设计。

---

## 概述

jq_trader 是一个聚宽(JQ)API 兼容层，基于 Backtrader 引擎实现本地量化回测。

```
┌─────────────────────────────────────────────────────────────┐
│                        用户策略                              │
│                   (继承 JQStrategy)                         │
└────────────────────────┬────────────────────────────────────┘
                         │ 调用
┌────────────────────────▼────────────────────────────────────┐
│                      JQStrategy                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ env.py   │  │ data.py  │  │ trade.py │  │objects.py│    │
│  │ 策略基类 │  │ 数据API  │  │ 交易API  │  │ 对象模型 │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└────────────────────────┬────────────────────────────────────┘
                         │ 调用
┌────────────────────────▼────────────────────────────────────┐
│                    Backtrader 引擎                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Cerebro  │  │ DataFeed │  │ Broker   │  │ Strategy │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└────────────────────────┬────────────────────────────────────┘
                         │ 数据来源
┌────────────────────────▼────────────────────────────────────┐
│                      数据层                                  │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  本地Parquet缓存  │  │   Tushare Pro    │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心模块

### 1. env.py — 策略基类和调度器

**职责**：
- `JQStrategy`: 策略基类，兼容聚宽 API
- `Scheduler`: 定时调度器
- `GObject`: 全局变量管理器（pickle 持久化）

**关键类**：
```python
class JQStrategy(bt.Strategy, Scheduler):
    """聚宽兼容策略基类"""

    def initialize(self, context): ...
    def handle_data(self, context, data): ...
    def before_trading_start(self, context): ...
    def after_trading_end(self, context): ...
```

**装饰器**：
- `@run_daily(time_str="14:30")` — 每日定时任务
- `@run_weekly(weekday=0, time_str="09:30")` — 每周定时任务
- `@run_monthly(day=1, time_str="09:30")` — 每月定时任务

---

### 2. data.py — 数据获取层

**职责**：
- 提供聚宽风格的数据 API
- Tushare Pro API 封装
- 本地 Parquet 缓存
- 复权处理（前复权/后复权/不复权）

**核心函数**：
```python
get_price(security, count, end_date, frequency, fields)
get_bars(security, count, end_date, frequency)
get_current_data(security)
get_all_securities()
get_trade_days(start_date, end_date, is_open)
get_index_stocks(index)
get_valuation(security, date)
get_fundamentals(table, date)
get_money_flow(security)
get_billboard_list(date)
get_price_limit(security)
get_industry_stocks(industry)
get_concept_stocks(concept)
```

---

### 3. trade.py — 交易函数层

**职责**：
- 订单模型定义
- 订单管理器

**关键类**：
```python
class MarketOrder:
    """市价单"""

class LimitOrder:
    """限价单"""

class OrderManager:
    """订单管理器"""
    def buy(...)
    def sell(...)
    def cancel_order(...)
    def get_open_orders(...)
```

---

### 4. objects.py — 对象模型层

**职责**：
- 聚宽兼容对象定义

**关键类**：
```python
@dataclass
class Portfolio:
    """主账户组合"""
    main_portfolio: SubPortfolio

@dataclass
class SubPortfolio:
    """子账户组合"""
    portfolio_id, starting_cash, available_cash, total_value, positions

@dataclass
class Position:
    """持仓对象"""
    security, amount, avg_cost, price, value

@dataclass
class Order:
    """订单对象"""
    order_id, security, amount, price, action, status

@dataclass
class Trade:
    """成交记录"""

class SecurityUnitData:
    """证券数据对象"""
    close, open, high, low, volume, datetime

class Context:
    """策略执行上下文"""
```

---

### 5. adapter.py — Backtrader 适配器

**职责**：
- DataAdapter: 数据适配器
- StrategyAdapter: 策略适配器
- ConfigAdapter: 配置适配器
- CacheManager: 缓存管理器

---

### 6. backtester.py — 回测运行器

**职责**：
- `Backtester`: 回测运行类
- `run()`: 快速运行函数

**使用方式**：
```python
bt = Backtester(
    strategy=MyStrategy,
    stock="000001.SZ",
    start_date="20200101",
    end_date="20231231",
    initial_cash=1000000,
)
bt.run()
```

---

## 数据流

```
用户策略 (JQStrategy)
    │
    ├─ initialize(context)     → 设置股票池、全局变量
    ├─ handle_data(context, data) → 交易逻辑
    │
    ├─ self.g                  → 全局变量（持久化）
    ├─ context.portfolio       → 账户信息
    ├─ context.current_dt      → 当前时间
    │
    └─ self.order*(...)        → 交易函数
           │
           ▼
    Backtrader 引擎
           │
           ├─ Cerebro (主控制器)
           ├─ Broker (经纪商/资金管理)
           ├─ PandasData (数据馈送)
           └─ Strategy (策略实例)
```

---

## 配置和初始化

```python
# 创建回测
bt = Backtester(
    strategy=MaCrossStrategy,
    stock="000001.SZ",
    start_date="20200101",
    end_date="20231231",
    initial_cash=1000000,
    commission=0.0003,  # 佣金
    tax=0.001,          # 印花税
    benchmark="000001.SZ",  # 基准
    adjust="front",    # 前复权
)
bt.run()
```

---

## 第三阶段（自研引擎）

当前完全依赖 Backtrader，第三阶段需要自研引擎：

**目标**：
- 完全自主的清算/结算逻辑
- 自定义滑点模型
- 更灵活的数据加载
- 支持实时交易模式

**前置条件**：
- 完成所有聚宽 API 翻译
- 建立完整的测试体系
- 性能基准测试
