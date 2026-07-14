"""领域模型 —— 数据类型与共享工具."""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP


def r2(d: Decimal) -> Decimal:
    """金额舍入到分."""
    return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


@dataclass
class Entry:
    """一条原始记账消息（解析中间产物）."""
    speaker: str        # 发送者
    amount: Decimal     # 金额
    description: str    # 用途描述
    mentions: list[str] # @提及的人


@dataclass
class Expense:
    """一笔花销记录."""
    payer: str
    amount: Decimal
    description: str
    shared_by: list[str] | None  # None = 全员分摊; [] = 无人分摊


@dataclass
class Transfer:
    """一条转账指令."""
    from_person: str
    to_person: str
    amount: Decimal


@dataclass
class Balance:
    """一人的收支汇总."""
    person: str
    paid: Decimal      # 垫付总额
    share: Decimal     # 应分摊总额
    net: Decimal       # 净额, 正=应收, 负=应付


@dataclass
class Settlement:
    """结算结果."""
    event_name: str
    participants: list[str]
    entries: list[Entry] = field(default_factory=list)
    expenses: list[Expense] = field(default_factory=list)
    balances: list[Balance] = field(default_factory=list)
    transfers: list[Transfer] = field(default_factory=list)
