# 安装与配置

## 系统要求

- Python 3.8+
- Windows / Linux / Mac

## 安装依赖

```bash
pip install backtrader pandas numpy tushare python-dotenv
```

## 获取 Tushare Token

1. 访问 [tushare.pro](https://tushare.pro)
2. 注册账号（免费）
3. 登录后进入「个人中心」→「API TOKEN」
4. 复制 Token

## 配置 Token

在 `DeepTraderV2` 目录下创建 `.env` 文件：

```bash
# Windows 创建 .env
echo TUSHARE_TOKEN=你的token > .env

# 或者直接用文本编辑器创建
```

`.env` 文件内容：

```
TUSHARE_TOKEN=你的token
```

> **重要**：`TUSHARE_TOKEN=` 后面不要加引号，直接写 token

## 验证安装

```bash
cd DeepTraderV2
python -c "from jq_trader import data; print('OK:', len(data.get_trade_days(count=5)), 'days')"
```

如果输出类似 `OK: 5 days` 说明安装成功。

如果报错：
- `ModuleNotFoundError` → 重新 `pip install`
- `Token error` → 检查 `.env` 文件是否正确
- 其他 → 查看常见问题

## 数据说明

默认使用 Tushare API 获取数据（免费额度足够）。

如需本地数据：
1. 下载 A 股 Parquet 数据到 `/mnt/d/A股全数据260320/`
2. 代码会优先使用本地数据

---

## 快速验证回测

```bash
cd DeepTraderV2
python jq_trader/examples/demo.py
```

正常情况下会输出回测结果。
