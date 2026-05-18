Return JSON with keys: plan_summary, steps, assumptions, missing_information, risk_notes.
Each step must include: step_id, title, kind, intent, depends_on, inputs,
expected_outputs, required_capabilities, timeout_sec, retryable, optional,
risk_level, on_failure.
