FROM python:3.10

WORKDIR /app

COPY workers.py .

# Fix apt issues explicitly
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends ffmpeg ca-certificates && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir boto3 openai

HEALTHCHECK CMD pgrep -f workers.py || exit 1

CMD ["python", "workers.py"]