from reflexdb.engine import synthetic, run, build_baselines, baseline_for

def test_pipeline():
    d = run(synthetic(hours=168, width=12, height=10), holdout_hours=24)
    assert len(d["timeline"]) == 24
    assert d["episodes"]
    assert all(e["emerging_score"] <= 100 for e in d["episodes"])

def test_asof_no_future_leakage():
    rows = synthetic(hours=168, width=2, height=2)
    cutoff = rows[-96]["hour_ts"]
    before = baseline_for(rows[-1], "throughput", build_baselines(rows, cutoff))
    for r in rows:
        if r["hour_ts"] >= cutoff:
            r["throughput"] = 0.001
    after = baseline_for(rows[-1], "throughput", build_baselines(rows, cutoff))
    assert before == after

def test_determinism():
    rows = synthetic(hours=100, width=8, height=7)
    assert run(rows) == run(rows)
