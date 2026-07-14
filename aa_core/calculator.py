"""结算计算器 —— 净额清算算法."""

from decimal import Decimal

from .models import Balance, Settlement, Transfer, r2


def calculate(settlement: Settlement) -> Settlement:
    """计算净额清算，生成转账清单和每人余额.

    保证每对人之间最多一笔转账.
    """
    participants = settlement.participants
    expenses = settlement.expenses

    if not participants or not expenses:
        return settlement

    # 每人垫付总额 & 应分摊总额
    paid: dict[str, Decimal] = {p: Decimal('0') for p in participants}
    share: dict[str, Decimal] = {p: Decimal('0') for p in participants}

    for exp in expenses:
        paid[exp.payer] += exp.amount

        # None = 全员分摊
        sharers = exp.shared_by if exp.shared_by is not None else participants
        per_person = r2(exp.amount / Decimal(len(sharers)))
        for person in sharers:
            share[person] += per_person

    # 净额
    balances: list[Balance] = []
    net: dict[str, Decimal] = {}
    for p in participants:
        b = Balance(
            person=p,
            paid=paid[p],
            share=share[p],
            net=r2(paid[p] - share[p]),
        )
        balances.append(b)
        net[p] = b.net

    settlement.balances = balances

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
    from .parser import parse_chat
    return calculate(parse_chat(text))
