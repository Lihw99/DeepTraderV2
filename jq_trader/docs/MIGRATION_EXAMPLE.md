# 聚宽策略迁移对比（并排看）

## 完整策略对比

左边是**聚宽原始代码**，右边是**改完的jq_trader代码**，不同之处已标红。

---

### 策略1：双均线金叉策略

```
┌─────────────────────────────────────┬─────────────────────────────────────┐
│ 聚宽（原始）                          │ jq_trader（改后）                      │
├─────────────────────────────────────┼─────────────────────────────────────┤
│                                     │ from jq_trader import JQStrategy,    │
│ def initialize(context):             │             Backtester               │
│     context.stock = "000001.SZ"     │                                     │
│     g.short = 5                      │ class MaCross(JQStrategy):          │
│     g.long = 20                      │     def initialize(self, context):  │
│                                      │         context.stock = "000001.SZ" │
│ def handle_data(context, data):     │         self.g.short = 5           │
│     hist = attribute_history(       │         self.g.long = 20           │
│         context.stock, 20,           │                                     │
│         unit="1d", fields=["close"] │     def handle_data(self, context, │
│     )                                │                 data):              │
│     ma5 = hist["close"].mean()      │         closes = self.history(      │
│     ma20 = hist["close"].mean()      │             20, fields="close")   │
│                                      │         if len(closes) < 20: return │
│     pos = context.portfolio.        │         ma5 = sum(closes[-5:])/5    │
│         positions[context.stock]     │         ma20 = sum(closes[-20:])/20│
│     if ma5 > ma20 and pos.amount==0:│                                     │
│         order(context.stock, 100)    │         pos = self.get_position() │
│                                      │         if ma5 > ma20 and \       │
│                                      │             pos["amount"] == 0:     │
│                                      │             self.order(context.stock,│
│                                      │                          100)     │
│                                      │                                     │
│ # 运行需要上传到聚宽网站              │ bt = Backtester(                   │
│                                      │     strategy=MaCross,              │
│                                      │     stock="000001.SZ",             │
│                                      │     start_date="20200101",         │
│                                      │     end_date="20231231")           │
│                                      │ bt.run()  # 本地直接跑              │
└─────────────────────────────────────┴─────────────────────────────────────┘
```

**改动点**：import 1处、def改class 2处、加self 3处、g改self.g 4处、portfolio改get_position 5处

---

### 策略2：PE阈值止盈策略

```
┌─────────────────────────────────────┬─────────────────────────────────────┐
│ 聚宽（原始）                          │ jq_trader（改后）                      │
├─────────────────────────────────────┼─────────────────────────────────────┤
│ def initialize(context):             │ class PEProtection(JQStrategy):     │
│     context.stock = "000001.SZ"     │     def initialize(self, context):  │
│     g.buy_price = 0                 │         context.stock = "000001.SZ" │
│     g.has_position = False           │         self.g.buy_price = 0       │
│                                     │         self.g.has_position = False│
│ def handle_data(context, data):     │                                     │
│     current = data.close            │     def handle_data(self, context, │
│     position = context.portfolio.    │                 data):              │
│         positions[context.stock]    │         current = data.close[0]    │
│                                     │         pos = self.get_position()   │
│     if not g.has_position:          │                                     │
│         if current < 10:            │         if not self.g.has_position: │
│             order(context.stock, 500)│             if current < 10:       │
│             g.buy_price = current    │                 self.order(       │
│             g.has_position = True   │                     context.stock, │
│                                      │                     500)          │
│     else:                           │                 self.g.buy_price =  │
│         if current > g.buy_price * 1.2:│                     current     │
│             order(context.stock,     │                 self.g.has_position│
│                   -position.amount)  │                     = True        │
│             g.has_position = False   │                                 │
│                                      │         else:                    │
│                                      │             if current > \        │
│                                      │                 self.g.buy_price │
│                                      │                 * 1.2:            │
│                                      │                 self.order(       │
│                                      │                     context.stock,│
│                                      │                     -pos["amount"])│
│                                      │                 self.g.has_position│
│                                      │                     = False        │
└─────────────────────────────────────┴─────────────────────────────────────┘
```

---

## 改动速查表

### 1. 文件头部

```python
# 聚宽：不需要import，直接写函数
def initialize(context):
    ...

# jq_trader：需要import和继承
from jq_trader import JQStrategy, Backtester

class MyStrategy(JQStrategy):
    ...
```

### 2. def 改成 class

```python
# 聚宽
def initialize(context):
def handle_data(context, data):

# jq_trader
class MyStrategy(JQStrategy):
    def initialize(self, context):
    def handle_data(self, context, data):
```

### 3. g 改成 self.g

```python
# 聚宽
g.counter = 0
g.has_position = True

# jq_trader
self.g.counter = 0
self.g.has_position = True
```

### 4. portfolio 改成 get_position

```python
# 聚宽
pos = context.portfolio.positions["000001.SZ"]
if pos.amount > 0:

# jq_trader
pos = self.get_position("000001.SZ")
if pos["amount"] > 0:
```

### 5. 历史数据

```python
# 聚宽
hist = attribute_history("000001.SZ", 20, unit="1d", fields=["close"])
closes = hist["close"]

# jq_trader
closes = self.history(20, fields="close")
```

### 6. 定时任务

```python
# 聚宽
def my_task(context):
    pass
run_daily(my_task, time_str="14:30")

# jq_trader
class MyStrategy(JQStrategy):
    @run_daily(time_str="14:30")
    def my_task(self, context):
        pass
```

---

## 总结：只有这 6 处需要改

| # | 位置 | 聚宽写法 | jq_trader写法 |
|---|------|---------|--------------|
| 1 | 文件开头 | 直接写函数 | `from jq_trader import ...` + `class X(JQStrategy):` |
| 2 | 函数参数 | `def initialize(context):` | `def initialize(self, context):` |
| 3 | 函数参数 | `def handle_data(context, data):` | `def handle_data(self, context, data):` |
| 4 | 全局变量 | `g.xxx` | `self.g.xxx` |
| 5 | 持仓查询 | `context.portfolio.positions[stock]` | `self.get_position()` |
| 6 | 定时任务 | `run_daily(func, ...)` | `@run_daily(...)` 装饰器 |

**order / order_target / order_value / log 这些不用改**，jq_trader 全部兼容。

---

## 一句话总结

```
聚宽策略 → 顶部加2行 → 套个class壳 → 加self → g变self.g
```

就这么简单。
