FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system --gid 10001 github \
    && useradd --system --uid 10001 --gid 10001 --create-home github

COPY requirements.txt ./

RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY Github ./Github
COPY .env.example ./

RUN chown -R github:github /app

USER github

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.getenv('PORT', '8000'), timeout=4)" || exit 1

CMD ["python", "-m", "Github"]
