"""聊天记录解析器 —— 从微信聊天文本提取花销."""

import re
from decimal import Decimal

from .models import Entry, Expense, Settlement, r2

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
    entries: list[Entry] = []
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
            amount = r2(Decimal(m.group(1)))
            rest = m.group(2)

            # 提取 @提及
            mentions = MENTION_RE.findall(rest)
            # 去掉 @mention 部分得到纯描述
            description = MENTION_RE.sub('', rest).strip()

            if current_speaker:
                for name in mentions:
                    participants.add(name)
                participants.add(current_speaker)

                entries.append(Entry(
                    speaker=current_speaker,
                    amount=amount,
                    description=description,
                    mentions=mentions,
                ))
                expenses.append(Expense(
                    payer=current_speaker,
                    amount=amount,
                    description=description,
                    shared_by=mentions if mentions else None,
                ))
            continue

        # 否则视为发言者
        current_speaker = line
        participants.add(current_speaker)

    return Settlement(
        event_name=event_name,
        participants=sorted(participants),
        entries=entries,
        expenses=expenses,
    )
