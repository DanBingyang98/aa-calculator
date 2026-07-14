"""AA 算账核心逻辑：聊天记录解析 + 净额清算."""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
import re


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class Expense:
    """一笔花销记录."""
    payer: str
    amount: Decimal
    description: str
    shared_by: list[str]  # 分摊者名单


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
    expenses: list[Expense] = field(default_factory=list)
    balances: list[Balance] = field(default_factory=list)
    transfers: list[Transfer] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

EXPENSE_RE = re.compile(r'^(\d+(?:\.\d{1,2})?)\s+(\S.*)')
MENTION_RE = re.compile(r'@(\S+)')


def parse_chat(text: str) -> Settlement:
    """从微信聊天记录解析出 Settlement.

    规则:
    - 以 # 开头的行作为活动名称
    - 匹配 "金额 用途 [@某人 ...]" 格式的行为花销
    - 其他非空行视为当前发言者
    - 参与者从发言者和 @提及中自动推断
    """
    lines = [line.strip() for line in text.strip().split('\n')]
    lines = [line for line in lines if line]  # 去空行

    event_name = ''
    expenses: list[Expense] = []
    current_speaker = ''
    participants: set[str] = set()

    for line in lines:
        # 活动名称
        if line.startswith('#'):
            event_name = line[1:].strip()
            continue

        # 花销行: "金额 用途 [@...]"
        m = EXPENSE_RE.match(line)
        if m:
            amount = Decimal(m.group(1)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            rest = m.group(2)

            # 提取 @提及
            mentions = MENTION_RE.findall(rest)
            # 去掉 @mention 部分得到纯描述
            description = MENTION_RE.sub('', rest).strip()

            if current_speaker:
                payer = current_speaker
                participants.add(payer)
                for name in mentions:
                    participants.add(name)

                shared_by = mentions if mentions else []  # 空列表表示全员分摊
                expenses.append(Expense(
                    payer=payer,
                    amount=amount,
                    description=description,
                    shared_by=shared_by,
                ))
            continue

        # 否则视为发言者
        current_speaker = line
        participants.add(current_speaker)

    return Settlement(
        event_name=event_name,
        participants=sorted(participants),
        expenses=expenses,
    )


# ---------------------------------------------------------------------------
# Settlement calculator
# ---------------------------------------------------------------------------

def calculate(settlement: Settlement) -> Settlement:
    """计算净额清算，生成转账清单."""
    participants = settlement.participants
    expenses = settlement.expenses

    if not participants or not expenses:
        return settlement

    # 每人垫付总额
    paid: dict[str, Decimal] = {p: Decimal('0') for p in participants}
    # 每人应分摊总额
    share: dict[str, Decimal] = {p: Decimal('0') for p in participants}

    for exp in expenses:
        paid[exp.payer] += exp.amount

        sharers = exp.shared_by if exp.shared_by else participants
        per_person = (exp.amount / Decimal(len(sharers))).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        for person in sharers:
            share[person] += per_person

    # 净额: 正数 = 应收, 负数 = 应付
    balances: list[Balance] = []
    for p in participants:
        b = Balance(
            person=p,
            paid=paid[p],
            share=share[p],
            net=(paid[p] - share[p]).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        )
        balances.append(b)

    settlement.balances = balances

    # 净额字典（贪心匹配用）
    net = {b.person: b.net for b in balances}

    # 贪心匹配: 债权人(正) vs 债务人(负)
    creditors = sorted(
        [(p, net[p]) for p in participants if net[p] > 0],
        key=lambda x: -x[1],
    )
    debtors = sorted(
        [(p, -net[p]) for p in participants if net[p] < 0],
        key=lambda x: -x[1],
    )

    transfers: list[Transfer] = []
    ci = 0
    di = 0
    while ci < len(creditors) and di < len(debtors):
        creditor_name, credit_amt = creditors[ci]
        debtor_name, debt_amt = debtors[di]

        transfer_amt = min(credit_amt, debt_amt)

        transfers.append(Transfer(
            from_person=debtor_name,
            to_person=creditor_name,
            amount=transfer_amt,
        ))

        # 更新余额
        credit_amt -= transfer_amt
        debt_amt -= transfer_amt

        if credit_amt < Decimal('0.01'):
            ci += 1
        else:
            creditors[ci] = (creditor_name, credit_amt)

        if debt_amt < Decimal('0.01'):
            di += 1
        else:
            debtors[di] = (debtor_name, debt_amt)

    settlement.transfers = transfers
    return settlement


def settle(text: str) -> Settlement:
    """一步完成：解析 + 计算."""
    s = parse_chat(text)
    return calculate(s)
