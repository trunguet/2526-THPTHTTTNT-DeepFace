FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TF_USE_LEGACY_KERAS=1
ENV MODELS_DIR=/app/models
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_REQUIRE_HASHES=0
ENV PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgomp1 \
        libgl1 \
        libsm6 \
        libxext6 \
        libxcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-ml.txt \
    && pip install --no-cache-dir --force-reinstall --no-deps \
        numpy==1.26.4 \
        opencv-python-headless==4.10.0.84

COPY backend/app ./app
COPY models ./models

RUN mkdir -p /root/.deepface/weights \
    && if [ -f /app/models/extraction/arcface_weights.h5 ]; then \
        cp /app/models/extraction/arcface_weights.h5 /root/.deepface/weights/arcface_weights.h5; \
    else \
        python -c "import os; os.environ.setdefault('TF_USE_LEGACY_KERAS', '1'); from deepface import DeepFace; DeepFace.build_model('ArcFace')" \
        || echo "ArcFace weights were not baked into the image; they will be downloaded or mounted at runtime."; \
    fi

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
