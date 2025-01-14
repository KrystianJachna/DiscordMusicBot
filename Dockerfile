FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

RUN apt-get -y update &&  \
    apt-get install -y ffmpeg &&  \
    apt-get clean  \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

# cookies.txt may or may not exist
# since COPY requires at least one file to exist, wildcard is used
# to ensure that the COPY command will not fail
COPY Dockerfile cookies.txt* /app/

COPY ./src /app/src

CMD ["python", "./src/main.py"]