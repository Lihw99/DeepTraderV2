# jq_trader API 参考文档

> 本文档提供聚宽(JQ)API 与 jq_trader 的完整对照表。

---

## 目录

1. [运行环境层](#1-运行环境层)
2. [数据获取层](#2-数据获取层)
3. [交易函数层](#3-交易函数层)
4. [对象模型层](#4-对象模型层)
5. [辅助配置层](#5-辅助配置层)
6. [数据适配层](#6-数据适配层)

---

## 1. 运行环境层

### 1.1 策略基类

| 聚宽API | jq_trader实现 | 说明 | 文件 |
|---------|---------------|------|------|
| `initialize(context)` | `JQStrategy.initialize()` | 策略初始化 | env.py |
| `handle_data(context, data)` | `JQStrategy.handle_data()` | 每bar执行 | env.py |
| `before_trading_start(context)` | `JQStrategy.before_trading_start()` | 交易前回调 | env.py |
| `after_trading_end(context)` | `JQStrategy.after_trading_end()` | 交易后回调 | env.py |

### 1.2 定时调度

| 聚宽API | jq_trader实现 | 说明 | 文件 |
|---------|---------------|------|------|
| `run_daily(time_str)` | `@run_daily()` 装饰器 | 每日定时 | env.py |
| `run_weekly(weekday, time_str)` | `@run_weekly()` 装饰器 | 每周定时 | env.py |
| `run_monthly(day, time_str)` | `@run_monthly()` 装饰器 | 每月定时 | env.py |

**使用示例**：
```python
class MyStrategy(JQStrategy):
    @run_daily(time_str="14:30")
    def rebalance(self, context):
        # 每日14:30执行
        pass

    @run_weekly(weekday=0, time_str="09:30")
    def weekly_task(self, context):
        # 每周一9:30执行
        pass
```

### 1.3 Context 属性

| 聚宽API | jq_trader实现 | 说明 | 文件 |
|---------|---------------|------|------|
| `context.current_dt` | `context._current_dt` | 当前时间 | env.py |
| `context.portfolio` | `context._portfolio` | 账户组合 | env.py |
| `context.universe` | `context._universe` | 股票池 | env.py |

### 1.4 全局变量

| 聚宽API | jq_trader实现 | 说明 | 文件 |
|---------|---------------|------|------|
| `self.g` | `self.g` | 全局变量(持久化) | env.py |

---

## 2. 数据获取层

### 2.1 历史行情

| 聚宽API | jq_trader实现 | 说明 | 文件 |
|---------|---------------|------|------|
| `get_price()` | `data.get_price()` | 获取历史行情 | data.py |
| `get_bars()` | `data.get_bars()` | 获取K线数据 | data.py |
| `get_current_data()` | `data.get_current_data()` | 当前行情 | data.py |
| `history()` | `self.history()` | 策略内获取历史 | env.py |
| `attribute_history()` | `self.attribute_history()` | 属性历史 | env.py |

**使用示例**：
```python
# get_price
df = get_price("000001.SZ", count=100, frequency="1d")

# history (在策略内)
closes = self.history(10, fields="close")
sma = sum(closes) / len(closes)
```

### 2.2 股票列表

| 聚宽API | jq_trader实现 | 说明 | 文件 |
|---------|---------------|------|------|
| `get_all_securities()` | `data.get_all_securities()` | 全量证券列表 | data.py |
| `get_trade_days()` | `data.get_trade_days()` | 交易日列表 | data.py |
| `get_index_stocks()` | `data.get_index_stocks()` | 指数成分股 | data.py |
| `get_industry_stocks()` | `data.get_industry_stocks()` | 行业成分股 | data.py |
| `get_concept_stocks()` | `data.get_concept_stocks()` | 概念成分股 | data.py |

**使用示例**：
```python
# 交易日
days = get_trade_days(start_date="20200101", end_date="20201231")

# 指数成分股
stocks = get_index_stocks("000300.XSHG")

# 行业成分股
stocks = get_industry_stocks("银行")
```

### 2.3 财务/估值数据

| 聚宽API | jq_trader实现 | 说明 | 文件 |
|---------|---------------|------|------|
| `get_valuation()` | `data.get_valuation()` | PE/PB/市值等 | data.py |
| `get_fundamentals()` | `data.get_fundamentals()` | 财务数据 | data.py |

### 2.4 资金/龙虎榜

| 聚宽API | jq_trader实现 | 说明 | 文件 |
|---------|---------------|------|------|
| `get_money_flow()` | `data.get_money_flow()` | 资金流向 | data.py |
| `get_billboard_list()` | `data.get_billboard_list()` | 龙虎榜 | data.py |
| `get_ticks()` | `data.get_ticks()` | 分笔数据(需权限) | data.py |

### 2.5 涨跌停

| 聚宽API | jq_trader实现 | 说明 | 文件 |
|---------|---------------|------|------|
| `get_price_limit()` | `data.get_price_limit()` | 涨跌停价 | data.py |

---

## 3. 交易函数层

### 3.1 订单函数

| 聚宽API | jq_trader实现 | 说明 | 文件 |
|---------|---------------|------|------|
| `order()` | `self.order()` | 市价单 | env.py |
| `order_target()` | `self.order_target()` | 目标股数 | env.py |
| `order_value()` | `self.order_value()` | 目标金额 | env.py |
| `order_target_value()` | `self.order_target_value()` | 目标市值 | env.py |
| `cancel_order()` | `self.cancel_order()` | 撤销订单 | env.py |

**使用示例**：
```python
def handle_data(self, context, data):
    # 市价单：买100股
    self.order(context.stock, 100)

    # 目标持仓：持有200股
    self.order_target(context.stock, 200)

    # 按金额：买入5000元
    self.order_value(context.stock, 5000)

    # 目标市值：持仓到10000元
    self.order_target_value(context.stock, 10000)
```

### 3.2 查询函数

| 聚宽API | jq_trader实现 | 说明 | 文件 |
|---------|---------------|------|------|
| `get_open_orders()` | `self.get_open_orders()` | 未成交订单 | env.py |
| `get_orders()` | `self.get_orders()` | 订单历史 | env.py |
| `get_position()` | `self.get_position()` | 当前持仓 | env.py |
| `get_trades()` | `trade.get_trades()` | 成交记录 | trade.py |

### 3.3 订单类型

| 聚宽API | jq_trader实现 | 说明 | 文件 |
|---------|---------------|------|------|
| `MarketOrder` | `trade.MarketOrder` | 市价单 | trade.py |
| `LimitOrder` | `trade.LimitOrder` | 限价单 | trade.py |

---

## 4. 对象模型层

| 聚宽对象 | jq_trader实现 | 说明 | 文件 |
|----------|---------------|------|------|
| `Portfolio` | `objects.Portfolio` | 主账户组合 | objects.py |
| `SubPortfolio` | `objects.SubPortfolio` | 子账户组合 | objects.py |
| `Position` | `objects.Position` | 持仓对象 | objects.py |
| `Order` | `objects.Order` | 订单对象 | objects.py |
| `Trade` | `objects.Trade` | 成交记录 | objects.py |
| `SecurityUnitData` | `objects.SecurityUnitData` | 证券数据 | objects.py |
| `Context` | `objects.Context` | 策略上下文 | objects.py |

### 4.1 Portfolio 属性

```python
portfolio.available_cash   # 可用资金
portfolio.total_value     # 总资产
portfolio.positions        # 持仓字典
portfolio.locked_cash     # 锁定资金
portfolio.starting_cash   # 初始资金
portfolio.daily_return    # 日收益率
```

### 4.2 Position 属性

```python
position.security     # 股票代码
position.amount       # 持仓数量
position.avg_cost     # 平均成本
position.price        # 当前价格
position.value        # 市值
position.market_value # 市值（同value）
position.unrealized_pnl  # 浮动盈亏
```

---

## 5. 辅助配置层

| 聚宽API | jq_trader实现 | 说明 | 文件 |
|---------|---------------|------|------|
| `set_benchmark()` | `self.set_benchmark()` | 设置基准 | env.py |
| `set_order_cost()` | `self.set_order_cost()` | 设置交易成本 | env.py |
| `set_slippage()` | 占位 | 滑点模型(未实现) | env.py |
| `record()` | `self.record()` | 记录数据 | env.py |
| `log()` | `self.log()` | 日志输出 | env.py |
| `send_message()` | `self.send_message()` | 发送消息(占位) | env.py |

**使用示例**：
```python
class MyStrategy(JQStrategy):
    def initialize(self, context):
        self.set_benchmark("000001.SZ")    # 设置基准
        self.set_order_cost(commission=0.0003, tax=0.001)  # 设置成本
        self.record(my_value=0)           # 记录数据

    def handle_data(self, context, data):
        self.log(f"当前时间: {context.current_dt}")  # 日志
```

---

## 6. 数据适配层

### 6.1 代码转换

| 功能 | 说明 | 文件 |
|------|------|------|
| `jq_to_tushare_code()` | 聚宽代码→tushare代码 | utils.py |
| `tushare_to_jq_code()` | tushare代码→聚宽代码 | utils.py |
| `normalize_code()` | 标准化代码 | utils.py |

**转换规则**：
- `000001.XSHE` → `000001.SZ` (深市)
- `600000.XSHG` → `600000.SH` (沪市)

### 6.2 复权方式

| 聚宽 | jq_trader | 说明 |
|------|-----------|------|
| `none` | `fq="none"` | 不复权 |
| `front` | `fq="front"` | 前复权 |
| `back` | `fq="back"` | 后复权 |

### 6.3 数据源

| 数据源 | 说明 |
|--------|------|
| 本地Parquet | `D:\A股全数据260320\个股日线\` |
| Tushare Pro | 在线API（需token） |

---

## 附录：状态码说明

### 订单状态

| 状态码 | 说明 |
|--------|------|
| `pending` | 待处理 |
| `open` | 已提交 |
| `filled` | 已成交 |
| `cancelled` | 已撤销 |
| `rejected` | 已拒绝 |

### 交易动作

| 动作 | 说明 |
|------|------|
| `buy` | 买入 |
| `sell` | 卖出 |

---

## 更新日志

| 日期 | 操作 | 说明 |
|------|------|------|
| 2026-05-06 | 创建文档 | 完成API对照表 |
