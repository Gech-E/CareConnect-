FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./

# Install dependencies using pip and standard python tools.
# In a real environment, we might use uv or poetry.
RUN pip install --no-cache-dir hatchling \
    && pip install --no-cache-dir .

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
