# ReflexDB MVP architecture

## Objective
Surface newly emerging network degradation episodes rather than simply ranking chronically poor H3 cells.

## Data flow
Observations → contextual as-of baselines → directional standardized residuals → EWMA/CUSUM → candidate H3 cells → geographic connected components → episode matching → operational dashboard.

## Baselines
Use H3 + hour-of-week when sufficient history exists; fall back to H3 + daypart and then technology peers. Baseline medians and robust MAD scales are computed strictly before the evaluation cutoff. Current demo freezes baselines over the holdout period.

## Operational interfaces
GET /api/health, /api/overview, /api/episodes?state=EMERGING, /api/episodes/{id}.

## Production migration
1. Add read-only StarRocks source with typed KPI semantics and minimum sample/denominator rules.
2. Replace rectangular demo adjacency with actual H3 neighbor graph and separate radio/topology graph.
3. Materialize incremental baselines, detector state, and durable episode history.
4. Add idempotent hourly scheduling, checkpoints, late-data backfills and outbox notifications.
5. Evaluate against historical incidents using false episodes per market-day, lead time, precision/recall, and impact-weighted recall.
6. Secure API, add market/tenant isolation, audit trails, and optional NIDL escalation.

## Known caveats
Scores are heuristics, not calibrated probabilities. Summed per-cell IMSIs are not deduplicated affected subscribers. Demo coordinates are not H3. This is not a root-cause engine or a network control plane.
