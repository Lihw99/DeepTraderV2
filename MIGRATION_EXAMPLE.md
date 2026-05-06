# 策略迁移示例

## 聚宽策略迁移演示

假设你有一个聚宽策略 `original_jq_strategy.py`：

```python
# 聚宽双均线策略
def initialize(context):
    context.stock = "000001.SZ"
    g.short = 5
    g.long = 20
    g.counter = 0

def handle_data(context, data):
    g.counter += 1

    hist = attribute_history(context.stock, 20, unit="1d", fields=["close"])
    ma5 = hist["close"].mean()
    ma20 = hist["close"].mean()

    pos = context.portfolio.positions[context.stock]
    if ma5 > ma20 and pos.amount == 0:
        order(context.stock, 100)
    elif ma5 < ma20 and pos.amount > 0:
        order(context.stock, -pos.amount)
```

### 迁移步骤

```bash
# 1. 保存上面的代码为 original_jq_strategy.py

# 2. 运行迁移工具
python jq_trader/migrate.py original_jq_strategy.py -o migrated_strategy.py -r
```

### 迁移结果

自动生成 `migrated_strategy.py`：

```python
from jq_trader import JQStrategy, Backtester

class MaCrossStrategy(JQStrategy):
    def initialize(self, context):
        context.stock = "000001.SZ"
        self.g.short = 5
        self.g.long = 20
        self.g.counter = 0

    def handle_data(self, context, data):
        self.g.counter += 1

        hist = self.history(20, fields="close", df=True)
        ma5 = hist["close"].mean()
        ma20 = hist["close"].mean()

        pos = self.get_position(context.stock)
        if ma5 > ma20 and pos["amount"] == 0:
            self.order(context.stock, 100)
        elif ma5 < ma20 and pos["amount"] > 0:
            self.order(context.stock, -pos["amount"])


# ========== 以下为自动添加的运行代码 ==========
if __name__ == "__main__":
    bt = Backtester(
        strategy=MaCrossStrategy,
        stock="000001.SZ",
        start_date="20200101",
        end_date="20231231",
        initial_cash=1000000,
    )
    bt.run()
```

### 运行迁移后的策略

```bash
python migrated_strategy.py
```

### 改动对照

| 原始（聚宽） | 迁移后（jq_trader） |
|--------------|-------------------|
| `def initialize(context):` | `def initialize(self, context):` |
| `g.counter` | `self.g.counter` |
| `context.portfolio.positions[stock]` | `self.get_position(stock)` |
| `attribute_history(...)` | `self.history(..., df=True)` |
| `pos.amount` | `pos["amount"]` |
| `order(...)` | `self.order(...)` |
| 无类定义 | `class MaCrossStrategy(JQStrategy):` |

---

## 手动迁移速查

如果不想用工具，手动改 6 处：

```python
# 1. 文件开头加
from jq_trader import JQStrategy, Backtester

# 2. 函数套 class
class MyStrategy(JQStrategy):
    def initialize(self, context):
        ...

# 3. handle_data 加 self
def handle_data(self, context, data):

# 4. g 改成 self.g
g.counter → self.g.counter

# 5. portfolio 改成 get_position
context.portfolio.positions["000001.SZ"]
    → self.get_position("000001.SZ")
    → pos["amount"]  # 注意取值的写法

# 6. 末尾加运行代码
if __name__ == "__main__":
    bt = Backtester(strategy=MyStrategy, stock="000001.SZ", ...)
    bt.run()
```

详见 [MIGRATION_EXAMPLE.md](./jq_trader/docs/MIGRATION_EXAMPLE.md)
