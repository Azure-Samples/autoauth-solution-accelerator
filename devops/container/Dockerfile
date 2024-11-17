FROM python:3.11-slim-buster

WORKDIR /app

ENV PYTHONPATH "${PYTHONPATH}:/app"

COPY src /app/src
COPY app /app/app
COPY utils/ml_logging.py /app/utils/ml_logging.py 
COPY utils/__init__.py /app/utils/__init__.py  
COPY utils/images/ /app/utils/images/
COPY requirements.txt /app/requirements.txt

RUN mkdir -p /app/.streamlit
COPY app/settings/config.toml /app/.streamlit/config.toml
RUN pip install --no-cache-dir -r requirements.txt
ENV STREAMLIT_CONFIG_FILE=/app/.streamlit/config.toml

EXPOSE 8501

ENTRYPOINT ["streamlit", "run"]
CMD ["app/streamlit/Home.py"]

