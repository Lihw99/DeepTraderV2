# coding=utf-8
"""
adapter.py — 引擎适配器
========================
封装 Backtrader 操作，提供统一的接口适配。
"""

import backtrader as bt
from typing import Optional, Dict, Any

from jq_trader.utils import normalize_code


# ============================================================
# Backtrader 数据适配器
# ============================================================
class DataAdapter:
    """Backtrader 数据适配器"""

    @staticmethod
    def create_datafeed(df, fromdate=None, todate=None, **kwargs):
        """
        创建 Backtrader DataFeed

        Args:
            df: pandas DataFrame，需包含 date/open/high/low/close/volume 列
            fromdate: 起始日期
            todate: 结束日期

        Returns:
            bt.feeds.PandasData
        """
        import pandas as pd

        df_indexed = df.set_index(pd.to_datetime(df["date"]))
        return bt.feeds.PandasData(
            dataname=df_indexed,
            fromdate=fromdate,
            todate=todate,
            **kwargs
        )

    @staticmethod
    def set_commission(cerebro, commission: float, tax: float = None) -> None:
        """设置佣金和印花税"""
        cerebro.broker.setcommission(commission=commission)

        if tax is not None:
            def commission_scheeme():
                return bt.CommissionInfo(
                    commission=commission,
                    tax=tax,
                    mult=1.0,
                    margin=None,
                    name="Stock"
                )
            cerebro.broker.setcommission(commission=commission)

    @staticmethod
    def set_slippage(cerebro, slippage: float = 0.0) -> None:
        """设置滑点（简化实现）"""
        pass


# ============================================================
# Backtrader 策略适配器
# ============================================================
class StrategyAdapter:
    """Backtrader 策略适配器基类"""

    @staticmethod
    def get_broker(strategy):
        """获取 Broker"""
        return strategy.broker

    @staticmethod
    def get_cash(strategy) -> float:
        """获取可用资金"""
        return strategy.broker.get_cash()

    @staticmethod
    def get_value(strategy) -> float:
        """获取总资产"""
        return strategy.broker.getvalue()

    @staticmethod
    def get_position(strategy, data=None):
        """获取持仓"""
        if data is None:
            data = strategy.datas[0]
        return strategy.getposition(data)

    @staticmethod
    def get_orders(strategy) -> Dict[int, bt.Order]:
        """获取所有订单"""
        return strategy.order_dict

    @staticmethod
    def get_current_datetime(strategy) -> Optional:
        """获取当前日期时间"""
        if strategy.datas:
            return strategy.datas[0].datetime.date(0)
        return None


# ============================================================
# 配置适配器
# ============================================================
class ConfigAdapter:
    """配置适配器"""

    def __init__(self):
        self._config = {
            "benchmark": None,
            "commission": 0.0003,
            "tax": 0.001,
            "slippage": 0.0,
        }

    def set_benchmark(self, benchmark: str) -> None:
        """设置基准"""
        self._config["benchmark"] = benchmark

    def set_order_cost(self, commission: float, tax: float = None) -> None:
        """设置交易成本"""
        self._config["commission"] = commission
        if tax is not None:
            self._config["tax"] = tax

    def set_slippage(self, slippage: float) -> None:
        """设置滑点"""
        self._config["slippage"] = slippage

    def set_option(self, key: str, value: Any) -> None:
        """设置其他选项"""
        self._config[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置"""
        return self._config.get(key, default)


# ============================================================
# 缓存管理
# ============================================================
class CacheManager:
    """数据缓存管理器"""

    def __init__(self, cache_dir: str = None):
        import os
        if cache_dir is None:
            cache_dir = os.path.join(os.path.dirname(__file__), "cache")
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def get_cache_path(self, key: str) -> str:
        """获取缓存文件路径"""
        import hashlib
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return f"{self.cache_dir}/{key_hash}.parquet"

    def has_cache(self, key: str) -> bool:
        """检查缓存是否存在"""
        import os
        return os.path.exists(self.get_cache_path(key))

    def save_cache(self, key: str, df) -> None:
        """保存缓存"""
        import pandas as pd
        df.to_parquet(self.get_cache_path(key))

    def load_cache(self, key: str):
        """加载缓存"""
        import pandas as pd
        path = self.get_cache_path(key)
        if path:
            return pd.read_parquet(path)
        return None

    def clear_cache(self, key: str = None) -> None:
        """清除缓存"""
        import os
        if key:
            path = self.get_cache_path(key)
            if os.path.exists(path):
                os.remove(path)
        else:
            for f in os.listdir(self.cache_dir):
                if f.endswith(".parquet"):
                    os.remove(os.path.join(self.cache_dir, f))
