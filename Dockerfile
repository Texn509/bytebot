FROM python:3.10-slim

# Prevent Python from writing pyc files to disc & buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Ensure latest pip version and setup toolchains
RUN pip install --no-cache-dir --upgrade pip

# Hardcode the module prerequisite directly inside the build layer
RUN pip install --no-cache-dir python-telegram-bot==20.8

# Transfer system application modules
COPY bot.py /app/

# Native runtime initialization
CMD ["python", "bot.py"]