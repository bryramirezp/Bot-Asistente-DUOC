import json
import requests
from opensearchpy import OpenSearch, RequestsHttpConnection
import os
import logging

# Configuración
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

OPENSEARCH_HOST = os.environ.get('OPENSEARCH_HOST', 'localhost:9200')
EMBEDDINGS_URL = os.environ.get('EMBEDDINGS_URL', 'http://localhost:8001')
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.1:8b')
OPENSEARCH_INDEX = os.environ.get('OPENSEARCH_INDEX', 'duoc-kb')

def lambda_handler(event, context):
    """
    Orquestador principal del sistema RAG
    Coordina: Embeddings → OpenSearch → Ollama
    """
    
    # Health check
    if event.get('path') == '/health':
        return create_response(200, {
            'status': 'healthy',
            'services': check_services_health()
        })
    
    try:
        # Extraer query
        body = json.loads(event.get('body', '{}'))
        query = body.get('query', '').strip()
        
        if not query:
            return create_response(400, {'error': 'Query vacía'})
        
        logger.info(f"Query recibida: {query}")
        
        # Pipeline RAG
        query_embedding = generate_embedding(query)
        logger.info(f"Embedding generado: {len(query_embedding)} dims")
        
        relevant_docs = search_documents(query_embedding, top_k=3)
        logger.info(f"Documentos encontrados: {len(relevant_docs)}")
        
        if not relevant_docs:
            return create_response(200, {
                'answer': 'Lo siento, no encontré información relevante para responder tu pregunta.',
                'sources': [],
                'confidence': 'low'
            })
        
        answer = generate_answer(query, relevant_docs)
        logger.info("Respuesta generada exitosamente")
        
        return create_response(200, {
            'answer': answer,
            'sources': [{'source': doc['source'], 'score': doc['score']} for doc in relevant_docs],
            'confidence': 'high' if relevant_docs[0]['score'] > 0.7 else 'medium'
        })
        
    except Exception as e:
        logger.error(f"Error en lambda_handler: {str(e)}", exc_info=True)
        return create_response(500, {
            'error': 'Error interno del servidor',
            'details': str(e)
        })

def generate_embedding(text):
    """Genera embedding usando servicio local"""
    try:
        response = requests.post(
            f"{EMBEDDINGS_URL}/embed",
            json={"texts": [text]},
            timeout=10
        )
        response.raise_for_status()
        return response.json()['embeddings'][0]
    except Exception as e:
        logger.error(f"Error generando embedding: {e}")
        raise

def search_documents(query_embedding, top_k=3):
    """Busca documentos similares en OpenSearch"""
    try:
        host, port = OPENSEARCH_HOST.split(':')
        client = OpenSearch(
            hosts=[{'host': host, 'port': int(port)}],
            http_auth=None,
            use_ssl=False,
            verify_certs=False,
            connection_class=RequestsHttpConnection
        )
        
        search_body = {
            "size": top_k,
            "query": {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                        "params": {"query_vector": query_embedding}
                    }
                }
            },
            "_source": ["text", "source", "metadata"]
        }
        
        response = client.search(index=OPENSEARCH_INDEX, body=search_body)
        
        results = []
        for hit in response['hits']['hits']:
            results.append({
                'text': hit['_source']['text'],
                'source': hit['_source'].get('source', 'unknown'),
                'score': (hit['_score'] - 1.0) / 2.0  # Normalizar a [0,1]
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Error buscando en OpenSearch: {e}")
        raise

def generate_answer(query, documents):
    """Genera respuesta usando Ollama"""
    try:
        context = "\n\n".join([f"[Fuente: {doc['source']}]\n{doc['text']}" for doc in documents])
        
        prompt = f"""Eres un asistente virtual de Duoc UC. Responde la pregunta del estudiante basándote ÚNICAMENTE en el siguiente contexto.

Si la información no está en el contexto, di claramente que no tienes esa información específica.
Sé conciso, claro y amigable. Máximo 3 párrafos.

CONTEXTO:
{context}

PREGUNTA DEL ESTUDIANTE: {query}

RESPUESTA:"""
        
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9
                }
            },
            timeout=120
        )
        response.raise_for_status()
        
        return response.json()['response'].strip()
        
    except Exception as e:
        logger.error(f"Error generando respuesta: {e}")
        raise

def check_services_health():
    """Verifica el estado de los microservicios"""
    health = {}
    
    try:
        r = requests.get(f"{EMBEDDINGS_URL}/health", timeout=5)
        health['embeddings'] = 'up' if r.status_code == 200 else 'down'
    except:
        health['embeddings'] = 'down'
    
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        health['ollama'] = 'up' if r.status_code == 200 else 'down'
    except:
        health['ollama'] = 'down'
    
    try:
        host, port = OPENSEARCH_HOST.split(':')
        r = requests.get(f"http://{host}:{port}/_cluster/health", timeout=5)
        health['opensearch'] = 'up' if r.status_code == 200 else 'down'
    except:
        health['opensearch'] = 'down'
    
    return health

def create_response(status_code, body):
    """Crea respuesta HTTP con CORS"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(body, ensure_ascii=False)
    }