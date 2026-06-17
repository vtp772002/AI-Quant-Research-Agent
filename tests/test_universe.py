from pathlib import Path

from quant_research_agent.data.loader import generate_synthetic_ohlcv
from quant_research_agent.data.universe import apply_universe_membership, resolve_universe


def test_csv_universe_provider_resolves_and_filters_membership(tmp_path: Path):
    membership_path = tmp_path / "membership.csv"
    membership_path.write_text(
        "symbol,start,end\n"
        "AAA,2020-01-01,2020-12-31\n"
        "BBB,2020-06-01,2021-12-31\n"
        "CCC,2018-01-01,2019-12-31\n",
        encoding="utf-8",
    )

    universe = resolve_universe(
        static_universe=[],
        start="2020-01-01",
        end="2021-12-31",
        provider_kind="csv",
        provider_path=membership_path,
    )
    data = generate_synthetic_ohlcv(
        symbols=["AAA", "BBB", "CCC"],
        start="2020-01-01",
        end="2021-12-31",
        seed=3,
    )
    filtered = apply_universe_membership(data, universe.membership)

    assert universe.symbols == ["AAA", "BBB"]
    assert universe.point_in_time
    assert universe.survivorship_bias_free
    assert filtered.index.get_level_values("symbol").nunique() == 2
    assert filtered.xs("AAA", level="symbol").index.max().year == 2020
    assert filtered.xs("BBB", level="symbol").index.min().month == 6
