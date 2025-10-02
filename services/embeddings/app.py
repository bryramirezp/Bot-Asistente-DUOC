from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
from typing import List
import logging
import os

# Configuración de logging
logging.basicConfig(
    level=os.environ.get('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Duoc UC - Embeddings Service",
    description="Servicio de generación de embeddings para RAG local",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cargar modelo
MODEL_NAME = os.environ.get('MODEL_NAME', 'sentence-transformers/all-MiniLM-L6-v2')
logger.info(f"Cargando modelo: {MODEL_NAME}")
model = SentenceTransformer(MODEL_NAME)
logger.info(f"Modelo cargado. Dimensión: {model.get_sentence_embedding_dimension()}")

class EmbedRequest(BaseModel):
    texts: List[str] = Field(..., min_items=1, max_items=100)

class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    dimension: int
    model: str

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model": MODEL_NAME,
        "dimension": model.get_sentence_embedding_dimension()
    }

@app.post("/embed", response_model=EmbedResponse)
async def create_embeddings(request: EmbedRequest):
    """Genera embeddings para una lista de textos"""
    try:
        logger.info(f"Generando embeddings para {len(request.texts)} textos")
        embeddings = model.encode(request.texts, show_progress_bar=False).tolist()
        
        return EmbedResponse(
            embeddings=embeddings,
            dimension=model.get_sentence_embedding_dimension(),
            model=MODEL_NAME
        )
    except Exception as e:
        logger.error(f"Error generando embeddings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {
        "service": "Duoc UC Embeddings Service",
        "model": MODEL_NAME,
        "endpoints": {
            "health": "/health",
            "embed": "/embed (POST)"
        }
    }