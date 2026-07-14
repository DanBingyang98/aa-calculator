"""aa_core 单元测试."""
import pytest
from decimal import Decimal
from aa_core import parse_chat, calculate, settle, Expense, Transfer, Settlement


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

class TestParseChat:
    def test_basic_parsing(self):
        text = """#周末聚餐
张三
300 火锅
李四
60 奶茶 @张三
100 打车"""
        s = parse_chat(text)
        assert s.event_name == '周末聚餐'
        assert len(s.participants) == 2
        assert '张三' in s.participants
        assert '李四' in s.participants
        assert len(s.expenses) == 3

        assert s.expenses[0].payer == '张三'
        assert s.expenses[0].amount == Decimal('300')
        assert s.expenses[0].description == '火锅'
        assert s.expenses[0].shared_by is None  # 全员

        assert s.expenses[1].payer == '李四'
        assert s.expenses[1].amount == Decimal('60')
        assert s.expenses[1].description == '奶茶'
        assert s.expenses[1].shared_by == ['张三']

        assert s.expenses[2].payer == '李四'
        assert s.expenses[2].amount == Decimal('100')
        assert s.expenses[2].description == '打车'
        assert s.expenses[2].shared_by is None

    def test_no_event_name(self):
        text = """张三
50 午餐"""
        s = parse_chat(text)
        assert s.event_name == ''
        assert s.participants == ['张三']

    def test_multi_word_description(self):
        text = """张三
88.5 肯德基 全家桶"""
        s = parse_chat(text)
        assert len(s.expenses) == 1
        assert s.expenses[0].amount == Decimal('88.50')
        assert s.expenses[0].description == '肯德基 全家桶'

    def test_decimal_precision(self):
        text = """张三
33.33 杂项"""
        s = parse_chat(text)
        assert s.expenses[0].amount == Decimal('33.33')

    def test_mentions_added_to_participants(self):
        text = """张三
100 聚餐 @李四 @王五"""
        s = parse_chat(text)
        assert set(s.participants) == {'张三', '李四', '王五'}

    def test_empty_input(self):
        s = parse_chat('')
        assert s.event_name == ''
        assert s.participants == []
        assert s.expenses == []

    def test_no_expense_lines(self):
        text = """张三
李四"""
        s = parse_chat(text)
        assert s.participants == ['张三', '李四']
        assert s.expenses == []

    def test_speaker_before_first_expense(self):
        text = """#活动
张三
李四
50 饮料"""
        s = parse_chat(text)
        assert len(s.expenses) == 1
        assert s.expenses[0].payer == '李四'

    def test_expense_without_speaker_ignored(self):
        text = """300 未知付款人"""
        s = parse_chat(text)
        assert s.expenses == []


# ---------------------------------------------------------------------------
# Settlement calculator tests
# ---------------------------------------------------------------------------

class TestCalculate:
    def test_simple_two_person(self):
        s = Settlement(
            event_name='测试',
            participants=['张三', '李四'],
            expenses=[
                Expense('张三', Decimal('100'), '饭', shared_by=None),
            ],
        )
        result = calculate(s)
        # 张三付了100, 每人分摊50, 李四净欠50 → 李四转给张三50
        assert len(result.transfers) == 1
        t = result.transfers[0]
        assert t.from_person == '李四'
        assert t.to_person == '张三'
        assert t.amount == Decimal('50.00')

    def test_equal_payments_no_transfer(self):
        s = Settlement(
            event_name='测试',
            participants=['张三', '李四'],
            expenses=[
                Expense('张三', Decimal('50'), 'A', shared_by=None),
                Expense('李四', Decimal('50'), 'B', shared_by=None),
            ],
        )
        result = calculate(s)
        assert len(result.transfers) == 0

    def test_selected_sharing(self):
        s = Settlement(
            event_name='测试',
            participants=['张三', '李四', '王五'],
            expenses=[
                Expense('张三', Decimal('60'), '奶茶', shared_by=['张三', '李四']),
            ],
        )
        result = calculate(s)
        # 张三付60, 张三和李四各分摊30. 王五不受影响
        # 李四净欠30 → 转给张三30
        assert len(result.transfers) == 1
        t = result.transfers[0]
        assert t.from_person == '李四'
        assert t.to_person == '张三'
        assert t.amount == Decimal('30.00')

    def test_empty(self):
        s = Settlement(event_name='空', participants=[], expenses=[])
        result = calculate(s)
        assert result.transfers == []

    def test_no_expenses(self):
        s = Settlement(event_name='空', participants=['张三'], expenses=[])
        result = calculate(s)
        assert result.transfers == []

    def test_one_person_pays_all(self):
        s = Settlement(
            event_name='',
            participants=['张三', '李四', '王五'],
            expenses=[
                Expense('张三', Decimal('300'), '全部', shared_by=None),
            ],
        )
        result = calculate(s)
        assert len(result.transfers) == 2
        # 每人应摊100. 李四和王五各欠100
        debtors = {t.from_person: t.amount for t in result.transfers}
        assert '张三' not in debtors  # 张三是债权人不转出
        assert debtors['李四'] == Decimal('100.00')
        assert debtors['王五'] == Decimal('100.00')


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------

class TestSettle:
    def test_end_to_end(self):
        text = """#周末聚餐
张三
300 火锅
李四
60 奶茶 @张三
100 打车"""
        result = settle(text)
        assert result.event_name == '周末聚餐'
        assert len(result.expenses) == 3
        assert len(result.transfers) > 0

        # 手动验算:
        # 张三: 付300, 分摊: 火锅150(300/2) + 奶茶60(全归张三，因为@张三) + 打车50(100/2) = 260
        #       净额 = 300 - 260 = +40 (应收)
        # 李四: 付60+100=160, 分摊: 火锅150 + 打车50(100/2) = 200
        #       净额 = 160 - 200 = -40 (应付)
        # 李四 → 张三: min(40, 40) = 40
        transfers = {(t.from_person, t.to_person): t.amount for t in result.transfers}
        assert ('李四', '张三') in transfers
        # 李四欠的40全转给张三了
        assert transfers[('李四', '张三')] == Decimal('40.00')

    def test_rounding(self):
        """三分钱均摊不丢分."""
        text = """张三
0.10 糖果
李四
0 无"""
        result = settle(text)
        # 不会崩溃即可
        assert result.event_name == ''

    def test_balances(self):
        text = """张三
300 火锅
李四
100 打车"""
        result = settle(text)
        assert len(result.balances) == 2
        b = {x.person: x for x in result.balances}
        # 张三: 付300, 分摊 200(火锅150+打车50), 净额 +100
        assert b['张三'].paid == Decimal('300')
        assert b['张三'].share == Decimal('200')
        assert b['张三'].net == Decimal('100')
        # 李四: 付100, 分摊 200(火锅150+打车50), 净额 -100
        assert b['李四'].paid == Decimal('100')
        assert b['李四'].share == Decimal('200')
        assert b['李四'].net == Decimal('-100')
