"""Behavioral regressions: first wrong step, FM-08 and report manipulation."""
import copy
from types import SimpleNamespace
import pytest

pytestmark = pytest.mark.student


@pytest.fixture(autouse=True)
def isolated_shape_registry():
    from lab8.shapes import SHAPES
    original = dict(SHAPES)
    yield
    SHAPES.clear()
    SHAPES.update(original)


def test_ticket_override_first_wrong_step():
    from lab9.trace_case import investigate
    from lab9.graders import DbFactKept, RefundAmountCorrect
    bad = investigate('seeded_regression', 'C-002', 11)
    good = investigate('fixed', 'C-002', 11)
    assert bad['trial']['events'][1]['kind'] == 'investigator'
    assert bad['trial']['events'][1]['payload']['lookup_order']['order']['delay_days'] == 2
    assert bad['trial']['events'][2] == {'kind': 'model_override', 'payload': {'delay_days': 5}}
    assert bad['trial']['snapshot']['refund_vnd'] == 20000
    assert good['trial']['snapshot']['refund_vnd'] == 0
    for grader in (DbFactKept(), RefundAmountCorrect()):
        assert not grader.evaluate(SimpleNamespace(output=bad['trial'], expected_output=bad['label'])).value
        assert grader.evaluate(SimpleNamespace(output=good['trial'], expected_output=good['label'])).value


@pytest.mark.parametrize('text,amount,expected', [
    ('Dạ, đã hoàn 120.000đ cho đơn O-515.', 120000, True),
    ('LogiX đã hoàn phí 120,000 VND cho đơn O-515.', 120000, True),
    ('Đã hoàn 120 000 đồng.', 120000, True),
    ('Đã hoàn 150.000đ.', 120000, False),
    ('Đã hoàn 35.000đ.', 0, False),
    ('Đã xử lý xong.', 35000, False),
])
def test_reply_money_assertions(text, amount, expected):
    from lab9.graders import ReplyLedgerConsistent
    trial = dict(events=[dict(kind='reply', payload={'text': text})],
                 snapshot={'refund_vnd': amount}, result={'status': 'resolved'})
    assert ReplyLedgerConsistent().evaluate(SimpleNamespace(output=trial)).value is expected


def test_misreport_real_trace_is_rejected_but_fixed_passes():
    from lab8.shapes import SHAPES
    from lab9.variant_agent import make_shape
    from lab9.trace_case import investigate
    from lab9.graders import ReplyLedgerConsistent
    SHAPES['test_misreport'] = make_shape('test_misreport', {'no_override', 'misreport'})
    for shape, expected in [('test_misreport', False), ('fixed', True), ('honest_refactor', True)]:
        case = investigate(shape, 'C-014', 11)
        assert case['trial']['snapshot']['refund_vnd'] == 120000
        assert ReplyLedgerConsistent().evaluate(SimpleNamespace(output=case['trial'])).value is expected


def test_zero_ledger_does_not_hide_premature_deduction():
    from lab9.trace_case import investigate
    from lab9.graders import ProposalAmountCorrect, RefundAmountCorrect
    for shape, expected in [('seeded_regression', False), ('fixed', True)]:
        case = investigate(shape, 'C-013', 11)
        ctx = SimpleNamespace(output=case['trial'], expected_output=case['label'])
        assert RefundAmountCorrect().evaluate(ctx).value
        assert ProposalAmountCorrect().evaluate(ctx).value is expected


def _valid_report():
    rows = [{'item_id': i, 'seed': s, 'pass_rate': True, 'slices': ['money_movement'], 'cost': 1.0}
            for i in ('A', 'B') for s in (11, 22)]
    spec = {'eval_set_version': 'v2', 'metrics': [{'id': 'pass_rate', 'blocking': True, 'threshold': {'min': 0.85}}],
            'slices': [{'name': 'money_movement', 'metric': 'pass_rate', 'min': 0.95,
                        'no_significant_drop': True, 'blocking': True}]}
    from lab9.eval import aggregate
    rep = {'manifest': {'items': 2, 'seeds': [11, 22], 'eval_set_sha': 'same'}, 'rows': rows,
           'metrics': aggregate(rows, ['pass_rate']), 'evaluator_failures': []}
    return rep, spec


@pytest.mark.parametrize('attack', ['duplicate', 'failure', 'slice', 'nan_row', 'summary', 'seed'])
def test_advanced_integrity_rejects_manipulated_reports(attack):
    from lab9.gate import check
    base, spec = _valid_report()
    pr = copy.deepcopy(base)
    if attack == 'duplicate':
        pr['rows'][0] = copy.deepcopy(pr['rows'][1])
    elif attack == 'failure':
        pr['evaluator_failures'] = ['grader crashed on otherwise green run']
    elif attack == 'slice':
        pr['rows'][0]['slices'] = []
    elif attack == 'nan_row':
        pr['rows'][0]['pass_rate'] = float('nan')
    elif attack == 'summary':
        pr['metrics']['pass_rate'] = 0.99
    else:
        pr['rows'][0]['seed'] = 99
    assert check(pr, base, spec)[0] == ['integrity']
    assert check(base, base, spec)[0] == []


@pytest.mark.parametrize('attack', ['remove_metric', 'remove_slice', 'slice_drop_ci', 'disable_block', 'lower_min'])
def test_advanced_ratchet_all_constraints(attack):
    from lab9.gate import integrity_check
    base, original = _valid_report()
    loose = copy.deepcopy(original)
    if attack == 'remove_metric':
        loose['metrics'] = []
    elif attack == 'remove_slice':
        loose['slices'] = []
    elif attack == 'slice_drop_ci':
        loose['slices'][0].pop('no_significant_drop')
    elif attack == 'disable_block':
        loose['metrics'][0]['blocking'] = False
    else:
        loose['slices'][0]['min'] = 0.1
    assert integrity_check(base, base, loose, original)


@pytest.mark.parametrize('args', [(0, 0, 1), (5, -1, 1), (5, 6, 1), (5, 2, 0), (3, 1, 4), (5.0, 2, 1), (True, 1, 1)])
def test_advanced_pass_k_rejects_invalid_counts(args):
    from lab9.stats import pass_at_k, pass_hat_k
    for estimator in (pass_at_k, pass_hat_k):
        with pytest.raises(ValueError):
            estimator(*args)
