FROM python:3.13-alpine
WORKDIR /app/wfs
COPY requirements.txt /app/wfs/
RUN pip install -r requirements.txt
COPY . /app/wfs
EXPOSE 8000
CMD ["uvicorn", "ogc_api.main:app", "--host", "0.0.0.0", "--port", "8000"]