# Local Demo Checklist

## Before Presentation

- [ ] MongoDB is running.
- [ ] Redis is running.
- [ ] Backend is running on `http://localhost:8000`.
- [ ] `curl http://localhost:8000/health/live` returns healthy status.
- [ ] `curl http://localhost:8000/health/ready` returns ready status.
- [ ] `python3 scripts/demo_seed.py` completed successfully.
- [ ] Demo user can log in.
- [ ] Demo Linux agent exists.
- [ ] Demo agent key is saved for lab scenarios.
- [ ] Seeded events exist.
- [ ] Seeded alerts exist.
- [ ] Seeded incidents exist.
- [ ] At least one attack chain exists.
- [ ] Attack chain story exists.
- [ ] Dashboard summary shows non-zero counts.
- [ ] `python3 scripts/demo_smoke_check.py` prints all PASS.
- [ ] Optional: `bash lab/attack_scenarios/scenario_06_full_attack_chain.sh` works.
- [ ] Optional: validation scripts pass for `scenario_06_full_attack_chain`.

## Presenter Notes

- Keep the demo local and safe.
- Mention that `sentinelxdr-demo` tags make demo data identifiable.
- Show event to detection to alert to incident to attack-chain flow.
- End with Lovable frontend readiness: API examples, route plan, context JSON, and prompt are already prepared.
