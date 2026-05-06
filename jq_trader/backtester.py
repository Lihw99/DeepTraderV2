# coding=utf-8
"""
backtester.py — 回测运行器
==========================
提供 Backtester 类来运行回测。
"""

import os
from datetime import datetime
from typing import Optional, Union, List

import pandas as pd
import backtrader as bt

from jq_trader.data import load_stock_data
from jq_trader.adapter import DataAdapter


class Backtester:
    """
    回测运行器

    使用方式：
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
            end_date="20231231",
            initial_cash=1000000,
        )
        bt.run()
    """

    def __init__(
        self,
        strategy: type,
        stock: Union[str, List[str]],
        start_date: str,
        end_date: str,
        initial_cash: float = 1000000.0,
        commission: float = 0.0003,
        tax: float = 0.001,
        benchmark: str = None,
        adjust: str = "front",
    ):
        self.strategy = strategy
        self.stock = stock if isinstance(stock, list) else [stock]
        self.start_date = start_date
        self.end_date = end_date
        self.initial_cash = initial_cash
        self.commission = commission
        self.tax = tax
        self.benchmark = benchmark
        self.adjust = adjust

        self._cerebro = None
        self._results = None

    def run(self):
        """运行回测"""
        self._cerebro = bt.Cerebro(stdstats=True)

        # 添加数据
        for stock_code in self.stock:
            df = load_stock_data(stock_code, self.start_date, self.end_date, self.adjust)
            if df is None or df.empty:
                print(f"[jq_trader] 数据加载失败: {stock_code}")
                continue

            df_indexed = df.set_index(pd.to_datetime(df["date"]))

            datafeed = bt.feeds.PandasData(
                dataname=df_indexed,
                fromdate=pd.to_datetime(self.start_date),
                todate=pd.to_datetime(self.end_date),
            )

            # 标记证券代码
            datafeed._security = stock_code

            self._cerebro.adddata(datafeed, name=stock_code)

        # 设置资金
        self._cerebro.broker.setcash(self.initial_cash)

        # 设置佣金
        self._cerebro.broker.setcommission(commission=self.commission)

        # 设置印花税（卖出时）
        # Backtrader 简化处理，不单独区分印花税

        # 添加策略
        self._cerebro.addstrategy(self.strategy)

        # 运行
        self._results = self._cerebro.run()

        # 输出结果
        self._print_result()

        return self._results

    def _print_result(self):
        """打印回测结果"""
        end_value = self._cerebro.broker.getvalue()
        profit = end_value - self.initial_cash
        return_rate = profit / self.initial_cash

        print(f"\n{'='*60}")
        print(f"  回测区间: {self.start_date} ~ {self.end_date}")
        print(f"  股票代码: {', '.join(self.stock)}")
        print(f"  初始资金: {self.initial_cash:,.2f}")
        print(f"  最终资金: {end_value:,.2f}")
        print(f"  净收益:   {profit:,.2f}")
        print(f"  收益率:   {return_rate*100:.2f}%")
        print(f"{'='*60}")

    def get_value(self) -> float:
        """获取最终资金"""
        if self._cerebro:
            return self._cerebro.broker.getvalue()
        return self.initial_cash

    def get_cash(self) -> float:
        """获取可用资金"""
        if self._cerebro:
            return self._cerebro.broker.getcash()
        return self.initial_cash

    def get_positions(self) -> dict:
        """获取最终持仓"""
        if not self._results:
            return {}
        strategy = self._results[0]
        positions = {}
        for data in strategy.datas:
            pos = strategy.getposition(data)
            if pos.size != 0:
                security = getattr(data, "_security", "unknown")
                positions[security] = {
                    "amount": pos.size,
                    "price": pos.price,
                    "value": pos.size * pos.price,
                }
        return positions

    def get_orders(self) -> List:
        """获取所有订单"""
        if not self._results:
            return []
        return self._results[0].order_dict.values()


# ============================================================
# 便捷函数
# ============================================================
def run(
    strategy: type,
    stock: Union[str, List[str]],
    start_date: str,
    end_date: str,
    **kwargs
):
    """
    快速运行回测

    用法：
        from jq_trader import run, JQStrategy

        class MyStrategy(JQStrategy):
            def initialize(self, context):
                context.stock = "000001.SZ"
                self.g.counter = 0

            def handle_data(self, context, data):
                self.g.counter += 1
                if self.g.counter > 10:
                    self.order(context.stock, 100)

        run(MyStrategy, "000001.SZ", "20200101", "20231231")
    """
    bt = Backtester(
        strategy=strategy,
        stock=stock,
        start_date=start_date,
        end_date=end_date,
        **kwargs
    )
    return bt.run()
