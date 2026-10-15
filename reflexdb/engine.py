"""Reference anomaly pipeline; deterministic synthetic demo and CSV support."""
from __future__ import annotations
import csv, math, random, statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone

METRICS = {"throughput": -1, "sinr": -1, "harq": 1}

def synthetic(hours=336, width=18, height=12, seed=19):
    rng = random.Random(seed)
    start = datetime(2026, 9, 28, tzinfo=timezone.utc)
    rows = []
    for t in range(hours):
        when = start + timedelta(hours=t)
        for y in range(height):
            for x in range(width):
                urban = x < 9
                rush = 1 + .2 * math.sin(2 * math.pi * (when.hour-8)/24)
                base = (105 if urban else 24) * (1 + .13 * math.sin((x*3+y)/8)) * rush
                chronic = x >= 15 and y >= 8
                emerg = 7 <= x <= 11 and 3 <= y <= 7 and t >= hours-16
                sudden = 2 <= x <= 4 and 8 <= y <= 10 and t >= hours-5
                factor = max(.32, 1-.045*(t-(hours-16))) if emerg else (.45 if sudden else (.52 if chronic else 1))
                tp = max(.2, base*factor*(1+rng.gauss(0,.055)))
                sinr = (17 if urban else 11) + (factor-1)*19 + rng.gauss(0,1.3)
                harq = max(0, .025+(1-factor)*.25+rng.gauss(0,.008))
                rows.append(dict(hour_ts=when.isoformat(), market_id="demo-market",
                    h3_id=f"grid-{x}-{y}", x=x, y=y, technology="NR",
                    throughput=round(tp,3), sinr=round(sinr,3), harq=round(harq,4),
                    sample_count=rng.randint(140,850), distinct_imsis=rng.randint(40,280),
                    prb_util=round(min(.98,.40+(1-factor)*.45+rng.random()*.15),3)))
    return rows

def load_csv(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("throughput","sinr","harq","prb_util"):
            r[k] = float(r[k]) if r.get(k) not in ("",None) else None
        for k in ("sample_count","distinct_imsis","x","y"):
            r[k] = int(r[k]) if r.get(k) not in ("",None) else None
    return rows

def hour_slot(ts):
    dt = datetime.fromisoformat(ts.replace("Z","+00:00"))
    return dt.weekday()*24 + dt.hour

def build_baselines(rows, cutoff, min_samples=30):
    exact, daypart, peer = defaultdict(list), defaultdict(list), defaultdict(list)
    for r in rows:
        if r["hour_ts"] >= cutoff or r["sample_count"] < min_samples:
            continue
        slot = hour_slot(r["hour_ts"])
        part = (slot % 24)//6
        for m in METRICS:
            if r[m] is None:
                continue
            exact[(r["h3_id"],m,slot)].append(r[m])
            daypart[(r["h3_id"],m,part)].append(r[m])
            peer[(r["technology"],m,part)].append(r[m])
    return exact, daypart, peer

def baseline_for(r, m, baselines):
    exact, daypart, peer = baselines
    slot = hour_slot(r["hour_ts"])
    part = (slot % 24)//6
    candidates = [
        (exact.get((r["h3_id"],m,slot),[]),4,"h3_hour_of_week"),
        (daypart.get((r["h3_id"],m,part),[]),16,"h3_daypart"),
        (peer.get((r["technology"],m,part),[]),100,"technology_peer")
    ]
    for vals, minimum, source in candidates:
        if len(vals) >= minimum:
            med = statistics.median(vals)
            mad = statistics.median(abs(v-med) for v in vals)
            scale = max(1.4826*mad, abs(med)*.07,
                .4 if m=="sinr" else (.005 if m=="harq" else 1))
            return med, scale, source, min(1,len(vals)/(minimum*2))
    return None, None, "unavailable", 0

def detect(rows, cutoff, min_samples=30):
    baselines = build_baselines(rows, cutoff, min_samples)
    byhour = defaultdict(list)
    for r in rows:
        if r["hour_ts"] >= cutoff:
            byhour[r["hour_ts"]].append(r)
    state = defaultdict(lambda: {"ewma":0.,"cusum":0.,"run":0})
    snapshots, timeline = [], []
    for ts in sorted(byhour):
        candidates = []
        for r in byhour[ts]:
            if r["sample_count"] < min_samples:
                continue
            scores, evidence, provenance = [], [], {}
            for m, direction in METRICS.items():
                if r[m] is None:
                    continue
                expected, scale, source, reliability = baseline_for(r,m,baselines)
                if expected is None:
                    continue
                residual = max(-8,min(8,direction*(r[m]-expected)/scale))
                st = state[(r["h3_id"],m)]
                st["ewma"] = .35*residual+.65*st["ewma"]
                st["cusum"] = max(0,st["cusum"]+residual-.6)
                bad = residual>1.3 or st["cusum"]>3.5 or st["ewma"]>1.4
                st["run"] = st["run"]+1 if bad else 0
                score = max(residual,st["ewma"],st["cusum"]/2)
                scores.append(score*reliability)
                provenance[m] = dict(observed=r[m],expected=round(expected,3),
                    residual=round(residual,2),baseline=source,reliability=round(reliability,2))
                if score>1.2:
                    evidence.append(m)
            if scores and max(scores)>=1.6 and evidence:
                candidates.append({**r,"anomaly_score":round(max(scores),2),
                    "evidence":evidence,"provenance":provenance})
        snapshots.append((ts,candidates))
        timeline.append({"hour_ts":ts,"candidate_count":len(candidates)})
    return snapshots,timeline

def components(candidates):
    """Demo grid adjacency, NOT actual H3 connectivity."""
    indexed = {(r["x"],r["y"]):r for r in candidates
               if r.get("x") is not None and r.get("y") is not None}
    seen, result = set(), []
    for loc in indexed:
        if loc in seen:
            continue
        todo, group = [loc], []
        seen.add(loc)
        while todo:
            x,y = todo.pop()
            group.append(indexed[(x,y)])
            for n in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if n in indexed and n not in seen:
                    seen.add(n)
                    todo.append(n)
        result.append(group)
    return result

def build_episodes(snapshots, min_cells=3):
    episodes, history, nextid = {}, [], 1
    prev_ts = None
    for ts, candidates in snapshots:
        clusters = [c for c in components(candidates) if len(c)>=min_cells]
        claimed = set()
        for cluster in sorted(clusters,key=len,reverse=True):
            cells = {r["h3_id"] for r in cluster}
            best, overlap = None, 0
            for eid, ep in episodes.items():
                if eid in claimed or ep["last_seen"]!=prev_ts:
                    continue
                old = set(ep["cells"])
                j = len(cells & old)/len(cells | old)
                if j>overlap:
                    overlap,best = j,eid
            if overlap<.20:
                best = None
            if best is None:
                best = f"EP-{nextid:04d}"
                nextid += 1
                episodes[best] = dict(episode_id=best,first_seen=ts,
                    max_cells=0,previous_count=0,age_hours=0)
            ep = episodes[best]
            oldcount = ep["previous_count"]
            ep.update(last_seen=ts,cells=sorted(cells),
                affected_h3_count=len(cells),age_hours=ep["age_hours"]+1,
                previous_count=len(cells),max_cells=max(ep["max_cells"],len(cells)))
            ep["growth_pct"] = round(100*(len(cells)-oldcount)/max(oldcount,1),1) if oldcount else 0
            ep["mean_anomaly"] = round(statistics.mean(r["anomaly_score"] for r in cluster),2)
            ep["exposure_proxy"] = sum(r["distinct_imsis"] for r in cluster)
            ep["evidence"] = sorted(set(v for r in cluster for v in r["evidence"]))
            ep["lifecycle_state"] = "EMERGING" if ep["age_hours"]<=8 or ep["growth_pct"]>25 else "ESTABLISHED"
            ep["emerging_score"] = round(min(100,20*ep["mean_anomaly"]+
                min(20,2*len(cells))+min(15,ep["age_hours"]*2)+
                min(15,max(0,ep["growth_pct"])/5)))
            history.append(dict(episode_id=best,hour_ts=ts,
                affected_h3_count=len(cells),score=ep["emerging_score"]))
            claimed.add(best)
        prev_ts = ts
    latest = snapshots[-1][0] if snapshots else None
    result = [{k:v for k,v in ep.items() if k not in ("previous_count","max_cells")}
              for ep in episodes.values() if ep["last_seen"]==latest]
    return sorted(result,key=lambda e:e["emerging_score"],reverse=True),history

def run(rows,holdout_hours=24):
    times = sorted({r["hour_ts"] for r in rows})
    if len(times)<holdout_hours+48:
        raise ValueError("Need at least 48 baseline hours plus holdout hours")
    cutoff = times[-holdout_hours]
    snapshots,timeline = detect(rows,cutoff)
    episodes,history = build_episodes(snapshots)
    latest = times[-1]
    latest_rows = [r for r in rows if r["hour_ts"]==latest]
    return dict(metadata=dict(latest_hour=latest,baseline_cutoff=cutoff,
        baseline_hours=len(times)-holdout_hours,holdout_hours=holdout_hours,
        source="synthetic" if str(rows[0]["h3_id"]).startswith("grid-") else "csv",
        disclaimer="Exposure sums per-H3 distinct IMSIs; not deduplicated users."),
        episodes=episodes,history=history,timeline=timeline,
        cells=[dict(h3_id=r["h3_id"],x=r.get("x"),y=r.get("y"),
            throughput=r["throughput"],sinr=r["sinr"],harq=r["harq"])
            for r in latest_rows])
