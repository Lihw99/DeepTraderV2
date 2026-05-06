# coding=utf-8
"""
trade.py — 交易函数
====================
实现聚宽风格的交易 API：
  - order, order_target, order_value, order_target_value
  - cancel_order, get_open_orders, get_orders, get_trades
  - MarketOrder / LimitOrder 支持
"""

from typing import List, Optional, Union
import backtrader as bt

from jq_trader.objects import Order


# ============================================================
# 订单类型
# ============================================================
class MarketOrder:
    """市价单"""
    def __init__(self, price=None):
        self.price = price


class LimitOrder:
    """限价单"""
    def __init__(self, price):
        self.price = price


# ============================================================
# 订单管理
# ============================================================
class OrderManager:
    """订单管理器"""

    def __init__(self):
        self._orders = {}  # {ref: bt.Order}
        self._order_counter = 0

    def add_order(self, bt_order) -> int:
        """添加Backtrader订单到管理"""
        self._order_counter += 1
        self._orders[bt_order.ref] = bt_order
        return self._order_counter

    def get_order(self, order_id: int):
        """通过ID获取订单"""
        for order in self._orders.values():
            if order.ref == order_id:
                return order
        return None

    def get_open_orders(self, security: str = None) -> List:
        """获取未成交订单"""
        open_orders = [
            o for o in self._orders.values()
            if o.status in [bt.Order.Submitted, bt.Order.Partial]
        ]
        if security:
            open_orders = [
                o for o in open_orders
                if getattr(o, "_security", None) == security
            ]
        return open_orders

    def get_orders(
        self,
        security: str = None,
        status: str = None
    ) -> List:
        """获取订单历史"""
        orders = list(self._orders.values())

        if security:
            orders = [o for o in orders if getattr(o, "_security", None) == security]

        if status == "open":
            orders = [o for o in orders if o.status in [bt.Order.Submitted, bt.Order.Partial]]
        elif status == "closed":
            orders = [o for o in orders if o.status in [bt.Order.Completed, bt.Order.Canceled, bt.Order.Rejected]]

        return orders

    def cancel_order(self, order_id: int, strategy) -> bool:
        """撤销订单"""
        for order in self._orders.values():
            if order.ref == order_id:
                if order.status in [bt.Order.Submitted, bt.Order.Partial]:
                    strategy.cancel(order)
                    order.status = bt.Order.Canceled
                    return True
        return False

    def clear(self):
        """清空订单"""
        self._orders.clear()


# ============================================================
# 交易函数封装
# ============================================================
def order(
    strategy,
    security: str,
    amount: int,
    price: float = None,
    style=None
) -> Optional[int]:
    """
    下单（市价单）

    Args:
        strategy: JQStrategy 实例
        security: 股票代码
        amount: 正数买入，负数卖出
        price: 价格（目前未使用）
        style: 订单类型（MarketOrder/LimitOrder）

    Returns:
        订单ID
    """
    if amount > 0:
        return strategy.buy(size=amount)
    elif amount < 0:
        return strategy.sell(size=abs(amount))
    return None


def order_target(
    strategy,
    security: str,
    target_amount: int
) -> Optional[int]:
    """
    调仓到目标股数

    Args:
        strategy: JQStrategy 实例
        security: 股票代码
        target_amount: 目标持仓股数（0=清仓）

    Returns:
        订单ID
    """
    current = strategy.getposition().size
    diff = target_amount - current
    if diff != 0:
        if diff > 0:
            return strategy.buy(size=diff)
        else:
            return strategy.sell(size=abs(diff))
    return None


def order_value(
    strategy,
    security: str,
    value: float,
    price: float = None
) -> Optional[int]:
    """
    按金额下单（市价单）

    Args:
        strategy: JQStrategy 实例
        security: 股票代码
        value: 金额（正数买入，负数卖出）
        price: 参考价格

    Returns:
        订单ID
    """
    if price is None or price == 0:
        price = strategy.datas[0].close[0]

    if value > 0:
        amount = int(value / price / 100) * 100  # 按手取整
        if amount > 0:
            return strategy.buy(size=amount)
    elif value < 0:
        amount = int(abs(value) / price / 100) * 100
        if amount > 0:
            return strategy.sell(size=amount)
    return None


def order_target_value(
    strategy,
    security: str,
    target_value: float
) -> Optional[int]:
    """
    调仓到目标市值

    Args:
        strategy: JQStrategy 实例
        security: 股票代码
        target_value: 目标持仓市值

    Returns:
        订单ID
    """
    current_value = strategy.getposition().size * strategy.datas[0].close[0]
    diff_value = target_value - current_value
    return order_value(strategy, security, diff_value)


def cancel_order(strategy, order_id: int) -> bool:
    """
    撤销订单

    Args:
        strategy: JQStrategy 实例
        order_id: 订单ID

    Returns:
        是否成功
    """
    return strategy._order_manager.cancel_order(order_id, strategy)


def get_open_orders(strategy, security: str = None) -> List:
    """获取未成交订单"""
    return strategy._order_manager.get_open_orders(security)


def get_orders(
    strategy,
    security: str = None,
    status: str = None
) -> List:
    """获取订单历史"""
    return strategy._order_manager.get_orders(security, status)


def get_trades(strategy, security: str = None) -> List:
    """获取成交记录"""
    return strategy._trades


# ============================================================
# 辅助函数
# ============================================================
def get_position(strategy, security: str = None) -> dict:
    """
    获取持仓（RQAlpha 风格）

    Returns:
        dict: {"security": str, "amount": int, "avg_cost": float}
    """
    data = strategy.datas[0]
    pos = strategy.getposition(data)
    return {
        "security": getattr(data, "_security", "unknown"),
        "amount": pos.size,
        "avg_cost": pos.price if pos.size > 0 else 0.0,
    }


def update_universe(strategy, securities: Union[str, List[str]]) -> None:
    """更新当前股票池"""
    if isinstance(securities, str):
        securities = [securities]
    strategy._universe = securities
