from app.pricing import cost_usd


def test_cost_usd_bills_uncached_input_plus_cache_rates():
    # claude-sonnet-5: input 3.00, output 15.00, cache_read 0.30, cache_write 3.75 ($/Mtok).
    # input_tokens is the TOTAL prompt count including cached tokens, so 2M input where
    # 1M was cache-read and 1M cache-written leaves 0 uncached input.
    cost = cost_usd(
        "claude-sonnet-5",
        input_tokens=2_000_000,
        output_tokens=1_000_000,
        cache_read_tokens=1_000_000,
        cache_write_tokens=1_000_000,
    )
    assert cost == 15.00 + 0.30 + 3.75


def test_cost_usd_does_not_double_charge_cache_reads():
    # A fully cached prompt costs the cache-read rate, not input + cache-read.
    cost = cost_usd(
        "claude-sonnet-5",
        input_tokens=1_000_000,
        output_tokens=0,
        cache_read_tokens=1_000_000,
        cache_write_tokens=0,
    )
    assert cost == 0.30


def test_cost_usd_zero_for_unknown_model():
    assert cost_usd("no-such-model", input_tokens=1000, output_tokens=1000, cache_read_tokens=0, cache_write_tokens=0) == 0.0


def test_cost_usd_scales_linearly():
    per_mtok = cost_usd("gpt-5.1-mini", input_tokens=1_000_000, output_tokens=0, cache_read_tokens=0, cache_write_tokens=0)
    per_1k = cost_usd("gpt-5.1-mini", input_tokens=1_000, output_tokens=0, cache_read_tokens=0, cache_write_tokens=0)
    assert round(per_mtok / 1000, 6) == round(per_1k, 6)
