"""Compatibility CLI wrapper.

The preferred entrypoint is `python -m quant_research_agent.main`, but the
project spec also suggested `python -m src.main`, so this wrapper supports both.
"""

from quant_research_agent.main import main


if __name__ == "__main__":
    raise SystemExit(main())
