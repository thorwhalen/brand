"""LLM-based brand evaluation scorers.

Uses Claude (via the Anthropic API) to evaluate brand names on subjective
qualities that are difficult to capture with rule-based scorers: overall
brand appeal, connotation quality, global safety, and domain fit.

Requires the ``anthropic`` package and a valid ``ANTHROPIC_API_KEY``.
"""

import json

from brand.registry import scorers


_DEFAULT_CONTEXT = (
    "AI-enabled tools for sociology and health researchers, analysts, and clinicians"
)

_RATING_PROMPT = """\
You are a brand naming expert. Rate each candidate brand name on a scale of 1-10 \
for each criterion below. The company builds {context}.

Criteria:
1. **memorability**: How easy is the name to remember?
2. **appeal**: How appealing and professional does it sound?
3. **positive_connotation**: Does it evoke positive associations (innovation, \
trust, clarity, health, insight)?
4. **global_safety**: Is it free of negative/embarrassing meanings in major \
world languages (English, Spanish, French, German, Portuguese, Mandarin, \
Japanese, Arabic, Hindi)?
5. **domain_fit**: How well does it suit a technology/research company?

Return ONLY a JSON array. Each element must be an object with keys: \
"name", "memorability", "appeal", "positive_connotation", "global_safety", \
"domain_fit", "overall" (weighted average, you choose weights), and \
"rationale" (one sentence).

Names to rate:
{names_list}
"""


_usage_log: list[dict] = []
"""Module-level log of token usage across all API calls."""


def _call_claude(prompt: str, *, model: str = 'claude-sonnet-4-20250514') -> str:
    """Call the Anthropic API and return the text response."""
    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "LLM scorers require the 'anthropic' package. "
            "Install with: pip install anthropic"
        )

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=model,
        max_tokens=8192,
        messages=[{'role': 'user', 'content': prompt}],
    )
    _usage_log.append({
        'model': message.model,
        'input_tokens': message.usage.input_tokens,
        'output_tokens': message.usage.output_tokens,
    })
    return message.content[0].text


def get_usage_summary() -> dict:
    """Return cumulative token usage and estimated cost.

    Pricing (as of 2025): Claude Sonnet — $3/M input, $15/M output.
    """
    total_input = sum(u['input_tokens'] for u in _usage_log)
    total_output = sum(u['output_tokens'] for u in _usage_log)
    # Sonnet pricing
    cost_input = total_input * 3.0 / 1_000_000
    cost_output = total_output * 15.0 / 1_000_000
    return {
        'api_calls': len(_usage_log),
        'total_input_tokens': total_input,
        'total_output_tokens': total_output,
        'total_tokens': total_input + total_output,
        'estimated_cost_usd': round(cost_input + cost_output, 4),
        'cost_breakdown': {
            'input': round(cost_input, 4),
            'output': round(cost_output, 4),
        },
    }


def _parse_ratings(text: str) -> list[dict]:
    """Extract the JSON array from Claude's response."""
    # Find JSON array in the response
    text = text.strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try to extract JSON from markdown code block
    import re

    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try to find array brackets
    start = text.find('[')
    end = text.rfind(']')
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return []


@scorers.register(
    'llm_brand_rating',
    description='LLM-based brand quality rating (1-10 across multiple criteria)',
    cost='expensive',
    requires_network=True,
    latency='slow',
    parallelizable=False,  # Batch scorer — handles multiple names at once
)
def llm_brand_rating(name: str, *, context: str = _DEFAULT_CONTEXT) -> dict:
    """Rate a single name using Claude.

    Returns a dict with keys: memorability, appeal, positive_connotation,
    global_safety, domain_fit, overall, rationale.

    >>> isinstance(llm_brand_rating.__doc__, str)  # just check it exists
    True
    """
    prompt = _RATING_PROMPT.format(
        context=context,
        names_list=name,
    )
    text = _call_claude(prompt)
    ratings = _parse_ratings(text)
    if ratings:
        return ratings[0]
    return {'error': 'Could not parse LLM response', 'raw': text[:500]}


def llm_brand_rating_batch(
    names: list[str],
    *,
    context: str = _DEFAULT_CONTEXT,
    batch_size: int = 50,
    model: str = 'claude-sonnet-4-20250514',
) -> dict[str, dict]:
    """Rate multiple names in batches using Claude.

    More efficient than calling ``llm_brand_rating`` one by one.
    Returns a dict mapping name → rating dict.

    Parameters
    ----------
    names : list[str]
        Candidate names to rate.
    context : str
        Company description for the LLM prompt.
    batch_size : int
        Names per API call (default 50).
    model : str
        Claude model to use.

    Returns
    -------
    dict[str, dict]
        Mapping of name → {memorability, appeal, ..., overall, rationale}.
    """
    import math
    import sys

    total_batches = math.ceil(len(names) / batch_size)
    results = {}
    for batch_idx, i in enumerate(range(0, len(names), batch_size), 1):
        batch = names[i:i + batch_size]
        names_list = '\n'.join(f'- {n}' for n in batch)
        prompt = _RATING_PROMPT.format(
            context=context,
            names_list=names_list,
        )
        text = _call_claude(prompt, model=model)
        ratings = _parse_ratings(text)
        # Match ratings back to names
        matched = 0
        for rating in ratings:
            rname = rating.get('name', '').lower()
            if rname in {n.lower() for n in batch}:
                results[rname] = rating
                matched += 1
        # Fill in any missing names with error marker
        for n in batch:
            if n.lower() not in results:
                results[n.lower()] = {'error': 'not rated in batch', 'overall': 0}
        usage = _usage_log[-1] if _usage_log else {}
        print(
            f'  Batch {batch_idx}/{total_batches}: '
            f'{matched}/{len(batch)} rated, '
            f'{usage.get("input_tokens", "?")}+{usage.get("output_tokens", "?")} tokens',
            file=sys.stderr, flush=True,
        )
    return results
