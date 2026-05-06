# coding=utf-8
"""
utils.py — 代码转换、日期工具
"""

import os
import pickle
from datetime import datetime
from typing import Union, List, Optional

# 自动加载 .env 文件（如果存在）
_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(_env_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        # python-dotenv 未安装，手动解析 .env 文件
        with open(_env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()

# ============================================================
# 常量
# ============================================================
STOCK_CODE_MAP = {
    "XSHE": "SZ",
    "XSHG": "SH",
}
REVERSE_CODE_MAP = {
    "SZ": "XSHE",
    "SH": "XSHG",
}

DEFAULT_FQ = "front"
DATA_DIR = "/mnt/d/A股全数据260320/"

# Tushare token（必须通过环境变量设置，不直接写在代码中）
# 在运行前执行：export TUSHARE_TOKEN="your_token_here"
TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN", "")
TUSHARE_URL = "http://121.40.135.59:8010/"


# ============================================================
# 代码转换
# ============================================================
def jq_to_tushare_code(code: str) -> str:
    """聚宽代码 → Tushare代码，如 000001.XSHE → 000001.SZ"""
    if "." in code:
        symbol, market = code.split(".")
        if market in STOCK_CODE_MAP:
            return f"{symbol}.{STOCK_CODE_MAP[market]}"
    return code


def tushare_to_jq_code(code: str) -> str:
    """Tushare代码 → 聚宽代码，如 000001.SZ → 000001.XSHE"""
    if "." in code:
        symbol, market = code.split(".")
        if market in REVERSE_CODE_MAP:
            return f"{symbol}.{REVERSE_CODE_MAP[market]}"
    return code


def normalize_code(code: str) -> str:
    """
    标准化证券代码格式。

    Args:
        code: 支持 6 位数字 / 聚宽格式 / Tushare 格式

    Returns:
        标准化代码，如 "000001.SZ"
    """
    if not code:
        return code

    if "." in code and len(code) == 10:
        return code.upper()

    if code.isdigit() and len(code) == 6:
        if code.startswith(("0", "3")):
            return f"{code}.SZ"
        else:
            return f"{code}.SH"

    if "." in code:
        symbol, suffix = code.split(".")
        suffix = suffix.upper()
        if suffix == "XSHE":
            return f"{symbol}.SZ"
        elif suffix == "XSHG":
            return f"{symbol}.SH"
    return code


def get_code_part(code: str) -> str:
    """获取股票代码（纯数字部分）"""
    if "." in code:
        return code.split(".")[0]
    return code


# ============================================================
# 日期工具
# ============================================================
def parse_date(date_str: Union[str, datetime]) -> datetime:
    """解析 YYYYMMDD 格式日期"""
    if isinstance(date_str, datetime):
        return date_str
    if isinstance(date_str, int):
        date_str = str(date_str)
    return datetime.strptime(str(date_str), "%Y%m%d")


def format_date(dt: datetime, fmt: str = "%Y-%m-%d") -> str:
    """格式化日期为字符串"""
    if isinstance(dt, str):
        return dt
    return dt.strftime(fmt)


def date_to_ymd(dt: datetime) -> str:
    """日期转 YYYYMMDD 格式"""
    return dt.strftime("%Y%m%d")


def normalize_frequency(freq: str) -> str:
    """将聚宽频率字符串转为标准格式"""
    freq = freq.lower()
    if freq == "1d":
        return "D"
    elif freq.endswith("m"):
        return freq
    elif freq.endswith("d"):
        return "D"
    return "D"


# ============================================================
# g 对象持久化
# ============================================================
G_STORAGE_PATH = os.path.join(os.path.dirname(__file__), "cache", "g_objects.pkl")


class GStorage:
    """g 对象持久化存储"""

    @staticmethod
    def save(g_obj: dict, strategy_name: str = "default") -> None:
        """保存 g 对象到磁盘"""
        cache_dir = os.path.join(os.path.dirname(__file__), "cache")
        os.makedirs(cache_dir, exist_ok=True)
        filepath = os.path.join(cache_dir, f"g_{strategy_name}.pkl")
        try:
            with open(filepath, "wb") as f:
                pickle.dump(g_obj, f)
        except Exception as e:
            print(f"[jq_trader] g 对象保存失败: {e}")

    @staticmethod
    def load(strategy_name: str = "default") -> dict:
        """从磁盘加载 g 对象"""
        filepath = os.path.join(os.path.dirname(__file__), "cache", f"g_{strategy_name}.pkl")
        if os.path.exists(filepath):
            try:
                with open(filepath, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"[jq_trader] g 对象加载失败: {e}")
        return {}

    @staticmethod
    def clear(strategy_name: str = "default") -> None:
        """清除持久化的 g 对象"""
        filepath = os.path.join(os.path.dirname(__file__), "cache", f"g_{strategy_name}.pkl")
        if os.path.exists(filepath):
            os.remove(filepath)


# ============================================================
# 其他工具
# ============================================================
def get_tushare_api():
    """获取 Tushare Pro API 实例"""
    try:
        import tushare as ts
        pro = ts.pro_api(TUSHARE_TOKEN)
        pro._DataApi__http_url = TUSHARE_URL
        return pro
    except Exception as e:
        print(f"[jq_trader] Tushare 初始化失败: {e}")
        return None


def get_data_dir() -> str:
    """获取数据目录"""
    return DATA_DIR


def set_data_dir(path: str) -> None:
    """设置数据目录"""
    global DATA_DIR
    DATA_DIR = path


# ============================================================
# 市场判断工具
# ============================================================
def is_kcb_code(code: str) -> bool:
    """判断是否为科创板股票"""
    code = normalize_code(code)
    # 科创板: 688xxx.SH
    if code.endswith(".SH"):
        return code.startswith("688")
    return False


def is_cyb_code(code: str) -> bool:
    """判断是否为创业板股票"""
    code = normalize_code(code)
    # 创业板: 300xxx.SZ
    if code.endswith(".SZ"):
        return code.startswith("300")
    return False


def is主板_code(code: str) -> bool:
    """判断是否为主板股票（沪市主板或深市主板）"""
    code = normalize_code(code)
    if code.endswith(".SH"):
        # 沪市主板: 600xxx, 601xxx, 603xxx, 605xxx
        symbol = code.split(".")[0]
        return symbol.startswith(("600", "601", "603", "605"))
    elif code.endswith(".SZ"):
        # 深市主板: 000xxx, 001xxx
        symbol = code.split(".")[0]
        return symbol.startswith(("000", "001"))
    return False


def is_bj_code(code: str) -> bool:
    """判断是否为北交所股票"""
    code = normalize_code(code)
    # 北交所: 8xxxxx.BJ
    return code.endswith(".BJ") or code.startswith("8") and len(code) == 6
