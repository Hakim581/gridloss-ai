import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from gridtrust_engine import SCENARIOS, generate, inspect, electric_state, graph, train_anomaly, score_anomaly, export_run


def test_all_scenarios_run():
    for code in SCENARIOS:
        run=generate(code,42)
        assert len(run['telemetry'])>=8
        assert inspect(run,7)['status']


def test_reproducible_generation():
    assert generate('S04',42)['sha256']==generate('S04',42)['sha256']
    assert generate('S04',42)['sha256'] != generate('S04',43)['sha256']


def test_communication_loss_never_confirms_last_status():
    run=generate('S03',42)
    state=inspect(run,5)
    assert state['last_known']=='BAĞLI'
    assert state['current_confirmed']=='MƏLUM DEYİL'
    assert state['status']=='RABİTƏ YOXDUR'
    assert run['truth'].iloc[5]['hidden_switch']=='AÇIQ'


def test_backfilled_measurement_not_confirmed():
    run=generate('S07',42)
    assert inspect(run,5)['current_confirmed']=='MƏLUM DEYİL'
    assert inspect(run,6)['current_confirmed']=='BAĞLI'


def test_bias_detected():
    assert inspect(generate('S04',42),7)['measurement_suspect']
    assert not inspect(generate('S01',42),7)['measurement_suspect']


def test_network_and_ai():
    assert len(graph().nodes)==9
    assert electric_state()['i1']>0
    model=train_anomaly(42)
    assert isinstance(score_anomaly(model,inspect(generate('S01',42),7)),float)


def test_export_excludes_hidden_truth():
    data=export_run(generate('S03',42)).decode()
    assert 'hidden_switch' not in data
    assert 'RTU-01' in data