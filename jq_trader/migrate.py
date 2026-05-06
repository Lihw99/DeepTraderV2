# migrate.py — 聚宽策略自动迁移工具
# 用法：python migrate.py 原始策略.py -o 迁移后策略.py

import re
import sys
import argparse
from pathlib import Path


def migrate_code(code: str) -> str:
    """
    聚宽策略代码 -> jq_trader 代码
    自动转换 6 处
    """
    lines = code.split('\n')
    result = []

    # 第一行添加 import
    result.append('from jq_trader import JQStrategy, Backtester')
    result.append('')

    # 状态机
    in_class = False
    in_function = None  # "initialize" or "handle_data"
    indent_level = 0

    for line in lines:
        stripped = line.strip()
        original = line

        # 跳过注释行（保留）
        if stripped.startswith('#'):
            result.append(line)
            continue

        # 空行保留
        if stripped == '':
            result.append('')
            continue

        # ===== 处理函数定义 =====
        # def initialize(context): 或 def initialize(self, context):
        if re.match(r'^def\s+initialize\s*\(', stripped):
            if not in_class:
                result.append('class MaCrossStrategy(JQStrategy):')
                in_class = True
            # 改成 def initialize(self, context):
            result.append('    def initialize(self, context):')
            in_function = "initialize"
            indent_level = 4
            continue

        # def handle_data(context, data):
        if re.match(r'^def\s+handle_data\s*\(', stripped):
            result.append('    def handle_data(self, context, data):')
            in_function = "handle_data"
            indent_level = 4
            continue

        # 其他 def xxx(context):
        if re.match(r'^def\s+\w+\s*\(context\):', stripped):
            # 可能是定时任务
            func_name = re.search(r'^def\s+(\w+)', stripped).group(1)
            result.append('    ' + line.lstrip().replace(f'(context):', f'(self, context):'))
            in_function = func_name
            indent_level = 4
            continue

        # ===== 处理函数体内的代码 =====
        if in_function in ("initialize", "handle_data") or in_class:
            # g.xxx -> self.g.xxx (多种模式)
            if 'self.g.' not in line:
                # g.short (单独成词)
                line = re.sub(r'\bg\.', 'self.g.', line)
                # (g.xxx) 括号内
                line = re.sub(r'\(g\.', '(self.g.', line)

            # context.portfolio.positions[xxx] -> self.get_position(xxx)
            if 'context.portfolio.positions[' in line:
                match = re.search(r'context\.portfolio\.positions\[(.+?)\]', line)
                if match:
                    stock = match.group(1)
                    line = line.replace(
                        f'context.portfolio.positions[{stock}]',
                        f'self.get_position({stock})'
                    )

            # attribute_history(xxx, count, ...) -> self.history(count, ..., df=True)
            if 'attribute_history(' in line:
                # attribute_history(context.stock, 20, unit="1d", fields=["close"])
                # -> self.history(20, fields="close", df=True)
                match = re.search(r'attribute_history\(([^,]+),\s*(\d+)', line)
                if match:
                    # stock = match.group(1)  # 忽略第一个参数
                    count = match.group(2)
                    line = re.sub(
                        r'attribute_history\([^)]+\)',
                        f'self.history({count}, fields="close", df=True)',
                        line
                    )
                    # 移除unit参数（jq_trader只支持日线）
                    if 'unit=' in line:
                        line = re.sub(r',?\s*unit="[^"]*"', '', line)

            # 如果行有内容，需要缩进
            if stripped:
                # 计算原始缩进
                raw_indent = len(original) - len(original.lstrip())
                if raw_indent > 0:
                    result.append(' ' * (indent_level + raw_indent) + line.lstrip())
                else:
                    result.append('    ' * (in_class and 1 or 0) + line.lstrip())
            continue

        # 默认：原样输出（加上类内的缩进）
        result.append(line)

    # 清理连续空行
    final = []
    prev_empty = False
    for line in result:
        if line.strip() == '':
            if not prev_empty:
                final.append(line)
            prev_empty = True
        else:
            final.append(line)
            prev_empty = False

    return '\n'.join(final)


def add_run_block(code: str) -> str:
    """添加 Backtester 运行代码"""
    if 'bt.run()' in code or 'Backtester(' in code:
        return code

    run_block = '''

# ========== 以下为自动添加的运行代码 ==========
if __name__ == "__main__":
    bt = Backtester(
        strategy=MaCrossStrategy,
        stock="000001.SZ",        # 修改为你的股票
        start_date="20200101",    # 修改为你的开始日期
        end_date="20231231",      # 修改为你的结束日期
        initial_cash=1000000,     # 修改为你的初始资金
    )
    bt.run()
'''

    return code + run_block


def main():
    parser = argparse.ArgumentParser(description='聚宽策略 -> jq_trader 自动迁移工具')
    parser.add_argument('input', help='输入文件（聚宽策略.py）')
    parser.add_argument('-o', '--output', help='输出文件路径')
    parser.add_argument('-r', '--run', action='store_true', help='自动添加运行代码')

    args = parser.parse_args()

    # 读取输入
    input_path = Path(args.input)
    if not input_path.exists():
        print(f'错误：文件不存在 {args.input}')
        sys.exit(1)

    code = input_path.read_text(encoding='utf-8')
    print(f'读取文件：{args.input}')

    # 迁移
    print('正在进行代码转换...')
    migrated = migrate_code(code)

    if args.run:
        print('添加运行代码...')
        migrated = add_run_block(migrated)

    # 输出
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(migrated, encoding='utf-8')
        print(f'已保存：{args.output}')
    else:
        print('\n' + '='*60)
        print('迁移结果：')
        print('='*60)
        print(migrated)

    print('\n转换完成！')


if __name__ == "__main__":
    main()
