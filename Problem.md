# Adaptive Project Manager

## Problem Statement

Software projects often fail for repeatable reasons:

- critical work is discovered late,
- teams become overloaded,
- priorities change,
- deadlines slip,
- short-term fixes create long-term issues.

Most project tools track tasks and timelines, but they do not help with decision-making under uncertainty.

This project introduces `AdaptiveProjectManagerEnv`, an OpenEnv-compatible reinforcement learning environment where the agent acts as a project manager.

The environment models:

- tasks with dependencies,
- employees with different skills,
- budget and deadline limits,
- workload and burnout,
- random project disruptions.

The goal is to learn better day-to-day project decisions over time.

In this environment, the agent plays the role of project manager and must choose actions repeatedly as the project evolves.

This is the core challenge: decisions that look useful today can hurt delivery later.

## Why This Problem Matters

Project management requires constant tradeoffs.

| Goal | Competing Goal |
| --- | --- |
| Deliver quickly | Avoid burnout |
| Stay in budget | Add enough capacity |
| Finish full scope | Protect the critical path |
| Solve current issues | Reduce future risk |

These decisions are hard because:

- future events are uncertain,
- effects are delayed,
- resources are limited,
- improving one metric can hurt another.

Traditional project-management systems are mostly descriptive: they show status, but they do not decide what should happen next.

This problem asks whether an agent can learn stronger decision policies through repeated interaction with a realistic simulation.

## Why Reinforcement Learning

This is a sequential decision problem, not just a prediction problem.

The core question is not:

> “Will the project be late?”

It is:

> “Given the current state, what action should we take now?”

RL is a good fit because the environment includes:

- repeated decisions,
- delayed rewards,
- changing conditions,
- multiple conflicting objectives.

The agent is not asked to predict outcomes once. It must repeatedly choose the next best action under uncertainty.

### Why Fixed Rules Are Not Enough

A simple rule like “always assign the strongest engineer to the highest-priority task” can fail because:

- one reassignment may block another dependency,
- overtime may help now but increase burnout later,
- dropping minor scope may protect delivery,
- short-term budget increases (e.g., contractor) may prevent larger delays.

No single rule is optimal in every state.

The best action depends on:

- what has already happened,
- what is likely to happen next,
- how current choices change future options.

## Research Question

Can an RL agent manage a software project under uncertainty better than fixed rule-based policies?

More specifically: can it learn when to assign, delay, reprioritize, de-scope, or escalate work to improve final delivery outcomes?

Baseline comparison is against fixed heuristic policies.

## Environment Objective

Deliver the project while balancing:

- schedule performance,
- budget control,
- burnout risk,
- stakeholder satisfaction,
- completed scope.

These goals conflict, so there is no perfect action at each step.

| Action | Benefit | Cost |
| --- | --- | --- |
| Request overtime | Faster progress | Higher burnout risk |
| Hire contractor | More capacity | Higher spend |
| Drop low-priority scope | Better schedule protection | Lower stakeholder satisfaction |
| Focus on easy tasks | Quick visible progress | Critical blockers remain |

Target behavior is to maximize project success while minimizing delay, overspend, and burnout.

## What the Agent Decides

### 1) Resource Allocation

- Who works on which task
- When to reassign staff
- When to preserve specialist capacity

### 2) Prioritization

- Which tasks to do now
- Whether to clear blockers first
- How to manage critical-path work

### 3) Contingency Actions

- Overtime
- Temporary hiring
- Scope deferral
- Delay acceptance

These contingency choices can produce delayed effects across later steps.

## OpenEnv Fit

This environment is suitable for OpenEnv because it provides:

- a realistic human decision task,
- clear observation/action/reward structure,
- deterministic evaluation through seeded randomness,
- support for multiple difficulty settings,
- efficient simulation with meaningful complexity.

Per simulated day, the loop is:

1. Observe project state
2. Choose actions
3. Simulate one day of progress
4. Apply possible disruptions
5. Return new state and reward

This directly matches the standard RL interaction cycle:

`Observation -> Action -> Environment Update -> Reward`

## Difficulty and Delayed Effects

Short-term gains can create long-term losses.

Example:

- Day 3: use overtime to recover schedule.
- Day 10: burnout reduces team speed; critical work slips.

The agent must therefore plan ahead, not optimize only for immediate reward.

This introduces long-horizon planning, risk management, and tradeoff control.

## Stochastic Events and Reproducibility

The environment includes realistic random events, such as:

- employee absence,
- urgent feature requests,
- effort increases,
- vendor delays,
- bug discovery,
- requirement changes.

Randomness is seed-controlled to ensure:

- reproducible runs,
- fair policy comparison,
- stable evaluation.

This keeps the environment realistic while still allowing fair and repeatable comparison between policies.

## Why This Problem Is Useful

`AdaptiveProjectManagerEnv` can serve as:

- a benchmark for long-horizon decision-making,
- a controlled setting for comparing project-management strategies,
- an early foundation for AI-assisted planning tools.

## Summary

`AdaptiveProjectManagerEnv` frames project management as sequential decision-making under uncertainty.

It combines limited resources, conflicting goals, delayed consequences, and controlled randomness in a reproducible RL environment.

Core question:

> Can an agent learn to manage a complex project under uncertainty better than fixed rules?
