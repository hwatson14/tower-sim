"""
app — Application layer.

Owns: orchestration only, CLI entrypoint, pipeline wiring, writing outputs.

Must not own: domain logic. All domain logic lives in input/, qe/,
simulators/, evaluators/, advisors/.
"""
