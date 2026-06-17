# Debian 13 (trixie) Python 3.12 build image.
# Update digest after verifying the new image on Docker Hub:
#   docker pull python:3.12-slim-trixie
#   docker inspect python:3.12-slim-trixie --format '{{index .RepoDigests 0}}'
FROM python:3.12-slim-trixie@sha256:d764629ce0ddd8c71fd371e9901efb324a95789d2315a47db7e4d27e78f1b0e9

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    PIP_CONSTRAINT=/app/requirements/constraints.txt

WORKDIR /app

RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get upgrade -y --no-install-recommends \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        binutils \
        libasound2 \
        libpulse0 \
        libxcb-cursor0 \
        tk \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN python -c "import tkinter; print('tkinter-ok')"

RUN groupadd --gid 1000 builder \
    && useradd --uid 1000 --gid builder --create-home --shell /usr/sbin/nologin builder \
    && chown -R builder:builder /app

COPY pyproject.toml README.md LICENSE ./
COPY requirements/constraints.txt ./requirements/constraints.txt
COPY src/meeting_mojiokoshi/__init__.py ./src/meeting_mojiokoshi/__init__.py

RUN python -m pip install "pip==26.1.2" \
    && python -m pip install --resume-retries 20 -c requirements/constraints.txt -e ".[build]"

COPY src ./src
COPY packaging ./packaging
COPY scripts ./scripts

RUN chown -R builder:builder /app

USER builder

CMD ["python", "-m", "meeting_mojiokoshi"]
