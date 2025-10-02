#!/usr/bin/env python3
"""
Script para indexar documentos PDF en OpenSearch
"""
import PyPDF2
import requests
from opensearchpy import OpenSearch
from pathlib import Path
import json

OPENSEARCH_HOST = 'localhost:9200'
EMBEDDINGS_URL = 'http://localhost:8001'
INDEX_NAME = 'duoc-kb'
DOCS_DIR = Path('services/documents')

def main():
    print("Iniciando indexación de documentos...")
    
    # Conectar a OpenSearch
    client = OpenSearch(
        hosts=[OPENSEARCH_HOST],
        use_ssl=False,
        verify_certs=False
    )
    
    # Crear índice
    create_index(client)
    
    # Procesar PDFs
    pdf_files = list(DOCS_DIR.glob('*.pdf'))
    print(f"Encontrados {len(pdf_files)} archivos PDF")
    
    for pdf_path in pdf_files:
        print(f"\nProcesando: {pdf_path.name}")
        chunks = extract_chunks_from_pdf(pdf_path)
        print(f"  Extraídos {len(chunks)} fragmentos")
        
        for i, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            
            doc = {
                'text': chunk,
                'embedding': embedding,
                'source': pdf_path.name,
                'chunk_id': i,
                'metadata': {
                    'file': pdf_path.name,
                    'chunk_index': i
                }
            }
            
            client.index(index=INDEX_NAME, body=doc)
        
        print(f"  ✓ Indexados {len(chunks)} fragmentos")
    
    print(f"\n✓ Indexación completada. Total documentos: {client.count(index=INDEX_NAME)['count']}")

def create_index(client):
    """Crea el índice con mapping para vectores"""
    index_body = {
        "settings": {
            "index": {
                "knn": True,
                "knn.algo_param.ef_search": 100
            }
        },
        "mappings": {
            "properties": {
                "text": {"type": "text"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": 384,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "nmslib"
                    }
                },
                "source": {"type": "keyword"},
                "chunk_id": {"type": "integer"},
                "metadata": {"type": "object"}
            }
        }
    }
    
    if client.indices.exists(index=INDEX_NAME):
        print(f"Eliminando índice existente: {INDEX_NAME}")
        client.indices.delete(index=INDEX_NAME)
    
    client.indices.create(index=INDEX_NAME, body=index_body)
    print(f"Índice creado: {INDEX_NAME}")

def extract_chunks_from_pdf(pdf_path, chunk_size=500, overlap=50):
    """Extrae texto del PDF y lo divide en chunks"""
    chunks = []
    
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ''
        
        for page in pdf_reader.pages:
            text += page.extract_text() + '\n'
        
        # Dividir en chunks
        words = text.split()
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if len(chunk.strip()) > 100:  # Solo chunks significativos
                chunks.append(chunk.strip())
    
    return chunks

def get_embedding(text):
    """Obtiene embedding del servicio"""
    response = requests.post(
        f"{EMBEDDINGS_URL}/embed",
        json={"texts": [text]},
        timeout=30
    )
    response.raise_for_status()
    return response.json()['embeddings'][0]

if __name__ == "__main__":
    main()