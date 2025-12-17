FROM python:3.11-slim-bullseye

WORKDIR /app

ENV PYTHONPATH "${PYTHONPATH}:/app"

COPY src /app/src
COPY app /app/app
COPY evals /app/evals
COPY utils/images/ /app/utils/images/
COPY utils/data/cases/policies /app/utils/data/cases/policies
COPY requirements.txt /app/requirements.txt

COPY ["utils/data/cases/003/b/doctor_notes/003_b (note) .pdf", "/app/utils/data/cases/003/b/doctor_notes/003_b (note) .pdf"]
COPY ["utils/data/cases/003/b/labs/003_b (labs) .pdf", "/app/utils/data/cases/003/b/labs/003_b (labs) .pdf"]
COPY ["utils/data/cases/003/b/pa_form/003_b (form).pdf", "/app/utils/data/cases/003/b/pa_form/003_b (form).pdf"]
COPY ["utils/data/cases/003/a/doctor_notes/003_a (note) .pdf", "/app/utils/data/cases/003/a/doctor_notes/003_a (note) .pdf"]
COPY ["utils/data/cases/003/a/labs/003_a (labs).pdf", "/app/utils/data/cases/003/a/labs/003_a (labs).pdf"]
COPY ["utils/data/cases/003/a/pa_form/003_a (form).pdf", "/app/utils/data/cases/003/a/pa_form/003_a (form).pdf"]

# Use slim frontend requirements (excludes PyTorch, eval libs, etc.)
COPY requirements-frontend.txt /app/requirements-frontend.txt

# Build Streamlit - install build deps, pip install, then cleanup
RUN apt-get update && \
    apt-get -y install --no-install-recommends gcc python3-dev && \
    pip install --no-cache-dir -r requirements-frontend.txt && \
    apt-get purge -y gcc python3-dev && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* /root/.cache/pip

RUN mkdir -p /app/.streamlit
COPY app/frontend/settings/config.toml /app/.streamlit/config.toml
ENV STREAMLIT_CONFIG_FILE=/app/.streamlit/config.toml

EXPOSE 8501

ENTRYPOINT ["streamlit", "run"]
CMD ["app/frontend/streamlit/Home.py"]
