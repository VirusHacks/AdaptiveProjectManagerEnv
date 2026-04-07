# Architecture for `AdaptiveProjectManagerEnv`

A compact view of how the environment runs and how components interact.

## System View (Simple)

```text
+------------------+     +------------------+     +----------------------+
| Agent / Policy   | --> | OpenEnv API      | --> | Env Orchestrator     |
| chooses action   |     | reset / step     |     | controls step order  |
+--------+---------+     +---------+--------+     +----------+-----------+
         ^                         |                         |
         |                         v                         v
+--------+---------+     +-------------------------+   +------------------+
| Observation Out  | <-- | ProjectState            |-->| Task Engine      |
| obs, reward,done |     | single source of truth  |   +------------------+
+------------------+     | day, budget, tasks,     |   +------------------+
                         | employees, risks, metas  |-->| Employee Engine  |
                         +-----------+-------------+   +------------------+
                                     |                 +------------------+
                                     +---------------> | Risk/Event Engine|
                                                       +---------+--------+
                                                                 |
                                                +----------------v----------------+
                                                | Reward Engine + Final Grader    |
                                                +---------------------------------+
```

## Runtime Flow (Per Step)

```text
reset -> initial observation
      -> action
      -> validate
      -> task update
      -> employee update
      -> risk/event update
      -> recompute metrics
      -> reward
      -> done?
         |- no  -> next observation -> loop
         |- yes -> final grading
```

## Core Components (Quick)

- **Orchestrator**: runs engines in deterministic order.
- **ProjectState**: single source of truth for all mutable state.
- **Task Engine**: dependencies, effort reduction, status transitions.
- **Employee Engine**: workload, burnout, availability effects.
- **Risk/Event Engine**: seeded disruptions and state impacts.
- **Reward Engine**: dense step reward $R_t$.
- **Final Grader**: terminal score in $[0,1]$.

## Long-Running Task Model

$$
E_{t+1} = \max(0, E_t - P_t)
$$

$$
P_t = \left(\sum_{i=1}^{n} s_i\right)c(n), \quad c(n)=\frac{1}{1+0.15(n-1)}
$$

- $s_i$: skill-match contribution
- $c(n)$: coordination penalty (diminishing returns)

## Determinism Guarantees

- fixed scenario seeds,
- deterministic engine order,
- deterministic grading rules,
- explicit transition equations.

This makes evaluation fair, repeatable, and easy to debug.
