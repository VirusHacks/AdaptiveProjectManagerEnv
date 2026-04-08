"""
Mission Control Dashboard for Adaptive Project Manager.

A high-fidelity, NASA-inspired interface built with Gradio Blocks and custom CSS.
Overlays CRT scanlines, uses IBM Plex Mono typography, and features dynamic status meters.
"""

import gradio as gr
from typing import Dict, Any, List, Optional
import pandas as pd
import plotly.graph_objects as go

# ============================================================================
# CSS DESIGN SYSTEM
# ============================================================================

CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Crimson+Pro:wght@700&display=swap');

:root {
    --amber: #FFB84D;
    --cyan: #00D9FF;
    --green: #00FF88;
    --red: #FF4757;
    --bg-dark: #0A0E1A;
    --bg-panel: #151B2D;
    --bg-card: #1E2738;
    --text-primary: #E8EAF0;
    --text-secondary: #8B93B0;
    --border: #2A3447;
}

.gradio-container {
    background-color: var(--bg-dark) !important;
    font-family: 'IBM Plex Mono', monospace !important;
    color: var(--text-primary) !important;
}

/* Scanline Effect */
.gradio-container::after {
    content: " ";
    display: block;
    position: fixed;
    top: 0; left: 0; bottom: 0; right: 0;
    background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), 
                linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
    z-index: 9999;
    background-size: 100% 2px, 3px 100%;
    pointer-events: none;
    opacity: 0.3;
}

.mc-header {
    background: var(--bg-panel);
    border-bottom: 2px solid var(--amber);
    padding: 15px 30px;
    margin-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
}

.mc-title {
    font-family: 'Crimson Pro', serif !important;
    font-size: 24px !important;
    font-weight: 700 !important;
    color: var(--amber) !important;
    text-transform: uppercase;
    letter-spacing: 2px;
}

.status-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 10px var(--green);
    animation: pulse 2s infinite;
    margin-right: 10px;
}

@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.4; transform: scale(0.8); }
}

.panel-title {
    font-family: 'Crimson Pro', serif !important;
    font-size: 14px !important;
    font-weight: 700 !important;
    color: var(--cyan);
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 15px;
    border-left: 3px solid var(--cyan);
    padding-left: 10px;
}

.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    padding: 15px;
    border-radius: 4px;
    text-align: center;
}

.metric-label {
    font-size: 10px;
    color: var(--text-secondary);
    text-transform: uppercase;
    margin-bottom: 5px;
}

.metric-value {
    font-size: 24px;
    font-weight: 600;
    color: var(--amber);
}

.progress-bar-bg {
    width: 100%;
    height: 8px;
    background: #000;
    border-radius: 4px;
    overflow: hidden;
    margin-top: 5px;
}

.progress-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--green), var(--cyan));
    transition: width 0.5s ease-in-out;
}

.event-log {
    font-size: 11px;
    line-height: 1.4;
    color: var(--text-primary);
    max-height: 300px;
    overflow-y: auto;
    padding: 10px;
    background: rgba(0,0,0,0.3);
    border: 1px solid var(--border);
    border-radius: 4px;
}

.log-entry {
    margin-bottom: 8px;
    border-left: 2px solid var(--cyan);
    padding-left: 8px;
}

.log-day {
    color: var(--cyan);
    font-weight: 600;
    margin-right: 5px;
}

button.primary-btn {
    background: linear-gradient(135deg, var(--amber) 0%, #FF8C42 100%) !important;
    color: var(--bg-dark) !important;
    font-weight: 700 !important;
    border: none !important;
}

button.secondary-btn {
    background: transparent !important;
    color: var(--cyan) !important;
    border: 1px solid var(--cyan) !important;
}

.gradio-dropdown label, .gradio-textbox label, .gradio-checkboxgroup label {
    color: var(--cyan) !important;
    font-size: 10px !important;
    text-transform: uppercase !important;
}

.gradio-dropdown, .gradio-textbox, .gradio-checkboxgroup {
    background: var(--bg-card) !important;
}
"""

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def format_burnout_html(name, value):
    percent = int(value * 100)
    color = "var(--green)"
    if percent > 70: color = "var(--red)"
    elif percent > 40: color = "var(--amber)"
    
    return f"""
    <div style="margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px;">
            <span>{name}</span>
            <span style="color: {color};">{percent}% BURNOUT</span>
        </div>
        <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width: {percent}%; background: {color};"></div>
        </div>
    </div>
    """

def create_reward_chart(history):
    if not history:
        # Return empty chart
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=0, b=0),
            height=200
        )
        return fig
    
    days = [h['day'] for h in history]
    rewards = [h['cumulative_reward'] for h in history]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=days, y=rewards,
        mode='lines+markers',
        line=dict(color='#00D9FF', width=2),
        marker=dict(color='#FFB84D', size=6),
        fill='tozeroy',
        fillcolor='rgba(0, 217, 255, 0.1)'
    ))
    
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(showgrid=False, title=dict(text='DAY', font=dict(size=10))),
        yaxis=dict(showgrid=True, gridcolor='#2A3447', title=dict(text='CUMULATIVE REWARD', font=dict(size=10))),
        height=240
    )
    return fig

# ============================================================================
# UI BUILDER
# ============================================================================

def create_custom_gradio_ui(web_manager=None) -> gr.Blocks:
    """Build the Mission Control Dashboard."""
    
    with gr.Blocks(title="◉ Mission Control") as demo:
        gr.HTML(f"<style>{CUSTOM_CSS}</style>")
        # State persistence
        obs_state = gr.State(None)
        history_state = gr.State([])
        
        # 1. HEADER
        with gr.HTML():
            gr.HTML("""
            <div class="mc-header">
                <div>
                    <span class="mc-title">◉ MISSION CONTROL</span>
                </div>
                <div style="display: flex; gap: 30px; font-size: 11px;">
                    <div style="display: flex; align-items: center;">
                        <span class="status-dot"></span>
                        <span style="letter-spacing: 1px;">SYSTEM: ACTIVE</span>
                    </div>
                </div>
            </div>
            """)
        
        with gr.Row():
            # 2. LEFT PANEL: SITUATION
            with gr.Column(scale=1):
                gr.HTML('<div class="panel-title">📡 SITUATION</div>')
                
                with gr.Row():
                    comp_box = gr.HTML('<div class="metric-card"><div class="metric-label">COMPLETION</div><div class="metric-value">0%</div></div>')
                    days_box = gr.HTML('<div class="metric-card"><div class="metric-label">DAYS LEFT</div><div class="metric-value" style="color: var(--red);">0</div></div>')
                
                with gr.Row():
                    block_box = gr.HTML('<div class="metric-card"><div class="metric-label">BLOCKED</div><div class="metric-value" style="color: var(--amber);">0</div></div>')
                    budget_box = gr.HTML('<div class="metric-card"><div class="metric-label">BUDGET</div><div class="metric-value" style="color: var(--green);">$0</div></div>')
                
                gr.HTML('<div class="panel-title" style="margin-top: 30px;">👥 TEAM STATUS</div>')
                team_meters = gr.HTML('<div class="event-log">Awaiting personnel deployment...</div>')

            # 3. CENTER PANEL: DECISIONS
            with gr.Column(scale=1):
                gr.HTML('<div class="panel-title">🎮 COMMANDS</div>')
                
                task_selector = gr.Dropdown(
                    choices=["easy", "medium", "hard"],
                    value="easy",
                    label="PROXIMITY SCAN (TASK SELECTION)",
                    interactive=True
                )
                
                reset_btn = gr.Button("↻ RESET & INITIALIZE PROTOCOL", variant="secondary", elem_classes=["secondary-btn"])
                
                gr.Markdown("---")
                
                # Structured Assignment Controls
                gr.HTML('<div class="metric-label">PERSONNEL ASSIGNMENTS</div>')
                auto_assign_btn = gr.Button("⚡ AUTO ASSIGN TASKS", variant="secondary")
                assignment_df = gr.Dataframe(
                    headers=["Employee", "Skill", "Task Assignment"],
                    datatype=["str", "str", "str"],
                    row_count=5,
                    column_count=3,
                    interactive=True,
                    label=None
                )
                
                with gr.Row():
                    contingency_select = gr.Dropdown(
                        choices=[
                            "none", 
                            "request_overtime", 
                            "hire_contractor", 
                            "defer_low_priority_work",
                            "request_emergency_funding"
                        ],
                        value="none",
                        label="CONTINGENCY PROTOCOL"
                    )
                    reprio_select = gr.Dropdown(
                        choices=[],
                        multiselect=True,
                        label="PRIORITY ESCALATION"
                    )
                
                step_btn = gr.Button("▶ EXECUTE DAY CYCLE", variant="primary", elem_classes=["primary-btn"])

            # 4. RIGHT PANEL: telemetry
            with gr.Column(scale=1):
                gr.HTML('<div class="panel-title">📈 TELEMETRY</div>')
                reward_plot = gr.Plot(label="Cumulative Reward")
                
                with gr.Row():
                    step_rew_box = gr.HTML('<div class="metric-card"><div class="metric-label">STEP REWARD</div><div class="metric-value" style="font-size: 18px;">0.00</div></div>')
                    tot_rew_box = gr.HTML('<div class="metric-card"><div class="metric-label">TOTAL ACCUMULATED</div><div class="metric-value" style="color: var(--cyan); font-size: 18px;">0.00</div></div>')
                
                gr.HTML('<div class="panel-title" style="margin-top: 30px;">📜 LOGGING</div>')
                event_log_html = gr.HTML('<div class="event-log" style="height: 250px;">Waiting for telemetry...</div>')

        # ========================================================================
        # LOGIC & WIRING
        # ========================================================================
        
        def update_ui_components(obs_dict, history):
            if not obs_dict:
                return [gr.update()]*11
            
            # Format Metrics
            comp_html = f'<div class="metric-card"><div class="metric-label">COMPLETION</div><div class="metric-value">{int(obs_dict.get("project_completion", 0)*100)}%</div></div>'
            days_html = f'<div class="metric-card"><div class="metric-label">DAYS LEFT</div><div class="metric-value" style="color: var(--red);">{obs_dict.get("days_remaining", 0)}</div></div>'
            block_html = f'<div class="metric-card"><div class="metric-label">BLOCKED</div><div class="metric-value" style="color: var(--amber);">{obs_dict.get("blocked_tasks", 0)}</div></div>'
            budget_html = f'<div class="metric-card"><div class="metric-label">BUDGET</div><div class="metric-value" style="color: var(--green);">${int(obs_dict.get("budget_remaining", 0))}</div></div>'
            
            # Format Team
            team_html = '<div style="padding: 10px;">'
            employees = obs_dict.get("employees", [])
            for e in employees:
                team_html += format_burnout_html(e.get("id"), e.get("burnout", 0))
            team_html += "</div>"
            
            # Format Assignment Dataframe
            tasks = obs_dict.get("tasks", [])
            
            df_data = []
            for e in employees:
                df_data.append([e.get("id"), " • ".join(e.get("skills", [])), e.get("assigned_task_id") or "None"])
            
            # Format Log
            log_entries = ""
            for h in reversed(history):
                log_entries += f'<div class="log-entry"><span class="log-day">D{h["day"]}</span> {h["message"]}</div>'
            log_html = f'<div class="event-log" style="height: 250px;">{log_entries}</div>'
            
            # Rewards
            step_rew_html = f'<div class="metric-card"><div class="metric-label">STEP REWARD</div><div class="metric-value" style="font-size: 18px;">{obs_dict.get("reward", 0):.2f}</div></div>'
            total_rew = history[-1]['cumulative_reward'] if history else 0
            tot_rew_html = f'<div class="metric-card"><div class="metric-label">TOTAL ACCUMULATED</div><div class="metric-value" style="color: var(--cyan); font-size: 18px;">{total_rew:.2f}</div></div>'
            
            # Task & Reprio options
            todo_tasks = [t.get("id") for t in tasks if t.get("status") != "done"]
            
            return [
                comp_html, days_html, block_html, budget_html,
                team_html,
                pd.DataFrame(df_data, columns=["Employee", "Skill", "Task Assignment"]),
                gr.update(choices=todo_tasks),
                create_reward_chart(history),
                step_rew_html, tot_rew_html,
                log_html
            ]

        def _normalize_observation(serialized: Dict[str, Any]) -> Dict[str, Any]:
            """Convert web_manager serialized payload into one observation dict for UI."""
            obs = dict(serialized.get("observation", {}) if isinstance(serialized, dict) else {})
            obs["reward"] = serialized.get("reward", obs.get("reward", 0.0)) if isinstance(serialized, dict) else obs.get("reward", 0.0)
            obs["done"] = serialized.get("done", obs.get("done", False)) if isinstance(serialized, dict) else obs.get("done", False)
            return obs

        async def reset_env(task_name, history):
            if web_manager is None:
                obs = _default_obs(task_name)
                obs["message"] = f"Reset unavailable (no web manager). Loaded local default for {task_name}."
                new_history = list(history or [])
                new_history.append({"day": 1, "message": obs["message"], "cumulative_reward": 0.0})
                return obs, new_history

            serialized = await web_manager.reset_environment({"task_id": task_name})
            obs = _normalize_observation(serialized)
            new_history = [{
                "day": obs.get("day", 1),
                "message": obs.get("message") or f"Mission reset for task '{task_name}'",
                "cumulative_reward": 0.0,
            }]
            return obs, new_history

        def _parse_assignments(df_value) -> List[Dict[str, str]]:
            rows = []
            if isinstance(df_value, pd.DataFrame):
                rows = df_value.fillna("").to_dict("records")
            elif isinstance(df_value, dict):
                headers = df_value.get("headers", [])
                data = df_value.get("data", [])
                for row_vals in data:
                    row = {headers[i]: row_vals[i] if i < len(row_vals) else "" for i in range(len(headers))}
                    rows.append(row)
            elif isinstance(df_value, list):
                for row_vals in df_value:
                    if isinstance(row_vals, (list, tuple)) and len(row_vals) >= 3:
                        rows.append({"Employee": row_vals[0], "Skill": row_vals[1], "Task Assignment": row_vals[2]})

            assignments = []
            for row in rows:
                employee_id = str(row.get("Employee", "")).strip()
                task_id = str(row.get("Task Assignment", "")).strip()
                if employee_id and task_id and task_id.lower() != "none":
                    assignments.append({"employee_id": employee_id, "task_id": task_id})
            return assignments

        async def execute_day_cycle(df_value, contingency, reprio, task_name, obs_dict, history):
            if web_manager is None:
                obs = dict(obs_dict or _default_obs(task_name))
                obs["message"] = "Execute unavailable (no web manager)."
                return obs, list(history or [])

            if not obs_dict:
                serialized = await web_manager.reset_environment({"task_id": task_name})
                obs_dict = _normalize_observation(serialized)

            action_data = {
                "assignments": _parse_assignments(df_value),
                "reprioritized_tasks": list(reprio or []),
                "contingency_action": contingency or "none",
            }

            serialized = await web_manager.step_environment(action_data)
            obs = _normalize_observation(serialized)

            prev_history = list(history or [])
            cumulative_before = prev_history[-1]["cumulative_reward"] if prev_history else 0.0
            reward = float(obs.get("reward", 0.0) or 0.0)
            prev_history.append({
                "day": obs.get("day", 1),
                "message": obs.get("message") or f"Executed day cycle ({len(action_data['assignments'])} assignments)",
                "cumulative_reward": cumulative_before + reward,
            })
            return obs, prev_history

        def auto_assign_tasks(obs_dict):
            if not obs_dict:
                return pd.DataFrame(columns=["Employee", "Skill", "Task Assignment"])

            tasks = list(obs_dict.get("tasks", []))
            employees = list(obs_dict.get("employees", []))
            if not tasks or not employees:
                return pd.DataFrame(columns=["Employee", "Skill", "Task Assignment"])

            task_by_id = {t.get("id"): t for t in tasks}

            def is_ready(task):
                if task.get("status") in ["done", "blocked"]:
                    return False
                for dep in task.get("dependencies", []):
                    dep_task = task_by_id.get(dep)
                    if not dep_task or dep_task.get("status") != "done":
                        return False
                return True

            ready_tasks = [t for t in tasks if is_ready(t)]
            priority_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            ready_tasks.sort(key=lambda t: (priority_rank.get(t.get("priority", "low"), 4), not t.get("is_critical_path", False), t.get("remaining_effort", 999)))

            available_employees = [e for e in employees if e.get("available", True)]
            assignments = {}
            used_tasks = set()

            for emp in available_employees:
                best_task = None
                best_score = -10
                emp_skills = set(emp.get("skills", []))
                for task in ready_tasks:
                    task_id = task.get("id")
                    if not task_id or task_id in used_tasks:
                        continue
                    required = task.get("required_skill", "")
                    score = 0
                    if required in emp_skills:
                        score += 10
                    elif any(s in required for s in emp_skills):
                        score += 5
                    score += 2 if task.get("is_critical_path") else 0
                    score -= float(emp.get("burnout", 0.0)) * 3
                    if score > best_score:
                        best_score = score
                        best_task = task
                if best_task and best_score >= 0:
                    task_id = best_task.get("id")
                    assignments[emp.get("id")] = task_id
                    used_tasks.add(task_id)

            rows = []
            for emp in employees:
                rows.append([
                    emp.get("id", ""),
                    " • ".join(emp.get("skills", [])),
                    assignments.get(emp.get("id"), "None"),
                ])

            return pd.DataFrame(rows, columns=["Employee", "Skill", "Task Assignment"])

        def _default_obs(task_name: str = "easy"):
            task_defaults = {
                "easy": {"days_remaining": 11, "budget_remaining": 120000},
                "medium": {"days_remaining": 17, "budget_remaining": 180000},
                "hard": {"days_remaining": 24, "budget_remaining": 250000},
            }
            defaults = task_defaults.get(task_name, task_defaults["easy"])
            return {
                "day": 1,
                "days_remaining": defaults["days_remaining"],
                "budget_remaining": defaults["budget_remaining"],
                "project_completion": 0.0,
                "blocked_tasks": 0,
                "overdue_tasks": 0,
                "average_burnout": 0.0,
                "reward": 0.0,
                "message": "Dummy scenario initialized",
                "employees": [],
                "tasks": [],
            }

            history = list(history or [])
            history.append({
                "day": obs.get("day", 1),
                "message": f"Dummy tasks synced to team size ({team_size})",
                "cumulative_reward": history[-1]["cumulative_reward"] if history else 0.0,
            })
            return obs, history

        # Note: In a real OpenEnv context, create_app attaches the environment instance.
        # These function signatures must match what OpenEnv expects if it binds directly.
        # However, we'll keep our updated logic for a premium experience.

        reset_btn.click(
            fn=reset_env,
            inputs=[task_selector, history_state],
            outputs=[obs_state, history_state]
        ).then(
            fn=update_ui_components,
            inputs=[obs_state, history_state],
            outputs=[
                comp_box, days_box, block_box, budget_box,
                team_meters,
                assignment_df,
                reprio_select,
                reward_plot,
                step_rew_box, tot_rew_box,
                event_log_html
            ]
        )

        auto_assign_btn.click(
            fn=auto_assign_tasks,
            inputs=[obs_state],
            outputs=[assignment_df],
        )
        
        step_btn.click(
            fn=execute_day_cycle,
            inputs=[assignment_df, contingency_select, reprio_select, task_selector, obs_state, history_state],
            outputs=[obs_state, history_state]
        ).then(
            fn=update_ui_components,
            inputs=[obs_state, history_state],
            outputs=[
                comp_box, days_box, block_box, budget_box,
                team_meters,
                assignment_df,
                reprio_select,
                reward_plot,
                step_rew_box, tot_rew_box,
                event_log_html
            ]
        )
        
    return demo

# Export for OpenEnv
def build_gradio_ui(web_manager=None, *args, **kwargs) -> gr.Blocks:
    """Builder function compatible with OpenEnv's gradio_builder parameter."""
    return create_custom_gradio_ui(web_manager=web_manager)
