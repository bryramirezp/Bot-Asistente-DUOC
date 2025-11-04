import json
import boto3
import os
import logging

# Configuración del logger para una mejor observabilidad en CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Variables de Entorno (Configurar en la consola de Lambda) ---
# Se obtienen las configuraciones del entorno para evitar hardcodear valores.
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID')
MODEL_ARN = os.environ.get('MODEL_ARN') # ARN del modelo Cohere Command R
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN') # Dominio del frontend para CORS

# Inicializar el cliente de Bedrock Agent Runtime fuera del handler para reutilización
bedrock_agent_runtime = boto3.client(
    'bedrock-agent-runtime',
    region_name=AWS_REGION
)



def handler(event, context):
    """
    Orquesta el flujo RAG invocando la API RetrieveAndGenerate de Bedrock Knowledge Bases.
    Esta función actúa como el backend seguro para el chatbot de Duoc UC.
    """
    logger.info(f"Iniciando ejecución para la solicitud: {event.get('requestContext', {}).get('requestId')}")

    # Validar que las variables de entorno críticas estén configuradas
    if not all([KNOWLEDGE_BASE_ID, MODEL_ARN, ALLOWED_ORIGIN]):
        logger.error("Error de configuración: Faltan una o más variables de entorno.")
        return create_response(500, {'error': 'Error de configuración interna del servidor.'})

    try:
        body = json.loads(event.get('body', '{}'))
        query = body.get('query', '').strip()

        if not query:
            logger.warning("Solicitud recibida sin una consulta (query).")
            return create_response(400, {'error': 'El campo "query" es requerido.'})

        logger.info(f"Procesando consulta: '{query}'")

        # --- Lógica RAG Simplificada ---
        # Única llamada a Bedrock para orquestar todo el flujo RAG.
        response = bedrock_agent_runtime.retrieve_and_generate(
            input={'text': query},
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': KNOWLEDGE_BASE_ID,
                    'modelArn': MODEL_ARN,
                    'generationConfiguration': {
                        'inferenceConfig': {
                            'textInferenceConfig': {
                                'temperature': 0.2,
                                'maxTokens': 1024,
                            }
                        }
                    }
                }
            }
        )

        # Extraer la respuesta y las fuentes (citas)
        answer = response['output']['text']
        citations = response.get('citations', [])

        # Formatear las fuentes para enviarlas al frontend
        sources = []
        if citations:
            for citation in citations:
                retrieved_refs = citation.get('retrievedReferences', [])
                for ref in retrieved_refs:
                    source_info = {
                        'document': ref.get('location', {}).get('s3Location', {}).get('uri'),
                        'excerpt': ref.get('content', {}).get('text'),
                        'score': ref.get('score')
                    }
                    sources.append(source_info)

        logger.info("Respuesta y fuentes generadas exitosamente.")
        return create_response(200, {'answer': answer, 'sources': sources})

    except Exception as e:
        logger.error(f"Error inesperado en el handler: {str(e)}", exc_info=True)
        return create_response(500, {'error': 'Ocurrió un error interno al procesar tu solicitud.'})


def create_response(status_code, body):
    """Función de utilidad para crear respuestas HTTP consistentes."""
    return {
        'statusCode': status_code,
        'body': json.dumps(body, ensure_ascii=False),  # Soporte para caracteres en español
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST'
        }
    }