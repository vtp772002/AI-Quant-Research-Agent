from quant_research_agent.data.loader import MarketDataRequest, load_market_data
from quant_research_agent.data.integrity import assess_market_data_integrity


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


def test_data_integrity_report_flags_non_institutional_sources():
    request = MarketDataRequest(
        source="synthetic",
        universe=["AAA", "BBB", "CCC", "DDD", "EEE"],
        start="2021-01-01",
        end="2021-09-30",
        seed=7,
    )
    data = load_market_data(request)

    report = assess_market_data_integrity(
        data=data,
        source=request.source,
        requested_symbols=request.universe,
        start=request.start,
        end=request.end,
        point_in_time_universe=False,
        survivorship_bias_free=False,
        corporate_actions_adjusted=False,
    )

    assert report.row_count == len(data)
    assert report.missing_symbols == []
    assert len(report.quality_by_symbol) == 5
    assert all(item.coverage == 1.0 for item in report.quality_by_symbol)
    assert any("Synthetic data validates mechanics" in warning for warning in report.warnings)
    assert any("not marked survivorship-bias-free" in warning for warning in report.warnings)
