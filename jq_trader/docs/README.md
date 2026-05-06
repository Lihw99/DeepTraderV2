# jq_trader 文档目录

## 概览
- [README.md](./README.md) — 项目总体介绍

## 迁移状态
- [MIGRATION_STATUS.md](./MIGRATION_STATUS.md) — 迁移进度日志，包含已完成/未完成清单

## 架构
- [ARCHITECTURE.md](./ARCHITECTURE.md) — 系统架构设计

## API参考
- [API_REFERENCE.md](./API_REFERENCE.md) — 聚宽API与jq_trader对照表

## 使用指南
- [USER_GUIDE.md](./USER_GUIDE.md) — 快速入门和使用示例

## 迁移指南
- [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) — 从聚宽迁移策略到jq_trader
- [MIGRATION_EXAMPLE.md](./MIGRATION_EXAMPLE.md) — 并排对比示例（推荐先看这个）

---

## 快速开始

```python
from jq_trader import JQStrategy, Backtester

class MyStrategy(JQStrategy):
    def initialize(self, context):
        context.stock = "000001.SZ"

    def handle_data(self, context, data):
        self.order(context.stock, 100)

bt = Backtester(
    strategy=MyStrategy,
    stock="000001.SZ",
    start_date="20200101",
    end_date="20231231"
)
bt.run()
```

## 关键文件

```
jq_trader/
├── env.py          # 核心策略基类
├── data.py         # 数据API
├── trade.py        # 交易API
├── objects.py      # 对象模型
├── adapter.py      # Backtrader适配器
├── backtester.py   # 回测运行器
├── utils.py        # 工具函数
└── docs/
    ├── README.md              # 本文档
    ├── MIGRATION_STATUS.md     # 迁移状态日志
    ├── ARCHITECTURE.md          # 架构文档
    └── API_REFERENCE.md        # API对照表
```

```python
from jq_trader import JQStrategy, Backtester

class MyStrategy(JQStrategy):
    def initialize(self, context):
        context.stock = "000001.SZ"

    def handle_data(self, context, data):
        self.order(context.stock, 100)

bt = Backtester(
    strategy=MyStrategy,
    stock="000001.SZ",
    start_date="20200101",
    end_date="20231231"
)
bt.run()
```
