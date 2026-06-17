FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY configs ./configs
COPY scripts ./scripts

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e ".[service]"

EXPOSE 8000

CMD ["uvicorn", "quant_research_agent.api:app", "--host", "0.0.0.0", "--port", "8000"]
