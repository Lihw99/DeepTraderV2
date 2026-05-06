# coding=utf-8
"""
data.py — 数据获取函数
======================
实现聚宽风格的数据 API：
  - get_price, history, attribute_history, get_bars
  - get_current_data
  - get_index_stocks, get_industry_stocks, get_concept_stocks
  - get_trade_days, get_all_securities
  - get_fundamentals, get_valuation
  - get_ticks, get_money_flow, get_billboard_list
  - get_price_limit
"""

import os
from datetime import datetime, timedelta
from typing import Union, List, Optional, Dict

import numpy as np
import pandas as pd

from jq_trader.utils import (
    jq_to_tushare_code,
    tushare_to_jq_code,
    normalize_code,
    get_tushare_api,
    get_data_dir,
    format_date,
)


# ============================================================
# 数据加载基础
# ============================================================
def _load_parquet(
    stock_code: str,
    start_date: str,
    end_date: str,
    adjust: str = "front"
) -> Optional[pd.DataFrame]:
    """
    从本地Parquet加载K线数据。
    数据目录结构: /mnt/d/A股全数据260320/个股日线/
    文件命名: {ts_code}_{start}_{end}.parquet
    """
    stock_data_dir = os.path.join(get_data_dir(), "个股日线")
    if not os.path.exists(stock_data_dir):
        print(f"[jq_trader] 本地数据目录不存在: {stock_data_dir}")
        return None

    start_dt = start_date.replace("-", "")
    end_dt = end_date.replace("-", "")

    prefix = stock_code + "_"
    matching_files = [
        f for f in os.listdir(stock_data_dir)
        if f.startswith(prefix) and f.endswith(".parquet")
    ]

    if not matching_files:
        return None

    all_rows = []
    for fname in matching_files:
        fpath = os.path.join(stock_data_dir, fname)
        try:
            df = pd.read_parquet(fpath)
            if "trade_date" in df.columns:
                df["trade_date"] = df["trade_date"].astype(str)
            elif "date" in df.columns:
                df["trade_date"] = df["date"].astype(str)

            df = df[
                (df["trade_date"] >= start_dt) & (df["trade_date"] <= end_dt)
            ]
            if len(df) > 0:
                rename = {}
                if "trade_date" in df.columns:
                    rename["trade_date"] = "date"
                if "vol" in df.columns:
                    rename["vol"] = "volume"
                if rename:
                    df = df.rename(columns=rename)

                cols = [c for c in ["date", "open", "high", "low", "close", "volume"] if c in df.columns]
                df = df[cols].copy()
                all_rows.append(df)
        except Exception as e:
            print(f"[jq_trader] 读取失败 {fname}: {e}")

    if not all_rows:
        return None

    result = pd.concat(all_rows, ignore_index=True)
    result = result.sort_values("date")
    result = result.drop_duplicates(subset=["date"], keep="first")
    result["date"] = pd.to_datetime(result["date"]).dt.strftime("%Y-%m-%d")

    return result


def _load_tushare(
    stock_code: str,
    start_date: str,
    end_date: str,
    adjust: str = "front"
) -> Optional[pd.DataFrame]:
    """通过Tushare Pro API加载K线数据"""
    pro = get_tushare_api()
    if pro is None:
        return None

    try:
        adjust_map = {"front": "1", "back": "2", "none": "3"}
        adj = adjust_map.get(adjust, "1")

        df = pro.daily(
            ts_code=stock_code,
            start_date=start_date.replace("-", ""),
            end_date=end_date.replace("-", ""),
        )
        if df is None or df.empty:
            return None

        df = df.sort_values("trade_date")
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.rename(columns={
            "trade_date": "date",
            "vol": "volume",
        })
        df["date"] = df["date"].dt.strftime("%Y-%m-%d")
        return df[["date", "open", "high", "low", "close", "volume"]]

    except Exception as e:
        print(f"[jq_trader] Tushare加载失败: {e}")
        return None


def load_stock_data(
    stock_code: str,
    start_date: str,
    end_date: str,
    adjust: str = "front",
) -> Optional[pd.DataFrame]:
    """统一数据加载入口：先本地Parquet，失败则Tushare"""
    start_date = start_date.replace("-", "") if start_date else ""
    end_date = end_date.replace("-", "") if end_date else ""

    ts_code = jq_to_tushare_code(stock_code) if "." in stock_code else stock_code

    df = _load_parquet(ts_code, start_date, end_date, adjust)
    if df is not None and len(df) > 0:
        print(f"[jq_trader] {ts_code}: 本地Parquet加载成功 ({len(df)}条)")
        return df

    print(f"[jq_trader] {ts_code}: 本地无数据，尝试Tushare...")
    df = _load_tushare(ts_code, start_date, end_date, adjust)
    if df is not None and len(df) > 0:
        print(f"[jq_trader] {ts_code}: Tushare加载成功 ({len(df)}条)")
        return df

    print(f"[jq_trader] {ts_code}: 数据加载失败")
    return None


# ============================================================
# 核心数据 API
# ============================================================
def get_price(
    security: Union[str, List[str]],
    count: int = None,
    start_date: str = None,
    end_date: str = None,
    frequency: str = "1d",
    fields: List[str] = None,
    fq: str = "front",
) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
    """
    获取股票历史行情（聚宽 get_price）

    Args:
        security: 股票代码，如 "000001.SZ" 或 ["000001.SZ", "000002.SZ"]
        count: 获取多少条（从 end_date 往前数）
        start_date: YYYYMMDD
        end_date: YYYYMMDD
        frequency: "1d" / "1m" / "5m" 等（目前仅支持日线）
        fields: ["open", "close", "high", "low", "volume"]
        fq: "front" / "back" / "none"

    Returns:
        单只股票: DataFrame
        多只股票: dict {code: DataFrame}
    """
    if frequency != "1d":
        raise NotImplementedError("目前仅支持日线 frequency='1d'")

    if end_date is None:
        end_date = datetime.today().strftime("%Y%m%d")

    if start_date is None and count is not None:
        fromdate = datetime.strptime(end_date, "%Y%m%d") - timedelta(days=int(count * 2))
        start_date = fromdate.strftime("%Y%m%d")
    elif start_date is None:
        start_date = "20150101"

    if isinstance(security, str):
        df = load_stock_data(security, start_date, end_date, fq)
        if df is None:
            return pd.DataFrame()
        if count is not None:
            df = df.tail(count)
        if fields:
            available = [f for f in fields if f in df.columns]
            df = df[["date"] + available]
        return df
    else:
        result = {}
        for code in security:
            df = load_stock_data(code, start_date, end_date, fq)
            if df is not None:
                if count is not None:
                    df = df.tail(count)
                if fields:
                    available = [f for f in fields if f in df.columns]
                    df = df[["date"] + available]
                result[code] = df
        return result


def get_bars(
    security: Union[str, List[str]],
    count: int = None,
    start_date: str = None,
    end_date: str = None,
    frequency: str = "1d",
    fields: List[str] = None,
    fq: str = "front",
) -> np.ndarray:
    """
    获取K线数据（返回numpy数组，聚宽 get_bars）

    Args:
        security: 股票代码
        count: 条数
        start_date / end_date: 日期范围
        frequency: "1d" / "1m" / "5m" 等
        fields: 返回字段
        fq: 复权方式

    Returns:
        numpy structured array
    """
    df = get_price(security, count, start_date, end_date, frequency, fields, fq)
    if df is None or df.empty:
        return np.array([])

    if isinstance(df, dict):
        # 多股票情况，返回第一个
        df = list(df.values())[0]

    return df.to_records(index=False)


def get_current_data(security: str = None) -> 'CurrentData':
    """
    获取当前行情数据（涨跌停、停牌、开盘价等）

    返回 CurrentData 对象，具有以下属性：
    - close / open / high / low / volume
    - is_st: 是否ST
    - is_paused: 是否停牌
    - up_limit / down_limit: 涨跌停价
    - pre_close: 昨收价
    """
    return CurrentData(security)


class CurrentData:
    """当前行情数据包装器"""

    def __init__(self, security: str = None):
        self._security = security
        self._data = None

    def set_data(self, data):
        self._data = data

    @property
    def close(self) -> float:
        if self._data:
            return self._data.close[0]
        return 0.0

    @property
    def open(self) -> float:
        if self._data:
            return self._data.open[0]
        return 0.0

    @property
    def high(self) -> float:
        if self._data:
            return self._data.high[0]
        return 0.0

    @property
    def low(self) -> float:
        if self._data:
            return self._data.low[0]
        return 0.0

    @property
    def volume(self) -> float:
        if self._data:
            return self._data.volume[0]
        return 0.0

    @property
    def is_st(self) -> bool:
        """是否ST（简化判断）"""
        return False

    @property
    def is_paused(self) -> bool:
        """是否停牌"""
        return self.volume == 0

    @property
    def up_limit(self) -> float:
        """涨停价"""
        return self.close * 1.10

    @property
    def down_limit(self) -> float:
        """跌停价"""
        return self.close * 0.90

    @property
    def pre_close(self) -> float:
        """昨收价"""
        if self._data and len(self._data.close) > 1:
            return self._data.close[-1]
        return self.close


# ============================================================
# 股票列表 / 交易日
# ============================================================
def get_all_securities(
    type_: str = "stock",
    date: str = None
) -> pd.DataFrame:
    """
    获取全量证券列表

    Returns:
        DataFrame: columns=[code, name, type, start_date, end_date]
    """
    data_dir = os.path.join(get_data_dir(), "个股日线")
    if not os.path.exists(data_dir):
        return pd.DataFrame(columns=["code", "name", "type", "start_date", "end_date"])

    files = os.listdir(data_dir)
    codes_seen = set()
    records = []
    for f in files:
        if not f.endswith(".parquet"):
            continue
        code_part = f.rsplit("_", 2)[0]
        if code_part in codes_seen:
            continue
        codes_seen.add(code_part)
        records.append({
            "code": code_part,
            "name": code_part,
            "type": "stock",
            "start_date": "",
            "end_date": "",
        })
    return pd.DataFrame(records)


def get_trade_days(
    start_date: str = None,
    end_date: str = None,
    count: int = None,
    is_open: str = "1"  # "1"=只返回交易日, "0"=只返回非交易日
) -> List[str]:
    """获取交易日列表

    Args:
        start_date: YYYYMMDD格式
        end_date: YYYYMMDD格式
        count: 取最近N个交易日
        is_open: "1"=只返回交易日, "0"=只返回非交易日
    """
    pro = get_tushare_api()
    if pro is None:
        return []

    try:
        if count:
            end_date = pd.Timestamp.today().strftime("%Y%m%d")
            start_date = (pd.Timestamp.today() - pd.Timedelta(days=count * 2)).strftime("%Y%m%d")

        df = pro.trade_cal(
            exchange='',  # 上交所
            start_date=start_date.replace("-", "") if start_date else None,
            end_date=end_date.replace("-", "") if end_date else None,
            is_open=is_open,
        )
        if df is not None and not df.empty:
            return df["cal_date"].sort_values().tolist()
    except Exception:
        pass
    return []


def get_index_stocks(index_code: str, date: str = None) -> List[str]:
    """获取指数成分股"""
    pro = get_tushare_api()
    if pro is None:
        return []

    index_map = {
        "000300.XSHG": "000300.SH",
        "000905.XSHG": "000905.SH",
        "000001.XSHG": "000001.SH",
        "399001.XSHE": "399001.SZ",
    }
    ts_index = index_map.get(index_code, index_code.replace("XSHG", ".SH").replace("XSHE", ".SZ"))

    try:
        df = pro.index_weight(index_code=ts_index)
        if df is not None and not df.empty:
            return df["con_code"].tolist()
    except Exception:
        pass
    return []


def get_industry_stocks(industry: str) -> List[str]:
    """获取行业成分股"""
    pro = get_tushare_api()
    if pro is None:
        return []

    try:
        # 不传 ts_code 和 list_status，否则返回空
        df = pro.stock_basic(fields="ts_code,industry")
        if df is not None and not df.empty and "industry" in df.columns:
            df = df[df["industry"] == industry]
            return df["ts_code"].tolist()
    except Exception:
        pass
    return []


def get_concept_stocks(concept: str) -> List[str]:
    """
    获取概念成分股（开盘啦题材，非东方财富）

    注意：开盘啦数据自2024年12月底停止更新，
    部分概念名称可能与聚宽不一致，请以实际返回结果为准。

    Args:
        concept: 概念名称，如 "AI低代码概念"、"大模型概念"、
                "合成生物"、或题材代码如 "000289.KP"

    Returns:
        成分股代码列表，如 ["000001.SZ", "600000.SH", ...]
    """
    pro = get_tushare_api()
    if pro is None:
        return []

    # 开盘啦最新数据日期
    FALLBACK_DATE = "20241227"

    # 缓存概念名称->ts_code映射（避免每次重新查询）
    # 概念数据变化不频繁，缓存在内存中
    if not hasattr(get_concept_stocks, '_concept_map'):
        get_concept_stocks._concept_map = {}
        # 先尝试近期交易日
        trade_days = get_trade_days(count=10)
        dates_to_try = trade_days + [FALLBACK_DATE]
        for date_str in dates_to_try:
            try:
                df = pro.kpl_concept_cons(trade_date=date_str.replace("-", ""))
                if df is not None and not df.empty:
                    for _, row in df[['ts_code', 'name']].drop_duplicates().iterrows():
                        if row['name'] not in get_concept_stocks._concept_map:
                            get_concept_stocks._concept_map[row['name']] = row['ts_code']
                    if len(get_concept_stocks._concept_map) > 50:
                        break
            except Exception:
                continue

    # 如果传入的是 KP 格式代码，直接查
    if concept.endswith(".KP"):
        try:
            df = pro.kpl_concept_cons(ts_code=concept)
            if df is not None and not df.empty:
                return df["con_code"].tolist()
        except Exception:
            pass
        return []

    # 通过名称查找 ts_code
    ts_code = None

    # 精确匹配
    if concept in get_concept_stocks._concept_map:
        ts_code = get_concept_stocks._concept_map[concept]

    # 模糊匹配（包含关系）
    if ts_code is None:
        for name, code in get_concept_stocks._concept_map.items():
            if concept in name or name in concept:
                ts_code = code
                break

    # 英文/拼音匹配（不区分大小写）
    if ts_code is None:
        concept_lower = concept.lower()
        for name, code in get_concept_stocks._concept_map.items():
            if name.lower() == concept_lower:
                ts_code = code
                break

    if ts_code is None:
        return []

    # 通过 ts_code 查询完整成分股
    try:
        df = pro.kpl_concept_cons(ts_code=ts_code)
        if df is not None and not df.empty:
            return df["con_code"].tolist()
    except Exception:
        pass

    return []


# ============================================================
# 财务 / 估值数据
# ============================================================
def get_valuation(
    securities: Union[str, List[str]] = None,
    start_date: str = None,
    end_date: str = None,
    count: int = None,
    fields: List[str] = None
) -> pd.DataFrame:
    """获取估值数据（PE/PB/市值等）"""
    pro = get_tushare_api()
    if pro is None:
        return pd.DataFrame()

    if securities is None:
        securities = []
    if isinstance(securities, str):
        securities = [securities]

    securities = [normalize_code(s) for s in securities]

    try:
        if count:
            end_dt = pd.Timestamp.today().strftime("%Y%m%d")
            start_dt = (pd.Timestamp.today() - pd.Timedelta(days=count * 3)).strftime("%Y%m%d")
        else:
            end_dt = end_date.replace("-", "") if end_date else pd.Timestamp.today().strftime("%Y%m%d")
            start_dt = start_date.replace("-", "") if start_date else (pd.Timestamp.today() - pd.Timedelta(days=365)).strftime("%Y%m%d")

        all_dfs = []
        for code in securities:
            df = pro.daily_basic(
                ts_code=normalize_code(code),
                start_date=start_dt,
                end_date=end_dt,
                fields="ts_code,trade_date,close,pe_ttm,pb,ps_ttm,market_cap,circ_market_cap",
            )
            if df is not None and not df.empty:
                df = df.rename(columns={
                    "ts_code": "code",
                    "close": "close",
                    "pe_ttm": "pe_ttm",
                    "pb": "pb",
                    "ps_ttm": "ps_ttm",
                    "market_cap": "market_cap",
                    "circ_market_cap": "circulating_market_cap",
                })
                df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d")
                all_dfs.append(df)

        if not all_dfs:
            return pd.DataFrame()

        result = pd.concat(all_dfs, ignore_index=True)
        return result.sort_values(["code", "trade_date"])
    except Exception as e:
        print(f"[jq_trader] get_valuation 失败: {e}")
        return pd.DataFrame()


def get_fundamentals(
    security: str = None,
    start_date: str = None,
    end_date: str = None,
    count: int = None,
    stat_date: str = None,
    fields: List[str] = None
) -> pd.DataFrame:
    """获取财务数据"""
    pro = get_tushare_api()
    if pro is None:
        return pd.DataFrame()

    security = normalize_code(security) if security else None

    try:
        df = pro.fina_indicator(ts_code=security, start_date=start_date, end_date=end_date)
        if df is not None and not df.empty:
            df["trade_date"] = pd.to_datetime(df["end_date"]).dt.strftime("%Y-%m-%d")
            return df
    except Exception:
        pass
    return pd.DataFrame()


# ============================================================
# 其他数据
# ============================================================
def get_ticks(
    security: str,
    date: str = None,
    count: int = None
) -> pd.DataFrame:
    """获取分笔数据（需要Tushare权限）"""
    pro = get_tushare_api()
    if pro is None:
        return pd.DataFrame()

    try:
        df = pro.tick_data(ts_code=normalize_code(security), trade_date=date)
        if df is not None and not df.empty:
            return df
    except Exception:
        pass
    return pd.DataFrame()


def get_money_flow(
    securities: Union[str, List[str]] = None,
    start_date: str = None,
    end_date: str = None,
    count: int = None
) -> pd.DataFrame:
    """获取资金流向"""
    pro = get_tushare_api()
    if pro is None:
        return pd.DataFrame()

    if securities is None:
        securities = []
    if isinstance(securities, str):
        securities = [securities]

    securities = [normalize_code(s) for s in securities]

    try:
        if count:
            end_dt = pd.Timestamp.today().strftime("%Y%m%d")
            start_dt = (pd.Timestamp.today() - pd.Timedelta(days=count * 2)).strftime("%Y%m%d")
        else:
            end_dt = (end_date or pd.Timestamp.today()).strftime("%Y%m%d")
            start_dt = (start_date or (pd.Timestamp.today() - pd.Timedelta(days=30))).strftime("%Y%m%d")

        all_dfs = []
        for code in securities:
            df = pro.moneyflow(ts_code=code, start_date=start_dt, end_date=end_dt)
            if df is not None and not df.empty:
                df = df.rename(columns={"ts_code": "code"})
                df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d")
                all_dfs.append(df)

        if all_dfs:
            return pd.concat(all_dfs, ignore_index=True).sort_values(["code", "trade_date"])
    except Exception:
        pass
    return pd.DataFrame()


def get_billboard_list(
    start_date: str = None,
    end_date: str = None,
    count: int = None
) -> pd.DataFrame:
    """获取龙虎榜数据"""
    pro = get_tushare_api()
    if pro is None:
        return pd.DataFrame()

    try:
        if count:
            end_dt = pd.Timestamp.today().strftime("%Y%m%d")
            start_dt = (pd.Timestamp.today() - pd.Timedelta(days=count)).strftime("%Y%m%d")
        else:
            end_dt = (end_date or pd.Timestamp.today()).strftime("%Y%m%d")
            start_dt = (start_date or (pd.Timestamp.today() - pd.Timedelta(days=1))).strftime("%Y%m%d")

        # top_list 需要 trade_date 参数（单日），遍历日期范围
        all_dfs = []
        current = pd.Timestamp(start_dt)
        end = pd.Timestamp(end_dt)
        while current <= end:
            date_str = current.strftime("%Y%m%d")
            try:
                df = pro.top_list(trade_date=date_str)
                if df is not None and not df.empty:
                    all_dfs.append(df)
            except Exception:
                pass
            current += pd.Timedelta(days=1)

        if all_dfs:
            return pd.concat(all_dfs, ignore_index=True)
    except Exception:
        pass
    return pd.DataFrame()


def get_price_limit(security: str = None) -> pd.DataFrame:
    """获取涨跌停价"""
    pro = get_tushare_api()
    if pro is None:
        return pd.DataFrame()

    security = normalize_code(security) if security else None

    try:
        if security:
            # 有指定股票，查其所在交易所最近的交易日
            # 涨跌停数据通常当天收盘后才有，尝试最近5个交易日
            trade_days = get_trade_days(count=5)
            for date_str in reversed(trade_days):
                try:
                    df = pro.stk_limit(ts_code=security, trade_date=date_str.replace("-", ""))
                    if df is not None and not df.empty:
                        df = df.rename(columns={"ts_code": "code"})
                        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d")
                        return df
                except Exception:
                    continue
        else:
            # 无指定股票，返回所有涨跌停（数据量大，限制返回）
            end_dt = pd.Timestamp.today().strftime("%Y%m%d")
            start_dt = (pd.Timestamp.today() - pd.Timedelta(days=5)).strftime("%Y%m%d")
            df = pro.stk_limit(trade_date=end_dt)
            if df is not None and not df.empty:
                df = df.rename(columns={"ts_code": "code"})
                df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y-%m-%d")
                return df
    except Exception:
        pass

    return pd.DataFrame()
