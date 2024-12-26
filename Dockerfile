FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

RUN apt-get -y update &&  \
    apt-get install -y ffmpeg &&  \
    apt-get clean  \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD ["python", "main.py"]