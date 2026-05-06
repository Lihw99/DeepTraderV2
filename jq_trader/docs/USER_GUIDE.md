# jq_trader 使用指南

## 什么是 jq_trader？

jq_trader 是一个**聚宽(JQ)API 兼容层**，让你可以用聚宽的写法，在本地运行量化回测。

**简单说**：你写的聚宽策略代码，稍微改一下，就能直接在本地跑，不需要充值聚宽会员。

---

## 快速开始

### 1. 安装依赖

```bash
pip install backtrader pandas tushare
```

### 2. 写一个策略

假设你想做一个**双均线策略**：金叉买，死叉卖。

**聚宽版**（需要在聚宽网站运行）：
```python
def initialize(context):
    context.stock = "000001.SZ"
    context.short_ma = 5
    context.long_ma = 20

def handle_data(context, data):
    hist = attribute_history(context.stock, context.long_ma, unit="1d", fields=["close"])
    ma_short = hist["close"].mean()
    ma_long = hist["close"].mean()
    
    if ma_short > ma_long and context.portfolio.positions[context.stock].amount == 0:
        order(context.stock, 100)
```

**jq_trader版**（本地运行）：
```python
from jq_trader import JQStrategy, Backtester

class MaCrossStrategy(JQStrategy):
    def initialize(self, context):
        context.stock = "000001.SZ"
        self.g.short_ma = 5
        self.g.long_ma = 20
        
    def handle_data(self, context, data):
        # 获取历史数据
        closes = self.history(self.g.long_ma, fields="close")
        if len(closes) < self.g.long_ma:
            return
        
        ma_short = sum(closes[-self.g.short_ma:]) / self.g.short_ma
        ma_long = sum(closes[-self.g.long_ma:]) / self.g.long_ma
        
        # 交易逻辑
        pos = self.get_position()
        if ma_short > ma_long and pos["amount"] == 0:
            self.order(context.stock, 100)  # 买入
        elif ma_short < ma_long and pos["amount"] > 0:
            self.order(context.stock, -pos["amount"])  # 卖出
```

### 3. 运行回测

```python
bt = Backtester(
    strategy=MaCrossStrategy,
    stock="000001.SZ",
    start_date="20200101",
    end_date="20231231",
    initial_cash=1000000,
)
bt.run()
```

**输出**：
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

## 核心概念

### 1. Context（上下文）

Context 是策略的"全局变量容器"，存储账户信息和用户数据：

```python
def initialize(self, context):
    context.stock = "000001.SZ"      # 用户数据
    context.target_ratio = 0.5        # 用户数据
    print(context.current_dt)         # 当前时间
    print(context.portfolio.total_value)  # 总资产
```

### 2. self.g（全局变量）

self.g 用于跨日期保存数据，会自动持久化：

```python
def initialize(self, context):
    self.g.counter = 0               # 计数器
    self.g.last_trade_date = None    # 上次交易日期
    
def handle_data(self, context, data):
    self.g.counter += 1              # 每次bar执行+1
```

### 3. 下单函数

| 函数 | 说明 | 示例 |
|------|------|------|
| `order(股票, 数量)` | 买/卖指定数量 | `order("000001.SZ", 100)` 买100股 |
| `order_target(股票, 数量)` | 调仓到目标数量 | `order_target("000001.SZ", 200)` 持仓到200股 |
| `order_value(股票, 金额)` | 买/卖指定金额 | `order_value("000001.SZ", 5000)` 买入5000元 |
| `order_target_value(股票, 市值)` | 调仓到目标市值 | `order_target_value("000001.SZ", 50000)` 持仓到5万市值 |

### 4. 定时任务

```python
class MyStrategy(JQStrategy):
    @run_daily(time_str="14:30")
    def rebalance(self, context):
        # 每天14:30执行调仓
        pass
    
    @run_weekly(weekday=0, time_str="09:30")
    def weekly_review(self, context):
        # 每周一9:30执行
        pass
```

---

## 对比：聚宽 vs jq_trader

| 功能 | 聚宽 | jq_trader |
|------|------|------------|
| 运行地点 | 聚宽云端 | 本地 |
| 费用 | 免费/付费 | 免费 |
| 数据源 | 聚宽数据 | Tushare/本地 |
| 实时交易 | 支持 | 仅回测 |
| 网络依赖 | 必须在线 | 可离线回测 |

---

## 适用场景

**适合用 jq_trader**：
- 本地调试策略，不需要每次上传
- 大量回测测试，不想付聚宽费用
- 策略不想公开，但想本地验证
- 需要对接自己的数据源

**不适合 jq_trader**：
- 需要实时交易
- 需要聚宽特有数据（因子库等）
- 完全不懂代码，需要可视化回测

---

## 完整示例

```python
# -*- coding: utf-8 -*-
from jq_trader import JQStrategy, Backtester, run_daily

class ValueStrategy(JQStrategy):
    """低估价值策略：PE低于行业均值时买入"""
    
    def initialize(self, context):
        context.stock = "000001.SZ"
        self.g.has_position = False
        
        # 设置交易成本
        self.set_order_cost(commission=0.0003, tax=0.001)
        
    def handle_data(self, context, data):
        # 获取持仓
        pos = self.get_position()
        
        # 简单策略：价格低于10元买入，高于15元卖出
        current_price = data.close[0]
        
        if not self.g.has_position and current_price < 10:
            self.order(context.stock, 1000)
            self.g.has_position = True
            self.log(f"买入: 价格={current_price:.2f}")
            
        elif self.g.has_position and current_price > 15:
            self.order(context.stock, -pos["amount"])
            self.g.has_position = False
            self.log(f"卖出: 价格={current_price:.2f}")
    
    @run_daily(time_str="14:30")
    def daily_check(self, context):
        """每日14:30检查持仓"""
        pos = self.get_position()
        if pos["amount"] > 0:
            self.log(f"持仓: {pos['amount']}股, 成本={pos['avg_cost']:.2f}")

# 运行回测
if __name__ == "__main__":
    bt = Backtester(
        strategy=ValueStrategy,
        stock="000001.SZ",
        start_date="20200101",
        end_date="20231231",
        initial_cash=1000000,
    )
    bt.run()
    
    # 打印持仓
    print("最终持仓:", bt.get_positions())
```

---

## 下一步

- 查看 [API参考文档](./docs/API_REFERENCE.md) 了解所有可用函数
- 查看 [架构文档](./docs/ARCHITECTURE.md) 了解内部原理
- 查看 [迁移状态](./docs/MIGRATION_STATUS.md) 了解开发进度