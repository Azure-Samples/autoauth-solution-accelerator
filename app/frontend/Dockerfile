FROM python:3.11-slim-bullseye

WORKDIR /app

ENV PYTHONPATH "${PYTHONPATH}:/app"

COPY src /app/src
COPY app /app/app
COPY utils/ml_logging.py /app/utils/ml_logging.py
COPY utils/__init__.py /app/utils/__init__.py
COPY utils/images/ /app/utils/images/
COPY utils/data/cases/policies /app/utils/data/cases/policies
COPY requirements.txt /app/requirements.txt

COPY ["utils/data/cases/003/b/doctor_notes/003_b (note) .pdf", "/app/utils/data/cases/003/b/doctor_notes/003_b (note) .pdf"]
COPY ["utils/data/cases/003/b/labs/003_b (labs) .pdf", "/app/utils/data/cases/003/b/labs/003_b (labs) .pdf"]
COPY ["utils/data/cases/003/b/pa_form/003_b (form).pdf", "/app/utils/data/cases/003/b/pa_form/003_b (form).pdf"]
COPY ["utils/data/cases/003/a/doctor_notes/003_a (note) .pdf", "/app/utils/data/cases/003/a/doctor_notes/003_a (note) .pdf"]
COPY ["utils/data/cases/003/a/labs/003_a (labs).pdf", "/app/utils/data/cases/003/a/labs/003_a (labs).pdf"]
COPY ["utils/data/cases/003/a/pa_form/003_a (form).pdf", "/app/utils/data/cases/003/a/pa_form/003_a (form).pdf"]

# Build Streamlit
RUN apt-get update && \
    apt-get -y install gcc mono-mcs python3-dev && \
    rm -rf /var/lib/apt/lists/*
RUN mkdir -p /app/.streamlit
COPY app/frontend/settings/config.toml /app/.streamlit/config.toml
RUN pip install --no-cache-dir -r requirements.txt
ENV STREAMLIT_CONFIG_FILE=/app/.streamlit/config.toml

EXPOSE 8501

ENTRYPOINT ["streamlit", "run"]
CMD ["app/frontend/streamlit/Home.py"]
