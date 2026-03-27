"""
advisors/recommendation_policy.py — Policy rules for recommendations.

Owns: recommendation selection policy, filtering rules,
policy parameters (e.g. budget constraints, priority rules).

Must not own: scoring logic (that lives in evaluators/).
Consumes: evaluator outputs only.

Extracted from: optimizer/ and engine/lab_advisory.py (T5).
"""
# T5: extract recommendation policy here
