# DeepTrader

> 把聚宽策略直接搬到本地跑，不需要会员、不需要上传代码、完全私有。

---

## 功能特点

| 特点 | 说明 |
|------|------|
| **零门槛迁移** | 聚宽策略只需改 3 处就能跑 |
| **本地运行** | 数据存在本地，不需要每次联网 |
| **完全兼容** | 90%+ 聚宽 API 已支持 |
| **免费数据** | 支持 Tushare Pro 免费额度 |
| **小白友好** | 提供自动迁移工具，一键转换 |

---

## 快速开始

### 1. 安装依赖

```bash
pip install backtrader pandas numpy tushare python-dotenv
```

### 2. 配置 Tushare Token（必选）

1. 去 [tushare.pro](https://tushare.pro) 注册账号
2. 创建 `.env` 文件（和 `jq_trader` 同目录）：

```
TUSHARE_TOKEN=你的token
```

> 没有 Tushare token？去 [tushare.pro 注册](https://tushare.pro/register)，免费账号有基础额度

### 3. 写一个策略

创建一个文件 `my_strategy.py`：

```python
# 聚宽策略（原始）
def initialize(context):
    context.stock = "000001.SZ"

def handle_data(context, data):
    order(context.stock, 100)
```

### 4. 一键迁移

```bash
python jq_trader/migrate.py my_strategy.py -o my_strategy_migrated.py -r
```

自动转换后生成：

```python
from jq_trader import JQStrategy, Backtester

class MaCrossStrategy(JQStrategy):
    def initialize(self, context):
        context.stock = "000001.SZ"

    def handle_data(self, context, data):
        self.order(context.stock, 100)

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

### 5. 运行回测

```bash
python my_strategy_migrated.py
```

输出：

```
============================================================
  回测区间: 20200101 ~ 20231231
  股票代码: 000001.SZ
  初始资金: 1,000,000.00
  最终资金: 1,125,000.00
  净收益:   125,000.00
  收益率:   12.50%
============================================================
```

---

## 目录结构

```
DeepTrader/
├── jq_trader/              # 核心库（直接 import 使用）
│   ├── __init__.py
│   ├── env.py              # 策略基类 JQStrategy
│   ├── data.py             # 数据获取函数
│   ├── trade.py            # 交易函数
│   ├── objects.py          # 数据对象
│   ├── backtester.py      # 回测运行器
│   ├── adapter.py          # Backtrader 适配器
│   ├── utils.py            # 工具函数（含 .env 自动加载）
│   ├── migrate.py          # 聚宽策略迁移工具 ⭐推荐使用
│   └── docs/               # 文档
│
├── examples/               # 示例策略
│   └── demo.py
│
├── .env                    # Token 配置（不要提交到 GitHub）
├── .env.example           # Token 模板
└── .gitignore
```

---

## 核心 API

### 数据获取

```python
from jq_trader import data

# 获取历史行情
df = data.get_price("000001.SZ", count=100)

# 交易日列表
days = data.get_trade_days(start_date="20200101", end_date="20201231")

# 指数成分股
stocks = data.get_index_stocks("000300.XSHG")  # 沪深300

# 行业成分股
stocks = data.get_industry_stocks("银行")

# 概念成分股（开盘啦）
stocks = data.get_concept_stocks("AI低代码概念")
```

### 下单交易

```python
class MyStrategy(JQStrategy):
    def handle_data(self, context, data):
        # 市价单：买100股
        self.order("000001.SZ", 100)

        # 目标持仓：持有200股
        self.order_target("000001.SZ", 200)

        # 按金额：买入5000元
        self.order_value("000001.SZ", 5000)
```

### 定时任务

```python
from jq_trader.env import run_daily, run_weekly, run_monthly

class MyStrategy(JQStrategy):
    @run_daily(time_str="14:30")
    def rebalance(self, context):
        # 每天14:30执行
        pass

    @run_weekly(weekday=0, time_str="09:30")
    def weekly_review(self, context):
        # 每周一9:30执行
        pass
```

---

## 迁移工具（推荐）

把聚宽策略代码粘贴到文件，直接运行迁移工具：

```bash
# 基本迁移
python jq_trader/migrate.py 原始策略.py -o 迁移后策略.py

# 同时添加运行代码
python jq_trader/migrate.py 原始策略.py -o 迁移后策略.py -r
```

**会自动转换**：
- `def initialize(context):` → `class X(JQStrategy): def initialize(self, context):`
- `g.xxx` → `self.g.xxx`
- `context.portfolio.positions[stock]` → `self.get_position()`
- `attribute_history(...)` → `self.history(...)`
- 添加 `Backtester` 运行代码

---

## 示例策略

### 双均线策略

```python
from jq_trader import JQStrategy, Backtester

class MaCrossStrategy(JQStrategy):
    def initialize(self, context):
        context.stock = "000001.SZ"
        self.g.short_ma = 5
        self.g.long_ma = 20

    def handle_data(self, context, data):
        closes = self.history(self.g.long_ma, fields="close")
        if len(closes) < self.g.long_ma:
            return

        ma5 = sum(closes[-self.g.short_ma:]) / self.g.short_ma
        ma20 = sum(closes[-self.g.long_ma:]) / self.g.long_ma

        pos = self.get_position()
        if ma5 > ma20 and pos["amount"] == 0:
            self.order(context.stock, 100)
        elif ma5 < ma20 and pos["amount"] > 0:
            self.order(context.stock, -pos["amount"])

bt = Backtester(
    strategy=MaCrossStrategy,
    stock="000001.SZ",
    start_date="20200101",
    end_date="20231231",
)
bt.run()
```

更多示例在 `examples/` 目录。

---

## 常见问题

**Q: 需要多少积分？**
A: Tushare 免费账号基础额度够日常使用。部分高级接口（如分笔数据）需要付费积分。

**Q: 本地需要存数据吗？**
A: 不需要。本地有 Parquet 数据时会优先使用，没有则自动用 Tushare API。

**Q: 策略保密吗？**
A: 完全本地运行，代码不外传。

**Q: 支持实时交易吗？**
A: 目前仅支持回测。实时交易是第三阶段计划。

---

## 文档

详细文档在 `jq_trader/docs/` 目录：

| 文档 | 内容 |
|------|------|
| [USER_GUIDE.md](./jq_trader/docs/USER_GUIDE.md) | 快速入门 |
| [MIGRATION_GUIDE.md](./jq_trader/docs/MIGRATION_GUIDE.md) | 迁移指南 |
| [MIGRATION_EXAMPLE.md](./jq_trader/docs/MIGRATION_EXAMPLE.md) | 并排对比示例 |
| [API_REFERENCE.md](./jq_trader/docs/API_REFERENCE.md) | API 对照表 |
| [ARCHITECTURE.md](./jq_trader/docs/ARCHITECTURE.md) | 架构设计 |
| [MIGRATION_STATUS.md](./jq_trader/docs/MIGRATION_STATUS.md) | 开发进度 |

---

## 许可

MIT License
