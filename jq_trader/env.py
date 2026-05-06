# coding=utf-8
"""
env.py — 运行调度（JQStrategy 基类）
======================================
实现聚宽风格的策略基类和运行环境：
  - JQStrategy: 策略基类
  - run_daily / run_weekly / run_monthly: 定时调度装饰器
  - before_trading_start / after_trading_end: 交易前后回调
  - g 对象持久化
"""

import os
import pickle
from datetime import datetime, time
from typing import Callable, Dict, List, Optional, Any, Union
import re

import backtrader as bt
import pandas as pd

from jq_trader.objects import Context, Portfolio, Position
from jq_trader.trade import OrderManager
from jq_trader.utils import GStorage, is_kcb_code


# ============================================================
# 定时调度
# ============================================================
class Scheduler:
    """定时调度器"""

    def __init__(self):
        self._daily_tasks = []  # [(time_str, callback), ...]
        self._weekly_tasks = []  # [(weekday, time_str, callback), ...]
        self._monthly_tasks = []  # [(day, time_str, callback), ...]

    def run_daily(self, time_str: str = None):
        """
        每日定时任务装饰器

        Args:
            time_str: 执行时间，如 "14:30" 或 "close"（收盘时）
        """
        def decorator(func: Callable):
            self._daily_tasks.append((time_str, func))
            return func
        return decorator

    def run_weekly(self, weekday: int = None, time_str: str = None):
        """
        每周定时任务装饰器

        Args:
            weekday: 0=周一, 1=周二, ..., 6=周日
            time_str: 执行时间
        """
        def decorator(func: Callable):
            self._weekly_tasks.append((weekday, time_str, func))
            return func
        return decorator

    def run_monthly(self, day: int = None, time_str: str = None):
        """
        每月定时任务装饰器

        Args:
            day: 日期（1-28）
            time_str: 执行时间
        """
        def decorator(func: Callable):
            self._monthly_tasks.append((day, time_str, func))
            return func
        return decorator

    def should_run(self, callback_time: str, current_dt: datetime, freq: str = "daily") -> bool:
        """检查是否应该执行"""
        if callback_time is None:
            return True

        if callback_time == "close":
            return freq == "daily"

        if callback_time == "open":
            return freq == "daily"

        try:
            target_time = datetime.strptime(callback_time, "%H:%M").time()
            return current_dt.time() >= target_time
        except:
            return True

    def parse_time(self, time_str: str) -> time:
        """解析时间字符串"""
        if time_str is None:
            return None
        try:
            return datetime.strptime(time_str, "%H:%M").time()
        except:
            return None


# ============================================================
# g 对象管理
# ============================================================
class GObject:
    """g 全局变量容器（支持持久化）"""

    def __init__(self, strategy_name: str = "default"):
        self._strategy_name = strategy_name
        self._data = GStorage.load(strategy_name)

    def __getattr__(self, name: str):
        return self._data.get(name)

    def __setattr__(self, name: str, value):
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            self._data[name] = value
            self.save()

    def __getitem__(self, name: str):
        return self._data.get(name)

    def __setitem__(self, name: str, value):
        self._data[name] = value
        self.save()

    def save(self):
        """保存到磁盘"""
        GStorage.save(self._data, self._strategy_name)

    def clear(self):
        """清除持久化"""
        GStorage.clear(self._strategy_name)
        self._data = {}

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()


# ============================================================
# JQStrategy 基类
# ============================================================
class JQStrategy(bt.Strategy, Scheduler):
    """
    聚宽兼容策略基类

    用户只需定义 initialize(context) 和 handle_data(context, data)，
    无需关心 Backtrader 的 Cerebro/DataFeed。

    支持：
      - initialize(context) / handle_data(context, data)
      - run_daily / run_weekly / run_monthly 定时任务
      - before_trading_start / after_trading_end 回调
      - self.g 全局变量（持久化）
      - context.current_dt / context.portfolio 等

    示例：
        class MyStrategy(JQStrategy):
            def initialize(self, context):
                context.stock = "000001.SZ"
                self.g.counter = 0

            def handle_data(self, context, data):
                self.g.counter += 1
                self.order(context.stock, 100)

            @run_daily(time_str="14:30")
            def rebalance(self, context):
                # 每日14:30执行
                pass
    """

    def __init__(self, **kwargs):
        super().__init__()

        # Scheduler 初始化
        Scheduler.__init__(self)

        # g 全局变量
        self.g = GObject(self.__class__.__name__)

        # context
        self._context = Context()
        self._user_context = Context()

        # 初始化标记
        self._initialized = False
        self._data_loaded = False

        # 持仓快照
        self._positions = {}

        # 订单管理
        self._order_manager = OrderManager()

        # 追踪历史数据（供 self.history() 使用）
        self._history_cache = {}

        # 保存 kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)

    # ---- 生命周期回调 ----

    def prenext(self):
        """数据未完全加载时"""
        self.next()

    def nextstart(self):
        """所有数据加载完毕后"""
        self._data_loaded = True
        self._call_initialize()
        self._call_handle_data()
        self._initialized = True

    def next(self):
        """每个bar执行"""
        if not self._initialized:
            return

        # 更新 context
        self._update_context()

        # 执行每日定时任务
        self._run_daily_tasks()

        # 执行 handle_data
        self._call_handle_data()

    def _call_initialize(self):
        """调用用户的 initialize"""
        self._update_context()
        if hasattr(self, "initialize"):
            self.initialize(self._user_context)

    def _call_handle_data(self):
        """调用用户的 handle_data"""
        self._update_context()
        data = self.datas[0]
        self.handle_data(self._user_context, data)

    def _update_context(self):
        """更新 context"""
        if self.datas:
            data = self.datas[0]
            self._context._current_dt = data.datetime.date(0) if hasattr(data.datetime, 'date') else data.datetime[0]

            # 更新持仓
            self._update_positions()

            # 更新 portfolio
            self._context.portfolio.main_portfolio.available_cash = self.broker.get_cash()
            self._context.portfolio.main_portfolio.total_value = self.broker.getvalue()
            self._context.portfolio.main_portfolio.positions = self._positions

            # 更新用户 context
            self._user_context["_current_dt"] = self._context._current_dt
            self._user_context["_portfolio"] = self._context.portfolio

    def _update_positions(self):
        """更新持仓快照"""
        self._positions = {}
        for data in self.datas:
            pos = self.getposition(data)
            if pos.size != 0:
                security = getattr(data, "_security", "unknown")
                self._positions[security] = Position(
                    security=security,
                    amount=pos.size,
                    avg_cost=pos.price,
                    price=data.close[0],
                    value=pos.size * pos.price
                )

    def _run_daily_tasks(self):
        """执行每日定时任务"""
        current_dt = self.datas[0].datetime.date(0) if self.datas else datetime.now()

        for time_str, callback in self._daily_tasks:
            if self.should_run(time_str, current_dt):
                try:
                    callback(self._user_context)
                except Exception as e:
                    print(f"[jq_trader] run_daily 任务执行失败: {e}")

    # ---- 用户可调用方法 ----

    def before_trading_start(self, context):
        """每日交易前回调（可重写）"""
        pass

    def after_trading_end(self, context):
        """每日交易后回调（可重写）"""
        pass

    def history(
        self,
        count: int,
        unit: str = "1d",
        fields: Union[str, List[str]] = "close",
        df: bool = False,
    ) -> Union[bt.LineSeries, dict]:
        """
        获取最近 N 条历史数据

        Args:
            count: 条数
            unit: "1d"（仅支持日线）
            fields: 字段名
            df: True 返回 DataFrame

        Returns:
            numpy array / dict / DataFrame
        """
        import pandas as pd

        if unit != "1d":
            raise NotImplementedError("目前仅支持 unit='1d'")

        data = self.datas[0]
        field_map = {"open": 0, "high": 1, "low": 2, "close": 3, "volume": 4}

        if isinstance(fields, str):
            field_list = [fields]
        else:
            field_list = list(fields)

        for f in field_list:
            if f not in field_map:
                return pd.DataFrame() if df else {}

        lookback = min(count, len(data))
        lines = data.lines

        def get_series(idx: int):
            return [lines[idx][-i] for i in range(lookback, 0, -1)]

        if not df:
            if len(field_list) == 1:
                return get_series(field_map[field_list[0]])
            else:
                return {f: get_series(field_map[f]) for f in field_list}
        else:
            import numpy as np
            dates = [bt.num2date(lines[6][-i]) for i in range(lookback, 0, -1)]
            data_dict = {f: get_series(field_map[f]) for f in field_list}
            return pd.DataFrame(data_dict, index=dates, columns=field_list)

    def attribute_history(
        self,
        security: str,
        count: int,
        unit: str = "1d",
        fields: Union[str, List[str]] = "close",
        df: bool = False,
    ) -> Union[dict, pd.DataFrame]:
        """
        获取指定证券的历史数据

        Args:
            security: 股票代码
            count: 条数
            unit: 时间单位
            fields: 字段
            df: 返回 DataFrame

        Returns:
            dict 或 DataFrame
        """
        return self.history(count, unit, fields, df)

    def sma(self, period: int, field: str = "close") -> Optional[float]:
        """计算 SMA"""
        arr = self.history(period, unit="1d", fields=field, df=False)
        if arr is None or len(arr) < period:
            return None
        return sum(arr) / period

    # ---- 交易方法 ----

    def order(
        self,
        security: str,
        amount: int,
        price: float = None,
        style=None
    ) -> Optional[int]:
        """
        下单（市价单）

        Args:
            security: 股票代码
            amount: 正数买入，负数卖出

        Returns:
            订单 ref
        """
        if amount > 0:
            return self.buy(size=amount)
        elif amount < 0:
            return self.sell(size=abs(amount))
        return None

    def order_target(
        self,
        security: str,
        target_amount: int
    ) -> Optional[int]:
        """调仓到目标股数"""
        current = self.getposition().size
        diff = target_amount - current
        if diff != 0:
            if diff > 0:
                return self.buy(size=diff)
            else:
                return self.sell(size=abs(diff))
        return None

    def order_value(
        self,
        security: str,
        value: float,
        price: float = None
    ) -> Optional[int]:
        """按金额下单"""
        if price is None or price == 0:
            price = self.datas[0].close[0]

        if value > 0:
            amount = int(value / price / 100) * 100
            if amount > 0:
                return self.buy(size=amount)
        elif value < 0:
            amount = int(abs(value) / price / 100) * 100
            if amount > 0:
                return self.sell(size=amount)
        return None

    def order_target_value(
        self,
        security: str,
        target_value: float
    ) -> Optional[int]:
        """调仓到目标市值"""
        current_value = self.getposition().size * self.datas[0].close[0]
        diff_value = target_value - current_value
        return self.order_value(security, diff_value)

    def get_position(self, security: str = None) -> dict:
        """获取持仓"""
        data = self.datas[0]
        pos = self.getposition(data)
        return {
            "security": getattr(data, "_security", "unknown"),
            "amount": pos.size,
            "avg_cost": pos.price if pos.size > 0 else 0.0,
        }

    def cancel_order(self, order_id: int) -> bool:
        """撤销订单"""
        return self._order_manager.cancel_order(order_id, self)

    def get_open_orders(self, security: str = None) -> List:
        """获取未成交订单"""
        return self._order_manager.get_open_orders(security)

    def get_orders(self, security: str = None, status: str = None) -> List:
        """获取订单历史"""
        return self._order_manager.get_orders(security, status)

    # ---- 配置方法 ----

    def set_benchmark(self, security: str) -> None:
        """设置基准"""
        self._benchmark = security
        print(f"[jq_trader] 基准已设置为: {security}")

    def set_order_cost(self, commission: float, tax: float = None) -> None:
        """设置交易成本"""
        self._commission = commission
        self._tax = tax if tax is not None else 0.001
        self.broker.setcommission(commission)
        print(f"[jq_trader] 佣金率: {commission:.4f}, 印花税: {self._tax:.4f}")

    def set_slippage(self, slippage: float, method: str = "perc") -> None:
        """
        设置滑点模型

        Args:
            slippage: 滑点值
                    - method="perc" 时，为百分比（如 0.001 = 0.1%）
                    - method="fixed" 时，为固定金额（如 0.01 = 每股浮动0.01元）
            method: "perc" 或 "fixed"
        """
        if method == "perc":
            self.broker.set_slippage_perc(slippage)
        else:
            self.broker.set_slippage_fixed(slippage)
        self._slippage = slippage
        self._slippage_method = method
        print(f"[jq_trader] 滑点: {slippage} ({method})")

    def update_universe(self, securities: Union[str, List[str]]) -> None:
        """更新股票池"""
        if isinstance(securities, str):
            securities = [securities]
        self._context._universe = securities

    def record(self, **kwargs) -> None:
        """记录数据到结果"""
        for key, value in kwargs.items():
            if not hasattr(self, "_record_data"):
                self._record_data = {}
            self._record_data[key] = value

    def log(self, txt: str) -> None:
        """日志输出"""
        if self.datas:
            print(f"[{self.datas[0].datetime.date(0)}] {txt}")

    def send_message(self, msg: str) -> None:
        """发送消息（占位）"""
        print(f"[jq_trader] 消息: {msg}")

    # ---- Backtrader 回调 ----

    def notify_order(self, order):
        """订单状态更新"""
        self._order_manager.add_order(order)

        if not hasattr(order, "_security"):
            order._security = getattr(self.datas[0], "_security", "unknown")

        security = getattr(order, "_security", None)

        # 科创板保护价机制
        # 科创板股票价格范围限制：不超过最近收盘价的上下10%
        # 但此限制在2020年已放宽，目前仅用于提醒，不强制阻止交易
        if security and is_kcb_code(security):
            if order.status in [order.Completed]:
                # 检查是否有异常价格（超出保护价范围）
                last_price = getattr(order.data, "close", [None])[-1] if hasattr(order.data, "close") else None
                if last_price:
                    up_limit = last_price * 1.10
                    down_limit = last_price * 0.90
                    exec_price = order.executed.price
                    if exec_price > up_limit or exec_price < down_limit:
                        self.log(f"[警告] 科创板订单价格超出保护价范围: {security} 成交价={exec_price:.2f} (限价:{down_limit:.2f}~{up_limit:.2f})")

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"买入: 价格={order.executed.price:.2f}, 数量={order.executed.size}")
            else:
                self.log(f"卖出: 价格={order.executed.price:.2f}, 数量={order.executed.size}")

    def notify_trade(self, trade):
        """成交通知"""
        if trade.isclosed:
            self.log(f"盈亏: 毛={trade.pnl:.2f}, 净={trade.pnlcomm:.2f}")
            # 使用自己的列表跟踪交易
            if not hasattr(self, '_trade_history'):
                self._trade_history = []
            self._trade_history.append({
                "trade_id": trade.ref,
                "pnl": trade.pnl,
                "pnlcomm": trade.pnlcomm,
            })


# ============================================================
# 装饰器工厂函数
# ============================================================
def run_daily(time_str: str = None):
    """
    每日定时任务装饰器

    用法：
        @run_daily(time_str="14:30")
        def rebalance(context):
            pass
    """
    def decorator(func: Callable):
        func._run_daily = True
        func._daily_time = time_str
        return func
    return decorator


def run_weekly(weekday: int = None, time_str: str = None):
    """
    每周定时任务装饰器

    Args:
        weekday: 0=周一, 1=周二, ..., 6=周日
    """
    def decorator(func: Callable):
        func._run_weekly = True
        func._weekly_weekday = weekday
        func._weekly_time = time_str
        return func
    return decorator


def run_monthly(day: int = None, time_str: str = None):
    """
    每月定时任务装饰器

    Args:
        day: 日期（1-28）
    """
    def decorator(func: Callable):
        func._run_monthly = True
        func._monthly_day = day
        func._monthly_time = time_str
        return func
    return decorator
