# syntax=docker/dockerfile:1.4
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/app/.venv/bin:${PATH}"

ARG APP_USER=lunia
WORKDIR /opt/app

# system deps include apparmor utilities and cryptsetup for encrypted swap support
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        apparmor \
        apparmor-utils \
        libapparmor1 \
        libapparmor-dev \
        cryptsetup \
        util-linux \
        dumb-init \
        curl \
        ca-certificates \
        git && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --system "${APP_USER}" && \
    useradd --system --gid "${APP_USER}" --home /opt/app "${APP_USER}"

COPY lunia_core/requirements/base.txt /tmp/requirements/base.txt
RUN python -m venv /opt/app/.venv && \
    . /opt/app/.venv/bin/activate && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements/base.txt

# AppArmor profile for Python processes inside the container
COPY deploy/security/apparmor-python.profile /etc/apparmor.d/lunia-python
RUN apparmor_parser -qr /etc/apparmor.d/lunia-python || true

# Encrypted swap helper executed as entrypoint (gracefully degrades if not permitted)
COPY deploy/scripts/enable_encrypted_swap.sh /usr/local/bin/enable_encrypted_swap.sh
RUN chmod 0755 /usr/local/bin/enable_encrypted_swap.sh

# Copy application source
COPY lunia_core /opt/app

USER ${APP_USER}

ENTRYPOINT ["/usr/local/bin/enable_encrypted_swap.sh"]
CMD ["dumb-init", "--", "python", "-m", "app.services.api.flask_app"]
