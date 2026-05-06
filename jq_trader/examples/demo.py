# coding=utf-8
"""
jq_trader 使用示例
==================

本文件展示 jq_trader 模块的用法。
"""

from jq_trader import JQStrategy, Backtester


# ============================================================
# 示例1：基础均线策略
# ============================================================
class MaCrossStrategy(JQStrategy):
    """
    均线交叉策略
    金叉买，死叉卖
    """

    def initialize(self, context):
        context.stock = "000001.SZ"
        context.ma5_window = 5
        context.ma20_window = 20
        self.g.hold = False

    def handle_data(self, context, data):
        ma5 = self.sma(context.ma5_window)
        ma20 = self.sma(context.ma20_window)

        if ma5 is None or ma20 is None:
            return

        if not self.g.hold and ma5 > ma20:
            self.order(context.stock, 100)
            self.g.hold = True
        elif self.g.hold and ma5 < ma20:
            self.order(context.stock, -100)
            self.g.hold = False


# ============================================================
# 示例2：使用定时任务
# ============================================================
class ScheduledStrategy(JQStrategy):
    """
    每日定时调仓策略
    """

    def initialize(self, context):
        context.stock = "000001.SZ"
        self.g.rebalance_done = False

    def handle_data(self, context, data):
        # 只在第一天买入
        if not self.g.rebalance_done:
            self.order_target(context.stock, 1000)
            self.g.rebalance_done = True


# ============================================================
# 示例3：PE阈值止盈策略
# ============================================================
class PEProtectionStrategy(JQStrategy):
    """
    PE阈值止盈策略
    价格低于10元买入，高于15元卖出
    """

    def initialize(self, context):
        context.stock = "000001.SZ"
        self.g.has_position = False
        self.g.buy_price = 0

    def handle_data(self, context, data):
        current_price = data.close[0]
        pos = self.get_position()

        if not self.g.has_position and current_price < 10:
            self.order(context.stock, 1000)
            self.g.has_position = True
            self.g.buy_price = current_price
            self.log(f"买入: 价格={current_price:.2f}")

        elif self.g.has_position and current_price > 15:
            self.order(context.stock, -pos["amount"])
            self.g.has_position = False
            self.log(f"卖出: 价格={current_price:.2f}, 成本={self.g.buy_price:.2f}")


# ============================================================
# 运行回测
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("运行示例1：均线交叉策略")
    print("=" * 60)

    bt = Backtester(
        strategy=MaCrossStrategy,
        stock="000001.SZ",
        start_date="20200101",
        end_date="20231231",
        initial_cash=1000000,
    )
    bt.run()
