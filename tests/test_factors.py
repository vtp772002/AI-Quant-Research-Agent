from quant_research_agent.data.loader import generate_synthetic_ohlcv
from quant_research_agent.factors.registry import compute_factor_library, factor_names


def test_factor_library_exposes_twenty_plus_factors():
    data = generate_synthetic_ohlcv(
        symbols=["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"],
        start="2020-01-01",
        end="2021-12-31",
    )

    factors = compute_factor_library(data)

    assert len(factor_names()) >= 20
    assert set(factor_names()).issubset(factors.columns)
    assert factors["momentum_20d"].notna().any()
    assert factors["volatility_20d"].notna().any()
