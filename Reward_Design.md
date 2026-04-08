# Reward Design for `AdaptiveProjectManagerEnv`

This document defines the reward function used in `AdaptiveProjectManagerEnv`, explains why each term exists, and shows how the design reduces reward hacking.

## At a Glance

- **Design goal:** reward strong project-management behavior, not just task completion.
- **Structure:** dense daily reward + weighted terminal outcome.
- **Core tension modeled:** speed, budget, team health, and delivery quality.
- **Primary safeguard:** penalties for exploitative behavior (switching loops, idle capacity, burnout abuse).
- **Long-horizon focus:** discounting plus terminal score encourages strategic planning.

## Why Reward Design Matters

The reward function is the most important part of this environment.

The environment is only useful if the agent learns behavior that resembles a good project manager.

A poorly designed reward can produce an agent that appears successful according to the score, while behaving in unrealistic or undesirable ways.

For example, an agent might:

- repeatedly switch employees between tasks,
- complete only easy tasks,
- ignore critical blockers,
- overwork the team,
- intentionally sacrifice long-term success to maximize short-term reward.

This failure mode is called **reward hacking**.

So the reward should not only encourage progress; it should encourage the **right** progress.

---

## Reward Design Goals

The reward function is designed to encourage five properties:

1. Deliver the project successfully.
2. Prioritize critical-path work.
3. Respect deadlines and budget.
4. Avoid employee burnout.
5. Make decisions with long-term consequences in mind.

These goals are intentionally aligned with the final grader.

If the step reward encourages one behavior but the final grader rewards something else, the agent may learn the wrong strategy.

This alignment is critical for stable learning and meaningful evaluation.

---

## Overall Reward Structure

The reward has two components:

$$
R_{\text{total}} = R_{\text{dense}} + R_{\text{final}}
$$

with:

$$
R_{\text{dense}} = \sum_{t=0}^{T-1} \gamma^t R_t
$$

$$
R_{\text{final}} = \lambda F
$$

where $T$ is the episode length and $\lambda$ is the scaling factor for terminal outcome.

In short: daily rewards shape behavior; the final score determines whether the overall project outcome is actually good.

The dense reward provides guidance during the project.
The final reward evaluates the overall project outcome.

We target the following signal balance:

- 35% from intermediate step rewards
- 65% from the final project outcome

> Note: this is a design target. The realized ratio can vary slightly across episodes depending on trajectory length and outcome magnitude.

This balance helps the environment avoid two common failures:

| Failure        | Cause                                                                  |
| -------------- | ---------------------------------------------------------------------- |
| Sparse reward  | Agent receives reward only at the end and cannot learn                 |
| Reward hacking | Agent optimizes small local rewards without caring about final success |

---

## Step Reward Formula

At each simulated day $t$, the environment computes:

$$
R_t = R_{\text{progress}} + R_{\text{efficiency}} - P_{\text{delay}} - P_{\text{burnout}} - P_{\text{waste}}
$$

where:

- $R_{\text{progress}}$ rewards meaningful project progress.
- $R_{\text{efficiency}}$ rewards good resource allocation.
- $P_{\text{delay}}$ penalizes schedule failures.
- $P_{\text{burnout}}$ penalizes unhealthy team behavior.
- $P_{\text{waste}}$ penalizes poor or exploitative actions.

### Notation Summary

- $t$: current day index.
- $i$: employee index.
- $T$: episode length in days.
- $\gamma$: discount factor.
- $\lambda$: final-reward scaling constant.

All scalar coefficients are tunable hyperparameters and can be re-calibrated per difficulty level.

---

## Progress Reward

The project should reward the completion of meaningful work.

However, not all tasks are equally important.

Tasks on the critical path receive larger rewards because they determine whether the project can finish on time.

We define:

$$
R_{\text{progress}} = 5C_{\text{critical}} + 2C_{\text{normal}} + U
$$

where:

- $C_{\text{critical}}$ = number of newly completed critical-path tasks.
- $C_{\text{normal}}$ = number of newly completed non-critical tasks.
- $U$ = number of newly unblocked tasks.

Reward events:

| Event                       | Reward |
| --------------------------- | ------ |
| Complete critical-path task | +5     |
| Complete ordinary task      | +2     |
| Unblock another task        | +1     |

Why these weights?

- Critical-path tasks matter more because delaying them delays the entire project.
- Ordinary tasks still matter, but should not dominate the reward.
- Unblocking work is valuable because it creates future options.

---

## Efficiency Reward

The environment should reward assigning the right people to the right work.

We define a skill-match score:

$$
M_i =
\begin{cases}
1.0 & \text{if employee skill matches task exactly} \\
0.5 & \text{if employee can partially contribute} \\
0.0 & \text{if employee is poorly suited}
\end{cases}
$$

The efficiency reward is:

$$
R_{\text{efficiency}} = 0.5 \sum_i M_i
$$

Assignment reward contribution:

| Assignment Type | Reward |
| --------------- | ------ |
| Perfect match   | +0.5   |
| Partial match   | +0.25  |
| Poor match      | 0      |

This encourages the agent to use specialists effectively.

However, the reward is intentionally small.

If this reward were too large, the agent might exploit it by repeatedly reassigning employees to farm assignment points.

---

## Delay Penalty

The environment should strongly discourage missed deadlines and idle time.

We define:

$$
P_{\text{delay}} = 0.25D + 3O
$$

where:

- $D$ = number of days elapsed.
- $O$ = number of overdue critical tasks.

Delay penalty contribution:

| Event                         | Penalty |
| ----------------------------- | ------- |
| One additional day passes     | -0.25   |
| Critical task becomes overdue | -3      |

Why?

- The small per-day penalty encourages the agent to finish efficiently.
- The larger overdue penalty ensures the agent cannot ignore important tasks.

Without this term, an agent could delay forever while still accumulating reward from small actions.

---

## Burnout Penalty

One of the most important tradeoffs in project management is speed versus sustainability.

The environment models burnout explicitly.

Each employee has a burnout value:

$$
b_i \in [0,1]
$$

where:

- 0 = healthy
- 1 = severely burned out

The burnout penalty is:

$$
P_{\text{burnout}} = 4 \sum_i \max(0, b_i - 0.7)
$$

This means:

- Burnout below 0.7 is tolerated.
- Burnout above 0.7 becomes increasingly costly.

Penalty examples:

| Burnout | Penalty |
| ------- | ------- |
| 0.5     | 0       |
| 0.8     | -0.4    |
| 1.0     | -1.2    |

This prevents the agent from using overtime constantly.

Without a burnout penalty, the optimal policy would often be:

```text
Always maximize workload.
```

That is unrealistic and would produce poor long-term behavior.

---

## Waste / Exploit Penalty

The environment must explicitly penalize exploitative behavior.

We define:

$$
P_{\text{waste}} = 1.5S + 2I + 2R
$$

where:

- $S$ = unnecessary task-switching events.
- $I$ = idle employees when useful work exists.
- $R$ = repeated assignment loops.

Waste penalty contribution:

| Behavior                       | Penalty |
| ------------------------------ | ------- |
| Switch employee unnecessarily  | -1.5    |
| Leave employee idle            | -2      |
| Repeat same useless assignment | -2      |

These penalties are specifically designed to prevent reward hacking.

---

## Final Episode Reward

At the end of the project, the environment computes a final score.

The final score is not binary.

Instead, it is based on several dimensions of project success.

We define:

$$
F = 0.35C + 0.25T + 0.15B + 0.15H + 0.10S
$$

where:

- $C$ = project completion score.
- $T$ = deadline adherence score.
- $B$ = budget score.
- $H$ = team health score.
- $S$ = stakeholder satisfaction score.

Each term is normalized to the range $[0,1]$.

This keeps all components comparable and prevents any single metric from dominating purely due to scale.

---

## Component Definitions

### Completion Score

$$
C = \frac{\text{completed task effort}}{\text{total task effort}}
$$

A project that completes all work receives:

$$
C = 1
$$

---

### Deadline Score

$$
T = \max\left(0, 1 - \frac{\text{delay days}}{\text{deadline buffer}}\right)
$$

Example:

| Delay    | Score |
| -------- | ----- |
| 0 days   | 1.0   |
| 2 days   | 0.8   |
| 5 days   | 0.5   |
| 10+ days | 0     |

---

### Budget Score

$$
B = \max\left(0, 1 - \frac{\text{overspend}}{\text{budget limit}}\right)
$$

---

### Team Health Score

$$
H = 1 - \frac{1}{N} \sum_i b_i
$$

where $N$ is the number of employees.

---

### Stakeholder Satisfaction

Stakeholder satisfaction increases if:

- important features are completed,
- milestones are met,
- the final deadline is respected.

It decreases if:

- high-priority features are dropped,
- important tasks are late,
- the project misses the release date.

We normalize it to:

$$
S \in [0,1]
$$

---

## Why These Weights Were Chosen

The final score weights are intentionally asymmetric.

| Metric                   | Weight | Why                                       |
| ------------------------ | ------ | ----------------------------------------- |
| Completion               | 0.35   | The project must actually be delivered    |
| Deadline                 | 0.25   | Timeliness matters, but is not everything |
| Budget                   | 0.15   | Small overspend may be acceptable         |
| Team Health              | 0.15   | Avoid unhealthy management strategies     |
| Stakeholder Satisfaction | 0.10   | Captures business realism                 |

We deliberately avoid giving too much weight to budget or stakeholder satisfaction.

In real projects, a small budget increase is often acceptable if it prevents catastrophic delay.

Similarly, stakeholder satisfaction matters, but should not dominate core delivery outcomes.

---

## Reward Hacking Risks and Defenses

The reward function was specifically designed to defend against common forms of reward hacking.

Each defense combines local shaping (step terms) with global accountability (terminal score).

### Risk 1: Complete Only Easy Tasks

An agent may try to maximize reward by finishing many small tasks.

Defense:

- critical-path tasks have larger reward,
- overdue critical tasks are penalized.

---

### Risk 2: Constant Reassignment

An agent may repeatedly move employees between tasks to farm assignment rewards.

Defense:

- assignment reward is small,
- unnecessary switching is penalized.

---

### Risk 3: Infinite Project Extension

An agent may delay forever while accumulating small positive rewards.

Defense:

- every day incurs a time penalty,
- final score decreases with missed deadlines.

---

### Risk 4: Exploit Burnout

An agent may force employees to work at maximum effort.

Defense:

- burnout penalty grows rapidly,
- final team-health score decreases.

---

### Risk 5: Ignore Important Work

An agent may sacrifice critical work to maximize short-term reward.

Defense:

- critical tasks have larger reward,
- stakeholder satisfaction depends on important features.

---

### Risk 6: Throwing Bodies at the Problem (The Mythical Man-Month)

An agent may try to assign everyone to the same task to finish it instantly, avoiding deadlines.

Defense:

- **Coordination Tax**: Assigning 2+ people to a task causes diminishing returns (productivity per dev drops to 80% or 60%).
- **Counter-play**: If an agent accepts this tax and uses *Pair Programming*, the environment guarantees zero bugs are spawned from Technical Debt, offering a brilliant strategic tradeoff.

---

## Discount Factor

The environment is designed for long-horizon reasoning.

We recommend:

$$
\gamma = 0.97
$$

Why?

- $\gamma < 0.9$ makes the agent too short-sighted.
- $\gamma > 0.99$ makes learning unstable and slow.
- $\gamma = 0.97$ provides a good balance between immediate and future consequences.

With this discount factor, the agent learns that:

- using overtime today may create burnout later,
- delaying a dependency now may cause future delay,
- investing in the right task early may create larger downstream reward.

This improves long-term credit assignment while keeping optimization stable.

---

## Final Reward Equation

Putting everything together:

$$
R_{\text{total}} = \sum_{t=0}^{T-1} \gamma^t R_t + \lambda F
$$

where:

$$
R_t = R_{\text{progress}} + R_{\text{efficiency}} - P_{\text{delay}} - P_{\text{burnout}} - P_{\text{waste}}
$$

and:

$$
F = 0.35C + 0.25T + 0.15B + 0.15H + 0.10S
$$

For this environment, we use $\lambda = 50$.

Implementation note: if you retune step-term coefficients, retune $\lambda$ as well to preserve the intended dense-vs-terminal balance.

This design ensures that the agent is rewarded not only for finishing the project, but for finishing it in the way that a strong human project manager would.
