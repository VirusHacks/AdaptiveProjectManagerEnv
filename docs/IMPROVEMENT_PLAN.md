# 🎯 IMPROVEMENT PLAN - Score Boost Strategy

## Current Score: 81.4/100 → Target: 85-88/100

## PHASE 1: CRITICAL FIX (2 minutes) ⚠️ MUST DO
- [x] Remove .env file from repo (security issue)
- Prevents disqualification risk
- Impact: Prevents negative scoring

## PHASE 2: HIGH-IMPACT, LOW-RISK (30 minutes) 🎯 RECOMMENDED
These give maximum score boost with minimal break risk:

1. **Make hard task harder** (15 min, +2-3 points)
   - Add 2-3 more scheduled events
   - Tighten deadline (25 → 22 days)
   - Add more critical path dependencies
   - Target: Baseline score 0.30-0.40 instead of 0.58

2. **Add early termination** (10 min, +1-2 points)
   - End episode if all employees burned out
   - End if budget exhausted
   - Clearer failure signals

3. **Add production incident mechanic** (20 min, +1-2 points)
   - Random urgent task spawns mid-project
   - Must be handled immediately (drops other work)
   - Realistic crisis management

**Total Phase 2: ~45 min, +4-7 points → Target score: 85.4-88.4**

## PHASE 3: POLISH (15 minutes) ✨ NICE TO HAVE
Low effort, small gains:

4. **Better documentation** (5 min, +0.5 points)
   - Document reward normalization constants
   - Add inline comments for magic numbers

5. **Make thresholds configurable** (10 min, +0.5 points)
   - Move burnout threshold to config
   - Expose productivity multipliers

**Total Phase 3: +1 point → Target score: 86.4-89.4**

## PHASE 4: HIGH-RISK (60+ min) ⚠️ NOT RECOMMENDED
Could break things before submission:

- Task estimation uncertainty (complex changes)
- Collaboration effects (requires testing)
- Major reward function changes (could break balance)

**RECOMMENDATION: Skip Phase 4 - not worth the risk**

---

## RECOMMENDED APPROACH

**Safe path (60 min total):**
1. Critical fix (2 min)
2. Phase 2 improvements (45 min)  
3. Phase 3 polish (15 min)
4. Rebuild Docker & test (15 min)
5. Re-run validation (5 min)

**Expected final score: 85-88/100 (Top 10-15%)**

**Want me to start implementing?**
