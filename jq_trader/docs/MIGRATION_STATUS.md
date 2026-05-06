# jq_trader 迁移状态日志

> 本文档记录聚宽API到jq_trader的迁移进度，供后续开发者和AI参考。

---

## 迁移阶段

| 阶段 | 名称 | 状态 | 完成度 |
|------|------|------|--------|
| 第一阶段 | jq_lite.py 轻量复刻 | ✅ 完成 | 100% |
| 第二阶段 | jq_trader 模块化 + 接口兼容层 | ✅ 完成 | ~90% |
| 第三阶段 | 自研引擎 + 完全兼容 | ⏳ 待开始 | 0% |

---

## 第二阶段迁移清单

### ✅ 已完成 (90%)

#### 1. 运行环境层
| 聚宽API | jq_trader实现 | 状态 | 文件 |
|---------|---------------|------|------|
| `initialize(context)` | `JQStrategy.initialize()` | ✅ | env.py |
| `handle_data(context, data)` | `JQStrategy.handle_data()` | ✅ | env.py |
| `run_daily(time_str)` | `@run_daily()` 装饰器 | ✅ | env.py |
| `run_weekly(weekday, time_str)` | `@run_weekly()` 装饰器 | ✅ | env.py |
| `run_monthly(day, time_str)` | `@run_monthly()` 装饰器 | ✅ | env.py |
| `before_trading_start(context)` | `JQStrategy.before_trading_start()` | ✅ | env.py |
| `after_trading_end(context)` | `JQStrategy.after_trading_end()` | ✅ | env.py |
| `context.current_dt` | `context._current_dt` | ✅ | env.py |
| `context.portfolio` | `JQStrategy._context.portfolio` | ✅ | objects.py |
| `context.universe` | `JQStrategy._context.universe` | ✅ | objects.py |
| `self.g` 全局变量 | `JQStrategy.g` (pickle持久化) | ✅ | env.py |

#### 2. 数据获取层
| 聚宽API | jq_trader实现 | 状态 | 文件 |
|---------|---------------|------|------|
| `get_price()` | `data.get_price()` | ✅ | data.py |
| `history(count, unit, field)` | `JQStrategy.history()` | ✅ | env.py |
| `attribute_history()` | `JQStrategy.attribute_history()` | ✅ | env.py |
| `get_bars()` | `data.get_bars()` | ✅ | data.py |
| `get_current_data()` | `data.get_current_data()` | ✅ | data.py |
| `get_all_securities()` | `data.get_all_securities()` | ✅ | data.py |
| `get_trade_days()` | `data.get_trade_days()` | ✅ | data.py |
| `get_index_stocks()` | `data.get_index_stocks()` | ✅ | data.py |
| `get_valuation()` | `data.get_valuation()` | ✅ | data.py |
| `get_fundamentals()` | `data.get_fundamentals()` | ✅ | data.py |
| `get_money_flow()` | `data.get_money_flow()` | ✅ | data.py |
| `get_billboard_list()` | `data.get_billboard_list()` | ✅ | data.py |
| `get_price_limit()` | `data.get_price_limit()` | ✅ | data.py |

#### 3. 交易函数层
| 聚宽API | jq_trader实现 | 状态 | 文件 |
|---------|---------------|------|------|
| `order(security, amount)` | `JQStrategy.order()` | ✅ | env.py |
| `order_target(security, amount)` | `JQStrategy.order_target()` | ✅ | env.py |
| `order_value(security, value)` | `JQStrategy.order_value()` | ✅ | env.py |
| `order_target_value(security, value)` | `JQStrategy.order_target_value()` | ✅ | env.py |
| `cancel_order(order_id)` | `JQStrategy.cancel_order()` | ✅ | env.py |
| `get_open_orders()` | `JQStrategy.get_open_orders()` | ✅ | env.py |
| `get_orders()` | `JQStrategy.get_orders()` | ✅ | env.py |
| `get_position(security)` | `JQStrategy.get_position()` | ✅ | env.py |
| `MarketOrder` | `trade.MarketOrder` | ✅ | trade.py |
| `LimitOrder` | `trade.LimitOrder` | ✅ | trade.py |

#### 4. 对象模型层
| 聚宽对象 | jq_trader实现 | 状态 | 文件 |
|----------|---------------|------|------|
| `Portfolio` | `objects.Portfolio` | ✅ | objects.py |
| `SubPortfolio` | `objects.SubPortfolio` | ✅ | objects.py |
| `Position` | `objects.Position` | ✅ | objects.py |
| `Order` | `objects.Order` | ✅ | objects.py |
| `Trade` | `objects.Trade` | ✅ | objects.py |
| `Context` | `objects.Context` | ✅ | objects.py |
| `SecurityUnitData` | `objects.SecurityUnitData` | ✅ | objects.py |

#### 5. 辅助配置层
| 聚宽API | jq_trader实现 | 状态 | 文件 |
|---------|---------------|------|------|
| `set_benchmark(security)` | `JQStrategy.set_benchmark()` | ✅ | env.py |
| `set_order_cost(commission, tax)` | `JQStrategy.set_order_cost()` | ✅ | env.py |
| `set_slippage()` | `JQStrategy.set_slippage()` | ✅ | env.py |
| `record()` | `JQStrategy.record()` | ✅ | env.py |
| `log()` | `JQStrategy.log()` | ✅ | env.py |
| `send_message()` | `JQStrategy.send_message()` | ✅ | env.py |

#### 6. 数据适配层
| 功能 | 状态 | 说明 |
|------|------|------|
| 代码转换 XSHE→SZ, XSHG→SH | ✅ | utils.py |
| 复权方式(前复权/后复权/不复权) | ✅ | data.py |
| 本地Parquet + Tushare双数据源 | ✅ | data.py |
| Tushare API封装 | ✅ | utils.py |

---

### ⚠️ 部分完成 / 有缺陷

| API | 问题 | 优先级 |
|-----|------|--------|
| `get_ticks()` | 需要Tushare Pro+权限，返回空 | 低 |
| 非标准K线周期合成 | 需要K线合成逻辑 | 中 |

### ❌ 未实现

| 聚宽API | 说明 | 优先级 |
|---------|------|--------|
| `handle_tick(context, tick)` | 需要实时数据流，架构不同 | 低 |
| `context.subportfolios` | 多子账户支持 | 低 |
| `order(order_id, amount, price, style)` | 已有部分支持 | - |
| 因子库(jqlib) | 庞大工程，按需实现 | 低 |
| 实时交易模式 | 仅支持回测 | 低 |

---

## 技术债务

1. **Backtrader依赖**: 目前完全依赖Backtrader作为引擎，第三阶段需要自研
2. **数据缓存**: 尚未实现本地缓存机制
3. **错误处理**: 部分API的错误处理较简单

---

## 下一步行动 (第三阶段前)

1. [ ] 实现 `set_slippage` 滑点模型
2. [ ] 完善多标的交易支持
3. [ ] 添加数据缓存机制

---

## 关键文件

```
jq_trader/
├── env.py          # 核心策略基类
├── data.py         # 数据API
├── trade.py        # 交易API
├── objects.py      # 对象模型
├── adapter.py      # Backtrader适配器
├── backtester.py   # 回测运行器
├── utils.py        # 工具函数
└── docs/
    ├── README.md              # 本文档
    ├── MIGRATION_STATUS.md     # 本文件
    ├── ARCHITECTURE.md          # 架构文档
    └── API_REFERENCE.md        # API对照表
```

---

## 更新日志

| 日期 | 操作 | 说明 |
|------|------|------|
| 2026-05-06 | 初始化文档 | 创建迁移状态文档 |
| 2026-05-06 | 修复get_trade_days | is_open参数错误("A"→"1") |
| 2026-05-06 | 完成核心API | 完成90%的API翻译 |
| 2026-05-06 | 完善文档 | 完成ARCHITECTURE.md和API_REFERENCE.md |
| 2026-05-06 | 修复get_industry_stocks | stock_basic参数错误，返回空数据 |
| 2026-05-06 | 修复get_billboard_list | top_list需要trade_date参数（非日期范围） |
| 2026-05-06 | 修复get_price_limit | 遍历最近交易日查找涨跌停数据 |
| 2026-05-06 | 修复get_concept_stocks | 改用kpl_concept_cons（开盘啦），修复API和匹配逻辑 |
| 2026-05-06 | 补全set_slippage | 实现滑点模型（perc/fixed两种模式） |
| 2026-05-06 | 补全科创板保护价 | 添加科创板价格监控警告 |
| 2026-05-06 | 补全市场判断工具 | is_kcb_code, is_cyb_code, is主板_code, is_bj_code |
