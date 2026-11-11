# Image Linux pour déployer tts-server sur Render (ou tout hébergeur basé conteneurs).
# Même code Python que le dev Windows (app/) — seule différence : le binaire Rhubarb Lip
# Sync est le build Linux officiel (bin/rhubarb.exe est Windows-only, inutilisable ici).

FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl unzip && \
    rm -rf /var/lib/apt/lists/*

# Rhubarb Lip Sync 1.14.0 (build Linux officiel) — même version exacte que bin/rhubarb.exe
# vendored pour le dev Windows, pour garantir une sortie identique entre les deux environnements.
RUN curl -fsSL -o /tmp/rhubarb.zip \
      https://github.com/DanielSWolf/rhubarb-lip-sync/releases/download/v1.14.0/Rhubarb-Lip-Sync-1.14.0-Linux.zip && \
    unzip -q /tmp/rhubarb.zip -d /opt && \
    mv /opt/Rhubarb-Lip-Sync-1.14.0-Linux /opt/rhubarb && \
    chmod +x /opt/rhubarb/rhubarb && \
    rm /tmp/rhubarb.zip

ENV RHUBARB_PATH=/opt/rhubarb/rhubarb
ENV FFMPEG_PATH=ffmpeg
ENV PORT=8080

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
