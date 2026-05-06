# 聚宽策略迁移指南

## 迁移一句话：改 3 处就能跑

把聚宽策略改成 jq_trader，只需要：

```
1. import 换一下
2. 类名换一下
3. 函数签名换一下
```

---

## 实际例子

### 原始聚宽策略

```python
# 聚宽量化策略
def initialize(context):
    context.stock = "000001.SZ"
    context.short_window = 5
    context.long_window = 20
    g.counter = 0

def handle_data(context, data):
    g.counter += 1

    # 获取历史数据
    hist = attribute_history(context.stock, context.long_window, unit="1d", fields=["close"])
    ma5 = hist["close"].mean()
    ma20 = context.long_window

    # 交易逻辑
    position = context.portfolio.positions[context.stock]
    if ma5 > ma20 and position.amount == 0:
        order(context.stock, 100)

# 运行
run_daily(time_str="14:30")
```

### 迁移后 jq_trader 策略

```python
# 只需要改这3处 ↓

# 1. import 换一下
from jq_trader import JQStrategy, Backtester

# 2. 类名换一下 + 加装饰器
class MaCrossStrategy(JQStrategy):
    def initialize(self, context):
        context.stock = "000001.SZ"
        context.short_window = 5
        context.long_window = 20
        self.g.counter = 0

    def handle_data(self, context, data):
        self.g.counter += 1

        # 获取历史数据（self.history 替代 attribute_history）
        closes = self.history(context.long_window, fields="close")
        if len(closes) < context.long_window:
            return
        ma5 = sum(closes[-context.short_window:]) / context.short_window
        ma20 = sum(closes[-context.long_window:]) / context.long_window

        # 交易逻辑（self.get_position 替代 context.portfolio）
        pos = self.get_position()
        if ma5 > ma20 and pos["amount"] == 0:
            self.order(context.stock, 100)

# 3. 用 Backtester 运行
bt = Backtester(
    strategy=MaCrossStrategy,
    stock="000001.SZ",
    start_date="20200101",
    end_date="20231231",
    initial_cash=1000000,
)
bt.run()
```

---

## 3 处改动详解

### 1. import 替换

| 聚宽 | jq_trader |
|------|-----------|
| `run_daily` (内置) | `from jq_trader import JQStrategy, Backtester` |
| 无需导入 | `from jq_trader.env import run_daily` (需要装饰器时) |

### 2. 类名替换

| 聚宽 | jq_trader |
|------|-----------|
| `def initialize(context):` | `def initialize(self, context):` |
| `def handle_data(context, data):` | `def handle_data(self, context, data):` |
| 无类定义 | `class xxx(JQStrategy):` |

### 3. 变量访问替换

| 聚宽 | jq_trader |
|------|-----------|
| `g.counter` | `self.g.counter` |
| `context.portfolio.positions[stock]` | `self.get_position()` |
| `context.current_dt` | `context._current_dt` |
| `attribute_history(...)` | `self.history(...)` |

---

## 常见模式对照

### 获取持仓

```python
# 聚宽
position = context.portfolio.positions["000001.SZ"]
amount = position.amount
avg_cost = position.avg_cost

# jq_trader
pos = self.get_position("000001.SZ")
amount = pos["amount"]
avg_cost = pos["avg_cost"]
```

### 历史数据

```python
# 聚宽
hist = attribute_history("000001.SZ", 20, unit="1d", fields=["close", "volume"])
closes = hist["close"]

# jq_trader
closes = self.history(20, fields="close")
volumes = self.history(20, fields="volume")
```

### 下单

```python
# 聚宽
order("000001.SZ", 100)           # 买入100股
order_target("000001.SZ", 200)    # 持仓到200股
order_value("000001.SZ", 5000)    # 买入5000元

# jq_trader（完全一样）
self.order("000001.SZ", 100)
self.order_target("000001.SZ", 200)
self.order_value("000001.SZ", 5000)
```

### 定时任务

```python
# 聚宽
def rebalance(context):
    pass
run_daily(rebalance, time_str="14:30")

# jq_trader
class MyStrategy(JQStrategy):
    @run_daily(time_str="14:30")
    def rebalance(self, context):
        pass
```

---

## 自动化迁移工具（未来）

计划中的 `migrate.py` 工具，可以一键转换：

```bash
python migrate.py original_strategy.py -o migrated_strategy.py
```

自动替换：
- `g.` → `self.g.`
- `context.portfolio` → `self.get_position()`
- `attribute_history` → `self.history`
- 添加 `class xxx(JQStrategy):` 包装

---

## 自检清单

迁移完后，检查以下几点：

- [ ] import 是否正确
- [ ] 是否继承了 `JQStrategy`
- [ ] `initialize` 和 `handle_data` 是否有 `self` 参数
- [ ] `g.xxx` 是否改成 `self.g.xxx`
- [ ] `context.portfolio` 相关是否改成 `self.get_position()`
- [ ] `Backtester` 是否正确配置