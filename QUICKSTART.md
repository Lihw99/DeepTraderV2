# 5分钟快速上手

> 如果你已经有聚宽策略，按照下面的步骤，5分钟就能在本地跑起来。

---

## 第一步：安装依赖

```bash
pip install backtrader pandas numpy tushare python-dotenv
```

---

## 第二步：配置 Token

1. 去 [tushare.pro](https://tushare.pro) 注册（免费）
2. 登录后复制你的 Token
3. 在 `DeepTraderV2` 目录下创建 `.env` 文件：

```
TUSHARE_TOKEN=你注册后获得的token
```

> 没有 token？戳这里：[tushare.pro 注册入口](https://tushare.pro/register)

---

## 第三步：复制你的聚宽策略

假设你的聚宽策略长这样（保存为 `my_strategy.py`）：

```python
def initialize(context):
    context.stock = "000001.SZ"

def handle_data(context, data):
    g.counter = getattr(g, 'counter', 0) + 1
    if g.counter > 10:
        order(context.stock, 100)
```

---

## 第四步：一键迁移

```bash
cd DeepTraderV2
python jq_trader/migrate.py my_strategy.py -o my_strategy_migrated.py -r
```

等待几秒，自动生成 `my_strategy_migrated.py`：

```python
from jq_trader import JQStrategy, Backtester

class MaCrossStrategy(JQStrategy):
    def initialize(self, context):
        context.stock = "000001.SZ"

    def handle_data(self, context, data):
        self.g.counter = getattr(self.g, 'counter', 0) + 1
        if self.g.counter > 10:
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

---

## 第五步：运行

```bash
python my_strategy_migrated.py
```

看到输出就成功了：

```
============================================================
  回测区间: 20200101 ~ 20231231
  股票代码: 000001.SZ
  初始资金: 1,000,000.00
  最终资金: 1,xxx,xxx.xx
  净收益:   xx,xxx.xx
  收益率:   x.xx%
============================================================
```

---

## 常见问题

**Q: 报错了？**
A: 检查：
1. `.env` 文件是否在 `DeepTraderV2` 目录下
2. Token 是否正确
3. `pip install` 是否成功

**Q: 迁移后报错了？**
A: 部分复杂语法可能需要手动调整，参考 `jq_trader/docs/MIGRATION_EXAMPLE.md`

**Q: 怎么改回测日期？**
A: 编辑生成文件中的 `start_date` 和 `end_date`

---

## 下一步

- 查看更多示例：`jq_trader/examples/demo.py`
- 学习完整 API：`jq_trader/docs/API_REFERENCE.md`
- 了解迁移细节：`jq_trader/docs/MIGRATION_EXAMPLE.md`
