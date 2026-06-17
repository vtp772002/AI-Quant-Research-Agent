from quant_research_agent.data.loader import MarketDataRequest, load_market_data


def test_synthetic_loader_returns_reproducible_panel():
    request = MarketDataRequest(
        source="synthetic",
        universe=["AAA", "BBB", "CCC", "DDD", "EEE"],
        start="2021-01-01",
        end="2021-09-30",
        seed=7,
    )

    first = load_market_data(request)
    second = load_market_data(request)

    assert first.equals(second)
    assert first.index.names == ["date", "symbol"]
    assert {"open", "high", "low", "close", "adj_close", "volume"}.issubset(first.columns)
    assert first.index.get_level_values("symbol").nunique() == 5
