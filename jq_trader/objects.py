# coding=utf-8
"""
objects.py — 聚宽对象模型
===========================
实现 Portfolio, SubPortfolio, Position, Order, Trade, SecurityUnitData 等对象。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any


# ============================================================
# Portfolio / SubPortfolio
# ============================================================
@dataclass
class SubPortfolio:
    """子账户组合"""
    portfolio_id: str = "main"
    starting_cash: float = 1000000.0
    locked_cash: float = 0.0
    available_cash: float = 1000000.0
    total_value: float = 1000000.0
    positions: Dict[str, 'Position'] = None

    def __post_init__(self):
        if self.positions is None:
            self.positions = {}

    @property
    def portfolio_value(self) -> float:
        """组合总价值"""
        return self.total_value

    @property
    def daily_return(self) -> float:
        """日收益率（简化）"""
        if self.starting_cash > 0:
            return (self.total_value - self.starting_cash) / self.starting_cash
        return 0.0


@dataclass
class Portfolio:
    """主账户组合（兼容聚宽 context.portfolio）"""
    main_portfolio: SubPortfolio = None

    def __post_init__(self):
        if self.main_portfolio is None:
            self.main_portfolio = SubPortfolio()

    @property
    def available_cash(self) -> float:
        """可用资金"""
        return self.main_portfolio.available_cash

    @property
    def total_value(self) -> float:
        """总资产"""
        return self.main_portfolio.total_value

    @property
    def positions(self) -> Dict[str, 'Position']:
        """持仓字典"""
        return self.main_portfolio.positions

    @property
    def locked_cash(self) -> float:
        """锁定资金"""
        return self.main_portfolio.locked_cash

    @property
    def starting_cash(self) -> float:
        """初始资金"""
        return self.main_portfolio.starting_cash

    @property
    def daily_return(self) -> float:
        """日收益率"""
        return self.main_portfolio.daily_return

    def get_position(self, security: str) -> Optional['Position']:
        """获取持仓"""
        return self.positions.get(security)


# ============================================================
# Position
# ============================================================
@dataclass
class Position:
    """持仓对象"""
    security: str
    amount: int = 0
    avg_cost: float = 0.0
    price: float = 0.0
    value: float = 0.0
    is_long: bool = True
    is_short: bool = False

    def __post_init__(self):
        if self.amount < 0:
            self.is_long = False
            self.is_short = True

    @property
    def market_value(self) -> float:
        """市值"""
        return self.amount * self.price

    @property
    def unrealized_pnl(self) -> float:
        """浮动盈亏"""
        if self.amount == 0:
            return 0.0
        return (self.price - self.avg_cost) * self.amount

    @property
    def pnl(self) -> float:
        """盈亏（等同于浮动盈亏）"""
        return self.unrealized_pnl


# ============================================================
# Order
# ============================================================
@dataclass
class Order:
    """订单对象"""
    order_id: int
    security: str
    amount: int
    price: float = 0.0
    action: str = ""  # "buy" / "sell"
    status: str = "pending"  # "pending" / "open" / "filled" / "cancelled" / "rejected"
    order_type: str = "market"  # "market" / "limit"
    filled_amount: int = 0
    filled_price: float = 0.0
    create_time: datetime = None
    update_time: datetime = None

    def __post_init__(self):
        if self.create_time is None:
            self.create_time = datetime.now()
        if self.update_time is None:
            self.update_time = self.create_time

    @property
    def is_buy(self) -> bool:
        return self.action.lower() == "buy"

    @property
    def is_sell(self) -> bool:
        return self.action.lower() == "sell"

    @property
    def is_filled(self) -> bool:
        return self.status == "filled"

    @property
    def is_cancelled(self) -> bool:
        return self.status == "cancelled"

    @property
    def is_open(self) -> bool:
        return self.status == "open"


# ============================================================
# Trade
# ============================================================
@dataclass
class Trade:
    """成交记录"""
    trade_id: int
    order_id: int
    security: str
    price: float
    amount: int
    trade_time: datetime
    action: str  # "buy" / "sell"

    @property
    def is_buy(self) -> bool:
        return self.action.lower() == "buy"

    @property
    def is_sell(self) -> bool:
        return self.action.lower() == "sell"


# ============================================================
# SecurityUnitData
# ============================================================
class SecurityUnitData:
    """
    证券数据对象（兼容聚宽 data 对象）
    提供 price / open / close / high / low / volume 等属性访问
    """

    def __init__(self, data):
        self._data = data

    @property
    def close(self) -> float:
        """收盘价（当前bar）"""
        return self._data.close[0]

    @property
    def open(self) -> float:
        """开盘价"""
        return self._data.open[0]

    @property
    def high(self) -> float:
        """最高价"""
        return self._data.high[0]

    @property
    def low(self) -> float:
        """最低价"""
        return self._data.low[0]

    @property
    def volume(self) -> float:
        """成交量"""
        return self._data.volume[0]

    @property
    def datetime(self):
        """当前日期时间"""
        return self._data.datetime

    @property
    def date(self):
        """当前日期"""
        return self._data.datetime.date(0) if hasattr(self._data.datetime, 'date') else self._data.datetime[0]

    def __getitem__(self, key: str):
        """data["close"] → numpy数组"""
        if key == "close":
            return self._data.close
        elif key == "open":
            return self._data.open
        elif key == "high":
            return self._data.high
        elif key == "low":
            return self._data.low
        elif key == "volume":
            return self._data.volume
        raise KeyError(key)


# ============================================================
# Context 对象
# ============================================================
class Context:
    """
    策略执行上下文（兼容聚宽 context）
    """

    def __init__(self):
        self._current_dt: datetime = None
        self._portfolio: Portfolio = Portfolio()
        self._universe: List[str] = []
        self._user_data: Dict[str, Any] = {}

    @property
    def current_dt(self) -> datetime:
        """当前日期时间"""
        return self._current_dt

    @property
    def portfolio(self) -> Portfolio:
        """账户组合"""
        return self._portfolio

    @property
    def universe(self) -> List[str]:
        """股票池"""
        return self._universe

    def __getattr__(self, name: str):
        """用户自定义属性访问"""
        if name.startswith("_"):
            raise AttributeError(name)
        return self._user_data.get(name)

    def __setattr__(self, name: str, value):
        """用户自定义属性设置"""
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            self._user_data[name] = value

    def __getitem__(self, key: str):
        return self._user_data[key]

    def __setitem__(self, key: str, value):
        self._user_data[key] = value
