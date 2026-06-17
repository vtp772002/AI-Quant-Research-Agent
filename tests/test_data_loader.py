from pathlib import Path

import pandas as pd

from quant_research_agent.data.loader import MarketDataRequest, generate_synthetic_ohlcv, load_market_data
from quant_research_agent.data.integrity import assess_market_data_integrity
from quant_research_agent.data.snapshot import file_sha256, load_snapshot_provenance


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


def test_csv_snapshot_loader_validates_manifest_provenance(tmp_path: Path):
    symbols = ["AAA", "BBB", "CCC", "DDD", "EEE"]
    snapshot_path = tmp_path / "snapshot.csv"
    manifest_path = tmp_path / "snapshot.yaml"
    source = generate_synthetic_ohlcv(
        symbols=symbols,
        start="2021-01-01",
        end="2021-09-30",
        seed=11,
    )
    source.reset_index().to_csv(snapshot_path, index=False)
    manifest_path.write_text(
        "\n".join(
            [
                "dataset_id: golden-test-v1",
                "vendor: InternalGolden",
                "as_of: '2021-10-01'",
                "created_at: '2021-10-01T00:00:00Z'",
                f"content_sha256: {file_sha256(snapshot_path)}",
                f"row_count: {len(source)}",
                "symbols: [AAA, BBB, CCC, DDD, EEE]",
                "start: '2021-01-01'",
                "end: '2021-09-30'",
                "point_in_time_universe: true",
                "survivorship_bias_free: true",
                "corporate_actions_adjusted: true",
            ]
        ),
        encoding="utf-8",
    )

    loaded = load_market_data(
        MarketDataRequest(
            source="csv_snapshot",
            universe=symbols,
            start="2021-01-01",
            end="2021-09-30",
            snapshot_path=snapshot_path,
        )
    )
    provenance = load_snapshot_provenance(
        manifest_path=manifest_path,
        data_path=snapshot_path,
        data=loaded,
        require_hash=True,
    )
    report = assess_market_data_integrity(
        data=loaded,
        source="csv_snapshot",
        requested_symbols=symbols,
        start="2021-01-01",
        end="2021-09-30",
        point_in_time_universe=False,
        survivorship_bias_free=False,
        corporate_actions_adjusted=False,
        provenance=provenance,
    )

    pd.testing.assert_index_equal(loaded.index, source.index)
    pd.testing.assert_frame_equal(loaded, source, check_exact=False, rtol=1e-12)
    assert provenance is not None
    assert provenance.hash_matches
    assert provenance.row_count_matches
    assert provenance.symbol_set_matches
    assert provenance.date_range_matches
    assert report.point_in_time_universe
    assert report.survivorship_bias_free
    assert report.corporate_actions_adjusted
    assert not any("Snapshot manifest" in warning for warning in report.warnings)
