# coding=utf-8
"""
jq_trader — 聚宽 API 完整兼容层（第二阶段）
==============================================
将聚宽(JQ)策略语法翻译为 Backtrader 执行。

模块化架构：
  - env.py      : 运行调度（JQStrategy 基类）
  - data.py     : 数据获取函数
  - trade.py    : 交易函数
  - objects.py  : 对象模型
  - adapter.py  : 引擎适配器
  - utils.py    : 工具函数

使用方式：
    from jq_trader import JQStrategy, Backtester, run_daily

    class MyStrategy(JQStrategy):
        def initialize(self, context):
            context.stock = "000001.SZ"

        def handle_data(self, context, data):
            self.order(context.stock, 100)

    bt = Backtester(strategy=MyStrategy, stock="000001.SZ", ...)
    bt.run()
"""

from jq_trader.env import JQStrategy
from jq_trader.backtester import Backtester

__all__ = [
    "JQStrategy",
    "Backtester",
]
