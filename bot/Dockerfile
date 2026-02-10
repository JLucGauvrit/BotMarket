# Utilise une image légère mais compatible avec les drivers NVIDIA
FROM python:3.11-slim

# Installation des dépendances système nécessaires pour le GPU/CUDA
RUN apt-get update && apt-get install -y \
    curl \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /brain
COPY requirements.txt .

RUN pip install --upgrade pip setuptools wheel && \
     pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "main.py"]