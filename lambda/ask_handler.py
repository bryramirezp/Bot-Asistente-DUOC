import json
import os
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
import boto3
from botocore.exceptions import ClientError

# Configuración del logger para una mejor observabilidad en CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# LLM Guard imports (opcional)
try:
    from llm_guard.input_scanners import PromptInjection
    from llm_guard.input_scanners.prompt_injection import MatchType
    LLM_GUARD_AVAILABLE = True
except ImportError:
    LLM_GUARD_AVAILABLE = False
    logger.warning("LLM Guard no está disponible. Instalar con: pip install llm-guard")

# --- Variables de Entorno (Configurar en la consola de Lambda) ---
# Se obtienen las configuraciones del entorno para evitar hardcodear valores.
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID')
MODEL_ID = os.environ.get('MODEL_ID')  # ID del modelo (ej: meta.llama3-1-8b-instruct-v1:0)
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN') # Dominio del frontend para CORS

# Construir el ARN del modelo a partir del MODEL_ID y la región
# Formato: arn:aws:bedrock:{region}::foundation-model/{model_id}
MODEL_ARN = None
if MODEL_ID:
    MODEL_ARN = f'arn:aws:bedrock:{AWS_REGION}::foundation-model/{MODEL_ID}'

# Variables opcionales con valores por defecto
TEMPERATURE = float(os.environ.get('TEMPERATURE', '0.2'))
MAX_TOKENS = int(os.environ.get('MAX_TOKENS', '1024'))
MAX_QUERY_LENGTH = int(os.environ.get('MAX_QUERY_LENGTH', '5000'))
MAX_CONTEXT_MESSAGES = int(os.environ.get('MAX_CONTEXT_MESSAGES', '10'))

# Validar que TEMPERATURE esté en rango válido (0.0 a 1.0)
if not 0.0 <= TEMPERATURE <= 1.0:
    logger.warning(f"TEMPERATURE fuera de rango válido ({TEMPERATURE}), usando valor por defecto 0.2")
    TEMPERATURE = 0.2

# Inicializar el cliente de Bedrock Agent Runtime fuera del handler para reutilización
bedrock_agent_runtime = boto3.client(
    'bedrock-agent-runtime',
    region_name=AWS_REGION
)

# Variable de entorno para timeout mínimo (segundos)
MIN_TIMEOUT_SECONDS = float(os.environ.get('MIN_TIMEOUT_SECONDS', '5.0'))

# Variables de entorno para Citation Validation
MIN_CITATION_SCORE = float(os.environ.get('MIN_CITATION_SCORE', '0.7'))
MAX_CITATIONS = int(os.environ.get('MAX_CITATIONS', '5'))

# Variables de entorno para LLM Guard
LLM_GUARD_ENABLED = os.environ.get('LLM_GUARD_ENABLED', 'false').lower() == 'true'
LLM_GUARD_THRESHOLD = float(os.environ.get('LLM_GUARD_THRESHOLD', '0.5'))

# Variables de entorno para Query Optimization (Phase 2)
QUERY_OPTIMIZATION_ENABLED = os.environ.get('QUERY_OPTIMIZATION_ENABLED', 'true').lower() == 'true'
QUERY_EXPANSION_ENABLED = os.environ.get('QUERY_EXPANSION_ENABLED', 'true').lower() == 'true'
HYBRID_SEARCH_ENABLED = os.environ.get('HYBRID_SEARCH_ENABLED', 'true').lower() == 'true'
QUERY_DECOMPOSITION_ENABLED = os.environ.get('QUERY_DECOMPOSITION_ENABLED', 'true').lower() == 'true'
MAX_QUERY_EXPANSIONS = int(os.environ.get('MAX_QUERY_EXPANSIONS', '3'))


class PromptInjectionFilter:
    """
    Filtro para detectar y sanitizar intentos de prompt injection.
    """
    def __init__(self):
        self.dangerous_patterns = [
            r'ignore\s+(all\s+)?previous\s+instructions?',
            r'you\s+are\s+now\s+(in\s+)?developer\s+mode',
            r'system\s+override',
            r'reveal\s+prompt',
            r'forget\s+(all\s+)?previous',
            r'new\s+instructions?',
            r'override\s+system',
            r'ignore\s+all\s+rules',
            r'you\s+must\s+now',
            r'disregard\s+previous',
        ]
        
        # Patrones para detección fuzzy (typoglycemia)
        self.fuzzy_patterns = [
            'ignore', 'bypass', 'override', 'reveal', 
            'delete', 'system', 'forget', 'disregard'
        ]

    def detect_injection(self, text: str) -> bool:
        """
        Detecta intentos de prompt injection.
        
        Args:
            text: Texto a analizar
            
        Returns:
            True si se detecta injection, False si es seguro
        """
        text_lower = text.lower()
        
        # Detección de patrones estándar
        for pattern in self.dangerous_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        # Detección fuzzy para typoglycemia
        words = re.findall(r'\b\w+\b', text_lower)
        for word in words:
            for pattern in self.fuzzy_patterns:
                if self._is_similar_word(word, pattern):
                    return True
        
        return False

    def _is_similar_word(self, word: str, target: str) -> bool:
        """
        Detecta variantes typoglycemia (mismas letras primera/última, medio mezclado).
        
        Args:
            word: Palabra a verificar
            target: Palabra objetivo
            
        Returns:
            True si la palabra es similar (typoglycemia)
        """
        if len(word) != len(target) or len(word) < 3:
            return False
        return (
            word[0] == target[0] and
            word[-1] == target[-1] and
            sorted(word[1:-1]) == sorted(target[1:-1])
        )

    def sanitize_input(self, text: str) -> str:
        """
        Sanitiza el input removiendo caracteres peligrosos y normalizando.
        
        Args:
            text: Texto a sanitizar
            
        Returns:
            Texto sanitizado
        """
        # Normalizar espacios en blanco
        text = re.sub(r'\s+', ' ', text)
        
        # Remover repetición de caracteres (aaaa -> a)
        text = re.sub(r'(.)\1{3,}', r'\1', text)
        
        # Remover caracteres invisibles Unicode
        text = re.sub(r'[\u200b-\u200f\u202a-\u202e]', '', text)
        
        # Filtrar patrones peligrosos
        for pattern in self.dangerous_patterns:
            text = re.sub(pattern, '[FILTERED]', text, flags=re.IGNORECASE)
        
        return text.strip()


class OutputValidator:
    """
    Validador para detectar fugas de información y patrones sospechosos en respuestas.
    """
    def __init__(self):
        self.suspicious_patterns = [
            r'SYSTEM\s*[:]\s*You\s+are',      # Fuga de system prompt
            r'API[_s]KEY[:=]\s*\w+',         # Exposición de API keys
            r'instructions?[:]\s*\d+\.',      # Instrucciones numeradas
            r'ignore\s+previous',             # Intentos de injection en output
            r'new\s+instructions?',
        ]

    def validate_output(self, output: str) -> bool:
        """
        Valida que el output no contenga información sensible o patrones sospechosos.
        
        Args:
            output: Respuesta a validar
            
        Returns:
            True si el output es válido, False si es sospechoso
        """
        output_lower = output.lower()
        for pattern in self.suspicious_patterns:
            if re.search(pattern, output_lower, re.IGNORECASE):
                return False
        return True

    def filter_response(self, response: str, max_length: int = 5000) -> str:
        """
        Filtra la respuesta removiendo contenido sospechoso.
        
        Args:
            response: Respuesta a filtrar
            max_length: Longitud máxima permitida
            
        Returns:
            Respuesta filtrada o mensaje genérico si es inválida
        """
        if not self.validate_output(response):
            logger.warning("Output validation failed - suspicious patterns detected")
            return "No puedo proporcionar esa información por razones de seguridad."
        
        if len(response) > max_length:
            logger.warning(f"Output exceeds maximum length: {len(response)}")
            return response[:max_length] + "..."
        
        return response


# Inicializar filtros de seguridad
prompt_filter = PromptInjectionFilter()
output_validator = OutputValidator()

# Inicializar LLM Guard scanner (si está disponible y habilitado)
llm_guard_scanner = None
if LLM_GUARD_AVAILABLE and LLM_GUARD_ENABLED:
    try:
        llm_guard_scanner = PromptInjection(
            threshold=LLM_GUARD_THRESHOLD,
            match_type=MatchType.FULL
        )
        logger.info(f"LLM Guard habilitado con threshold: {LLM_GUARD_THRESHOLD}")
    except Exception as e:
        logger.warning(f"Error inicializando LLM Guard: {str(e)}. Usando filtro manual.")
        llm_guard_scanner = None
elif LLM_GUARD_ENABLED and not LLM_GUARD_AVAILABLE:
    logger.warning("LLM Guard habilitado pero no disponible. Instalar con: pip install llm-guard")


def extract_request_id(event: Dict[str, Any]) -> str:
    """
    Extrae el request ID del evento para tracking y correlación.
    
    Args:
        event: Evento Lambda
        
    Returns:
        Request ID o 'unknown' si no está disponible
    """
    return (
        event.get('requestContext', {}).get('requestId') or
        event.get('requestId') or
        'unknown'
    )


def check_timeout_remaining(context: Any, min_seconds: float = None) -> bool:
    """
    Verifica que quede suficiente tiempo antes del timeout de Lambda.
    
    Args:
        context: Contexto de Lambda
        min_seconds: Segundos mínimos requeridos (usa MIN_TIMEOUT_SECONDS si no se especifica)
        
    Returns:
        True si hay tiempo suficiente, False si está cerca del timeout
    """
    if context is None:
        return True  # Si no hay contexto, asumir que está bien
    
    if min_seconds is None:
        min_seconds = MIN_TIMEOUT_SECONDS
    
    try:
        remaining_ms = context.get_remaining_time_in_millis()
        remaining_seconds = remaining_ms / 1000.0
        
        if remaining_seconds < min_seconds:
            logger.warning(
                f"Low remaining time: {remaining_seconds:.2f}s (minimum: {min_seconds}s)",
                extra={'remaining_seconds': remaining_seconds, 'min_seconds': min_seconds}
            )
            return False
        
        return True
    except Exception as e:
        logger.warning(f"Error checking timeout: {str(e)}")
        return True  # En caso de error, permitir continuar


def validate_cors_origin(event: Dict[str, Any], allowed_origin: str) -> bool:
    """
    Valida que el origen de la solicitud coincida con el permitido.
    Permite todas las solicitudes si allowed_origin no está configurado o es '*'.
    
    Args:
        event: Evento Lambda con headers de la solicitud
        allowed_origin: Origen permitido configurado en variables de entorno
        
    Returns:
        True si el origen es válido, False si no
    """
    # Si no está configurado o es '*', permitir todas las solicitudes (desarrollo)
    if not allowed_origin or allowed_origin == '*' or allowed_origin.strip() == '':
        logger.debug("CORS validation bypassed: ALLOWED_ORIGIN not set or set to '*'")
        return True
    
    # Obtener origen del header (API Gateway puede usar diferentes formatos)
    headers = event.get('headers', {}) or event.get('multiValueHeaders', {})
    
    # Normalizar headers a minúsculas para búsqueda más robusta
    headers_lower = {k.lower(): v for k, v in headers.items()} if isinstance(headers, dict) else {}
    
    # API Gateway puede pasar headers en minúsculas o con mayúsculas
    origin = (
        headers_lower.get('origin') or
        headers.get('origin') or 
        headers.get('Origin') or
        headers.get('ORIGIN') or
        headers_lower.get('Origin') or
        headers_lower.get('ORIGIN')
    )
    
    if not origin:
        # Si no hay header origin, puede ser una solicitud directa (permitir para desarrollo)
        logger.debug("No Origin header found in request - allowing for development")
        return True  # Permitir si no hay origin header (para desarrollo/API directo)
    
    # Validación exacta del origen
    is_valid = origin == allowed_origin
    
    if not is_valid:
        logger.warning(
            f"CORS validation failed: origin '{origin}' does not match allowed '{allowed_origin}'",
            extra={'requested_origin': origin, 'allowed_origin': allowed_origin}
        )
    else:
        logger.debug(f"CORS validation passed: origin '{origin}' matches allowed origin")
    
    return is_valid


class QueryOptimizer:
    """
    Optimizador de queries para mejorar la recuperación de información.
    Implementa Phase 2: Query Optimization.
    """
    def __init__(self):
        self.synonyms_dict = {
            'matrícula': ['inscripción', 'registro', 'matriculación'],
            'arancel': ['costo', 'precio', 'tarifa', 'pago', 'cuota'],
            'carrera': ['programa', 'técnica', 'profesional', 'estudios'],
            'admisión': ['ingreso', 'postulación', 'inscripción'],
            'gratuidad': ['beca', 'financiamiento', 'ayuda económica'],
            'sostenedor': ['apoderado', 'tutor', 'responsable', 'garante'],
            'requisito': ['requerimiento', 'documento', 'papeles'],
            'fecha': ['día', 'plazo', 'periodo', 'calendario'],
            'campus': ['sede', 'sucursal', 'ubicación', 'dirección'],
            'horario': ['calendario', 'cronograma', 'programa'],
            'certificado': ['diploma', 'título', 'documento'],
            'pago': ['cancelación', 'abono', 'transferencia'],
            'beca': ['gratuidad', 'ayuda', 'financiamiento'],
            'documento': ['papel', 'certificado', 'comprobante'],
            'información': ['datos', 'detalles', 'consultas'],
        }
        
        self.keyword_boost_terms = [
            'cuánto', 'cuánta', 'cuántos', 'cuántas',
            'cuándo', 'dónde', 'qué', 'cómo', 'por qué',
            'requisito', 'documento', 'proceso', 'paso',
            'costo', 'precio', 'arancel', 'pago',
            'fecha', 'plazo', 'horario', 'calendario',
        ]
        
        self.complex_query_indicators = [
            'y', 'además', 'también', 'tambien',
            'cuánto', 'cuánta', 'cuántos', 'cuántas',
            'más', 'menos', 'mejor', 'peor',
        ]
    
    def expand_query(self, query: str) -> str:
        """
        Expande el query agregando sinónimos relevantes.
        
        Args:
            query: Query original del usuario
            
        Returns:
            Query expandido con sinónimos
        """
        if not QUERY_EXPANSION_ENABLED:
            return query
        
        query_lower = query.lower()
        expanded_terms = []
        added_synonyms = set()
        
        words = re.findall(r'\b\w+\b', query_lower)
        
        for word in words:
            expanded_terms.append(word)
            
            if word in self.synonyms_dict and len(added_synonyms) < MAX_QUERY_EXPANSIONS:
                synonyms = self.synonyms_dict[word]
                for synonym in synonyms[:2]:
                    if synonym not in query_lower and synonym not in added_synonyms:
                        expanded_terms.append(synonym)
                        added_synonyms.add(synonym)
                        if len(added_synonyms) >= MAX_QUERY_EXPANSIONS:
                            break
        
        if len(added_synonyms) > 0:
            expanded_query = query
            for synonym in added_synonyms:
                expanded_query += f" {synonym}"
            logger.info(f"Query expandido: '{query}' -> '{expanded_query}' (sinónimos agregados: {len(added_synonyms)})")
            return expanded_query
        
        return query
    
    def enhance_with_keywords(self, query: str) -> str:
        """
        Mejora el query agregando keywords relevantes para búsqueda híbrida.
        No agrega keywords a saludos simples o queries muy cortos que no parecen ser preguntas.
        
        Bedrock Knowledge Bases usa OpenSearch que combina búsqueda semántica (embeddings)
        con búsqueda por keywords. Esta función asegura que el query tenga términos
        importantes que puedan ayudar en la recuperación híbrida, pero solo cuando sea apropiado.
        
        Args:
            query: Query original o expandido
            
        Returns:
            Query mejorado con keywords si es necesario
        """
        if not HYBRID_SEARCH_ENABLED:
            return query
        
        query_lower = query.lower().strip()
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        
        # Lista de saludos simples que no deben ser expandidos
        greetings = ['hola', 'hi', 'hey', 'buenos días', 'buenas tardes', 'buenas noches', 
                     'saludos', 'buen día', 'holi', 'qué tal', 'qué hubo']
        
        # Si es un saludo simple, no agregar keywords
        if query_lower in greetings or (len(query_words) == 1 and query_lower in greetings):
            logger.debug(f"Query es un saludo simple, no se agregarán keywords: '{query}'")
            return query
        
        query_is_short = len(query_words) < 3
        
        # Solo agregar keywords si:
        # 1. El query es corto (< 3 palabras)
        # 2. No es un saludo simple
        # 3. El query parece ser una pregunta real (contiene palabras interrogativas)
        is_question = any(word in query_lower for word in ['qué', 'cuál', 'cuándo', 'dónde', 
                                                            'cómo', 'por qué', 'quién', 'cuánto', 
                                                            'cuánta', 'cuántos', 'cuántas', '?'])
        
        # Si no es una pregunta y es muy corto, probablemente sea un saludo o frase simple
        if query_is_short and not is_question:
            logger.debug(f"Query muy corto sin indicadores de pregunta, no se agregarán keywords: '{query}'")
            return query
        
        if not query_is_short:
            return query
        
        relevant_keywords = []
        for keyword in self.keyword_boost_terms:
            if keyword not in query_words and keyword not in query_lower:
                relevant_keywords.append(keyword)
                if len(relevant_keywords) >= 2:
                    break
        
        if relevant_keywords:
            enhanced_query = f"{query} {' '.join(relevant_keywords)}"
            logger.debug(f"Query mejorado con keywords para búsqueda híbrida: '{enhanced_query}'")
            return enhanced_query
        
        return query
    
    def is_complex_query(self, query: str) -> bool:
        """
        Detecta si un query es complejo (múltiples preguntas o condiciones).
        
        Args:
            query: Query a analizar
            
        Returns:
            True si el query es complejo, False si es simple
        """
        query_lower = query.lower()
        
        question_count = query_lower.count('?')
        if question_count > 1:
            return True
        
        indicator_count = sum(1 for indicator in self.complex_query_indicators if indicator in query_lower)
        if indicator_count >= 2:
            return True
        
        if ' y ' in query_lower or ' además ' in query_lower or ' también ' in query_lower:
            return True
        
        return False
    
    def decompose_query(self, query: str) -> List[str]:
        """
        Descompone un query complejo en sub-queries más simples.
        
        Args:
            query: Query complejo a descomponer
            
        Returns:
            Lista de sub-queries simplificadas
        """
        if not QUERY_DECOMPOSITION_ENABLED:
            return [query]
        
        if not self.is_complex_query(query):
            return [query]
        
        sub_queries = []
        query_lower = query.lower()
        
        if ' y ' in query_lower:
            parts = query.split(' y ')
            sub_queries.extend([part.strip() for part in parts if part.strip()])
        elif ' además ' in query_lower:
            parts = query.split(' además ')
            sub_queries.extend([part.strip() for part in parts if part.strip()])
        elif ' también ' in query_lower:
            parts = query.split(' también ')
            sub_queries.extend([part.strip() for part in parts if part.strip()])
        else:
            question_markers = ['?', '¿']
            for marker in question_markers:
                if marker in query:
                    parts = query.split(marker)
                    sub_queries.extend([part.strip() + '?' for part in parts if part.strip()])
        
        if len(sub_queries) > 1:
            logger.info(f"Query descompuesto: '{query}' -> {len(sub_queries)} sub-queries")
            return sub_queries
        
        return [query]
    
    def optimize_query(self, query: str, history: List[Dict[str, str]] = None) -> str:
        """
        Optimiza un query aplicando todas las técnicas de optimización.
        
        Args:
            query: Query original del usuario
            history: Historial de conversación (opcional)
            
        Returns:
            Query optimizado
        """
        if not QUERY_OPTIMIZATION_ENABLED:
            return query
        
        optimized_query = query
        
        if QUERY_EXPANSION_ENABLED:
            optimized_query = self.expand_query(optimized_query)
        
        if HYBRID_SEARCH_ENABLED:
            optimized_query = self.enhance_with_keywords(optimized_query)
        
        if history:
            last_assistant_msg = None
            for msg in reversed(history):
                if msg.get('role') == 'assistant':
                    last_assistant_msg = msg.get('content', '')
                    break
            
            if last_assistant_msg and len(query.split()) < 5:
                context_keywords = self._extract_keywords_from_context(last_assistant_msg)
                if context_keywords:
                    optimized_query = f"{optimized_query} {context_keywords}"
                    logger.debug(f"Query mejorado con contexto: '{optimized_query}'")
        
        return optimized_query
    
    def _extract_keywords_from_context(self, context: str) -> str:
        """
        Extrae keywords relevantes del contexto de conversación.
        
        Args:
            context: Contexto de conversación anterior
            
        Returns:
            Keywords extraídos como string
        """
        context_lower = context.lower()
        extracted_keywords = []
        
        for term in self.synonyms_dict.keys():
            if term in context_lower and term not in extracted_keywords:
                extracted_keywords.append(term)
                if len(extracted_keywords) >= 2:
                    break
        
        return ' '.join(extracted_keywords) if extracted_keywords else ''


query_optimizer = QueryOptimizer()


# Diccionario de patrones RegEx para chit-chat y sus respuestas
# \b = Límite de palabra (para no coincidir "hola" dentro de "desaholar")
# ^ = Inicio del string
# re.IGNORECASE = Ignorar mayúsculas/minúsculas
CHIT_CHAT_PATTERNS = {
    # Saludos (wena, holis, buenas, aló)
    r'^\b(hola|holis|wena|buenas|alo|buenos días|buenas tardes|buenas noches)\b.*':
        "¡Hola! Soy el asistente virtual de la Mesa de Servicio Estudiantil de Duoc UC. ¿En qué puedo ayudarte hoy?",
    
    # Estado (cómo estás, cómo estai, qué tal)
    r'^\b(c(ó|o)mo est(á|ai)s?|qu(é|e) tal|todo bien)\b.*':
        "Estoy funcionando correctamente, ¡gracias por preguntar! ¿En qué te puedo ayudar?",
    
    # Despedidas (chao, chaíto, nos vemos)
    r'^\b(chao|cha(í|i)to|adi(ó|o)s|nos vemos|cu(í|i)date)\b.*':
        "¡Que te vaya bien! Si tienes más preguntas, estaré aquí.",
    
    # Agradecimientos (gracias, vale, se pasó)
    r'^\b(gracias|muchas gracias|vale|se pas(ó|o))\b.*':
        "¡De nada! Estoy aquí para ayudarte. ¿Necesitas algo más?",
    
    # Confirmaciones (ya, dale, ok, sipo, bacán)
    r'^\b(ya|dale|ok|sipo|ah ya|bac(á|a)n|genial|entendido)\b$':
        "Entendido. ¿Hay algo más en lo que te pueda ayudar?"
}


def handle_chit_chat(query: str) -> Optional[str]:
    """
    Verifica si el query es chit-chat y devuelve una respuesta predefinida.
    
    Utiliza patrones RegEx para detectar modismos chilenos y frases coloquiales comunes
    (saludos, despedidas, agradecimientos, confirmaciones, etc.) y devuelve respuestas
    programadas apropiadas sin necesidad de consultar RAG.
    
    Args:
        query: Query del usuario a verificar
        
    Returns:
        Respuesta predefinida si es chit-chat, None si no lo es
    """
    # Normalizar query: minúsculas y quitar espacios extra
    query_lower = query.lower().strip()
    
    for pattern, response in CHIT_CHAT_PATTERNS.items():
        if re.search(pattern, query_lower, re.IGNORECASE):
            logger.info(f"Chit-chat detectado: '{query}' -> respuesta programada")
            return response
    
    # Si no coincide con nada, no es chit-chat
    return None


def build_context_prompt(query: str, history: List[Dict[str, str]]) -> str:
    """
    Construye un prompt contextual a partir del historial de conversación.
    
    Instruye al LLM a usar el contexto solo cuando sea relevante.
    Para preguntas independientes, el LLM ignora el contexto anterior.
    
    Args:
        query: Consulta actual del usuario
        history: Lista de mensajes de conversación con 'role' y 'content'
        
    Returns:
        Prompt contextual formateado como string
    """
    if not history:
        return query
    
    context_parts = [
        "Conversación anterior:",
        "IMPORTANTE: Usa este contexto SOLO si es relevante para la pregunta actual.",
        "Si la pregunta actual es sobre un tema diferente, ignora el contexto anterior.",
        ""
    ]
    
    # Agregar historial de conversación (últimos MAX_CONTEXT_MESSAGES)
    for msg in history[-MAX_CONTEXT_MESSAGES:]:
        role = msg.get('role', 'user').capitalize()
        content = msg.get('content', '').strip()
        if content:
            # Traducir roles al español para mejor contexto
            role_spanish = 'Usuario' if role.lower() == 'user' else 'Asistente'
            context_parts.append(f"{role_spanish}: {content}")
    
    # Agregar pregunta actual
    context_parts.extend([
        "",
        f"Pregunta actual: {query}",
        "",
        "Instrucciones: Responde la pregunta actual. Usa el contexto anterior solo si es directamente relevante."
    ])
    
    return "\n".join(context_parts)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Orquesta el flujo RAG invocando la API RetrieveAndGenerate de Bedrock Knowledge Bases.
    Esta función actúa como el backend seguro para el chatbot de Duoc UC.
    
    Args:
        event: Evento Lambda con el cuerpo de la solicitud HTTP
        context: Contexto de ejecución de Lambda
        
    Returns:
        Respuesta HTTP con statusCode, headers y body
    """
    # Extraer request ID para tracking
    request_id = extract_request_id(event)
    
    # Manejar solicitud OPTIONS (CORS preflight)
    http_method = event.get('requestContext', {}).get('httpMethod') or event.get('httpMethod') or 'POST'
    if http_method == 'OPTIONS':
        logger.info(f"OPTIONS preflight request: {request_id}")
        # Retornar respuesta preflight con todos los headers CORS necesarios
        return {
            'statusCode': 200,
            'body': '',
            'headers': {
                'Access-Control-Allow-Origin': ALLOWED_ORIGIN or '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Max-Age': '86400'
            }
        }
    
    logger.info(f"Iniciando ejecución para la solicitud: {request_id}")

    # Validar que las variables de entorno críticas estén configuradas
    # ALLOWED_ORIGIN es opcional (puede ser '*' o vacío para desarrollo)
    if not all([KNOWLEDGE_BASE_ID, MODEL_ID]):
        logger.error("Error de configuración: Faltan variables de entorno críticas (KNOWLEDGE_BASE_ID o MODEL_ID).")
        return create_response(500, {'error': 'Error de configuración interna del servidor.'}, request_id)
    
    # Verificar que MODEL_ARN se construyó correctamente
    if not MODEL_ARN:
        logger.error("Error de configuración: No se pudo construir MODEL_ARN a partir de MODEL_ID.")
        return create_response(500, {'error': 'Error de configuración interna del servidor.'}, request_id)
    
    # Advertir si ALLOWED_ORIGIN no está configurado (pero no fallar)
    if not ALLOWED_ORIGIN or ALLOWED_ORIGIN.strip() == '':
        logger.warning("ALLOWED_ORIGIN no está configurado - usando '*' (permitir todos los orígenes)")
    
    # Verificar timeout antes de procesar
    if not check_timeout_remaining(context):
        logger.warning(f"Request rejected due to insufficient remaining time: {request_id}")
        return create_response(503, {'error': 'Request timeout'}, request_id)
    
    # Validar CORS origin antes de procesar la solicitud
    if not validate_cors_origin(event, ALLOWED_ORIGIN):
        logger.warning(
            "CORS validation failed - origin not allowed",
            extra={'allowed_origin': ALLOWED_ORIGIN, 'request_id': request_id}
        )
        return create_response(403, {'error': 'Origin not allowed'}, request_id)

    try:
        body = json.loads(event.get('body', '{}'))
        query = body.get('query', '').strip()
        history = body.get('history', [])

        # Validar que el query no esté vacío
        if not query:
            logger.warning("Solicitud recibida sin una consulta (query).", extra={'request_id': request_id})
            return create_response(400, {'error': 'El campo "query" es requerido.'}, request_id)
        
        # Router de chit-chat: detecta modismos chilenos y frases coloquiales
        # Si es chit-chat, retornar respuesta programada sin llamar a RAG
        chit_chat_response = handle_chit_chat(query)
        if chit_chat_response:
            logger.info(
                f"Respondiendo a chit-chat (sin RAG): '{query}'",
                extra={'request_id': request_id, 'query_type': 'chitchat'}
            )
            # Retornamos la respuesta programada sin llamar a Bedrock
            return create_response(200, {
                'answer': chit_chat_response,
                'sources': [],  # Importante: enviar sources vacías
                'request_id': request_id
            }, request_id)
        
        # Si no fue chit-chat, continuar con el flujo RAG normal
        logger.info(f"Procesando consulta RAG para: '{query}'", extra={'request_id': request_id})
        
        # Detectar prompt injection en query
        # Primero intentar con LLM Guard si está disponible, luego filtro manual
        injection_detected = False
        risk_score = 0.0
        
        if llm_guard_scanner:
            try:
                sanitized_query, is_valid, risk_score = llm_guard_scanner.scan(query)
                if not is_valid:
                    injection_detected = True
                    logger.warning(
                        f"LLM Guard: Prompt injection detected in query (risk: {risk_score:.2f})",
                        extra={'request_id': request_id, 'risk_score': risk_score, 'query_preview': query[:100]}
                    )
                else:
                    query = sanitized_query  # Usar versión sanitizada de LLM Guard
            except Exception as e:
                logger.warning(f"Error usando LLM Guard, usando filtro manual: {str(e)}")
                injection_detected = prompt_filter.detect_injection(query)
        else:
            # Fallback a detección manual
            injection_detected = prompt_filter.detect_injection(query)
        
        if injection_detected:
            return create_response(400, {'error': 'Invalid input detected'}, request_id)
        
        # Detectar prompt injection en history
        if history:
            for msg in history:
                content = str(msg.get('content', ''))
                history_injection = False
                
                if llm_guard_scanner:
                    try:
                        sanitized_content, is_valid, risk_score = llm_guard_scanner.scan(content)
                        if not is_valid:
                            history_injection = True
                            logger.warning(
                                f"LLM Guard: Prompt injection detected in history (risk: {risk_score:.2f})",
                                extra={'request_id': request_id, 'risk_score': risk_score}
                            )
                    except Exception:
                        history_injection = prompt_filter.detect_injection(content)
                else:
                    history_injection = prompt_filter.detect_injection(content)
                
                if history_injection:
                    return create_response(400, {'error': 'Invalid input detected'}, request_id)
        
        # Sanitizar inputs
        query = prompt_filter.sanitize_input(query)
        if history:
            history = [
                {
                    'role': msg.get('role'),
                    'content': prompt_filter.sanitize_input(str(msg.get('content', '')))
                }
                for msg in history
            ]
        
        # Validar longitud del query (después de sanitización)
        if len(query) > MAX_QUERY_LENGTH:
            logger.warning(f"Query excede longitud máxima: {len(query)} caracteres (máximo: {MAX_QUERY_LENGTH})")
            return create_response(
                400, 
                {'error': f'La consulta excede la longitud máxima permitida de {MAX_QUERY_LENGTH} caracteres.'},
                request_id
            )
        
        # Validar formato de history
        if history and not isinstance(history, list):
            logger.warning("Formato de history inválido, usando historial vacío")
            history = []
        
        # Validar estructura de mensajes en history
        if history:
            valid_history = []
            for msg in history:
                if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                    # Validar que role sea 'user' o 'assistant'
                    if msg.get('role') in ['user', 'assistant']:
                        valid_history.append({
                            'role': msg.get('role'),
                            'content': str(msg.get('content', '')).strip()
                        })
                else:
                    logger.warning(f"Mensaje inválido en history: {msg}")
            history = valid_history
        
        # Limitar history a MAX_CONTEXT_MESSAGES
        if len(history) > MAX_CONTEXT_MESSAGES:
            logger.info(f"History truncado de {len(history)} a {MAX_CONTEXT_MESSAGES} mensajes")
            history = history[-MAX_CONTEXT_MESSAGES:]
        
        # Optimizar query (Phase 2: Query Optimization)
        optimized_query = query
        if QUERY_OPTIMIZATION_ENABLED:
            optimized_query = query_optimizer.optimize_query(query, history)
            if optimized_query != query:
                logger.info(
                    f"Query optimizado: '{query[:100]}...' -> '{optimized_query[:100]}...'",
                    extra={'original_query': query, 'optimized_query': optimized_query, 'request_id': request_id}
                )
        
        # Construir query contextual usando el query optimizado
        contextual_query = build_context_prompt(optimized_query, history)
        
        query_preview = optimized_query[:100] + '...' if len(optimized_query) > 100 else optimized_query
        logger.info(
            f"Procesando consulta (longitud: {len(optimized_query)}, history: {len(history)} mensajes): '{query_preview}'",
            extra={
                'query_optimization_enabled': QUERY_OPTIMIZATION_ENABLED,
                'query_expansion_enabled': QUERY_EXPANSION_ENABLED,
                'hybrid_search_enabled': HYBRID_SEARCH_ENABLED,
                'query_decomposition_enabled': QUERY_DECOMPOSITION_ENABLED,
                'request_id': request_id
            }
        )

        # --- Lógica RAG con Query Optimization (Phase 2) ---
        # Query optimizado se envía a Bedrock para mejor recuperación.
        # Usar contextual_query que incluye el historial de conversación y el query optimizado
        
        # Prompt template para Orchestration (búsqueda y recuperación)
        # Reformula la pregunta del usuario para mejorar la búsqueda en la base de conocimientos
        # IMPORTANTE: Debe incluir $conversation_history$ y $output_format_instructions$ (obligatorios)
        # Bedrock reemplazará estos placeholders automáticamente
        orchestration_prompt = """Tu tarea es reformular la pregunta del usuario para mejorar la búsqueda en la base de conocimientos de Duoc UC.
La pregunta reformulada debe ser clara, específica y optimizada para encontrar información relevante sobre admisión, matrícula, becas, carreras, servicios estudiantiles, gratuidad, aranceles y otros temas relacionados con Duoc UC.
Mantén el sentido original de la pregunta pero hazla más específica para la búsqueda.

HISTORIAL DE CONVERSACIÓN:
$conversation_history$

PREGUNTA DEL USUARIO:
$query$

$output_format_instructions$

PREGUNTA REFORMULADA PARA BÚSQUEDA:"""

        # Prompt template para Generation (generación de respuesta)
        # Genera la respuesta final basada en el contexto recuperado
        # IMPORTANTE: Debe incluir el placeholder $search_results$ (obligatorio) y $query$ (opcional)
        # Bedrock reemplazará $search_results$ con los resultados recuperados de la Knowledge Base
        # VERSIÓN FINAL: PROACTIVA Y EVITA SEPARADORES INICIALES
        generation_prompt = """Eres un asistente virtual de la Mesa de Servicio Estudiantil de Duoc UC.

Tu función es ayudar a los estudiantes respondiendo sus consultas de manera clara, precisa y amigable.

---

INSTRUCCIONES DE CONTENIDO:

- Basa tu respuesta ESTRICTAMENTE en la información de los "RESULTADOS DE BÚSQUEDA".

- **(NUEVA REGLA) NO AÑADIR SEPARADORES:** Tu respuesta debe empezar directamente con la oración. NO incluyas separadores de formato al inicio (como `: ---`, `---`, `***`) ni dos puntos (`:`) antes de la respuesta.

- **SÉ PROACTIVO Y ÚTIL (MUY IMPORTANTE):** Si la respuesta es un resumen y los resultados de búsqueda contienen un enlace (URL) a más detalles, **DEBES incluir ese enlace** en tu respuesta.

- **IGNORAR LISTAS DE PALABRAS CLAVE:** Si los "RESULTADOS DE BÚSQUEDA" son solo una lista de palabras clave (ej. 'CAE', 'Aranceles'), ignóralos y responde que no tienes la información.

- **MÁXIMA PRECISIÓN (NO ASOCIAR):** No asocies información general (ej. "teléfono Mesa de Ayuda") con preguntas específicas (ej. "teléfono Sede Temuco").

- **NO INVENTAR:** Si no tienes un dato, no intentes adivinarlo.

- IGNORA Y OMITE CUALQUIER ARTEFACTO DE FORMATO (ej: 'Step 1', 'SEQ_STARTX', '[1]').

- NO incluyas títulos o nombres de fuente (como 'Gratuidad y Becas'). Tu respuesta debe ir directamente al grano.

- Usa SOLO español.

---

INSTRUCCIONES DE FORMATO (MUY IMPORTANTE):

- Tu respuesta final debe ser profesional, limpia y fácil de leer.

- **Usa Markdown simple** para estructurar tu respuesta.

- **Enlaces (Links):** Formatea los enlaces usando Markdown: `[Texto del enlace](url)`.

- **Listas:** Si la respuesta es una lista, formátala como una lista de Markdown (usando `- `). Asegúrate de que haya un salto de línea antes del primer elemento.

- **Ejemplo de formato de lista:**

El asistente debe responder:

Aquí tienes los requisitos:

- Requisito A.

- Requisito B.

- Requisito C.

---

RESULTADOS DE BÚSQUEDA:

$search_results$

PREGUNTA DEL USUARIO:

$query$

RESPUESTA LIMPIA Y FORMATEADA (en Markdown):"""

        response = bedrock_agent_runtime.retrieve_and_generate(
            input={'text': contextual_query},
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': KNOWLEDGE_BASE_ID,
                    'modelArn': MODEL_ARN,
                    'generationConfiguration': {
                        'inferenceConfig': {
                            'textInferenceConfig': {
                                'temperature': TEMPERATURE,
                                'maxTokens': MAX_TOKENS,
                            }
                        },
                        'promptTemplate': {
                            'textPromptTemplate': generation_prompt
                        }
                    },
                    'orchestrationConfiguration': {
                        'promptTemplate': {
                            'textPromptTemplate': orchestration_prompt
                        }
                    }
                }
            }
        )

        # Validar estructura de respuesta de Bedrock
        if 'output' not in response or 'text' not in response['output']:
            logger.error("Respuesta inválida de Bedrock: falta 'output' o 'text'", extra={'request_id': request_id})
            return create_response(500, {'error': 'Respuesta inválida del servicio de IA.'}, request_id)

        # Extraer la respuesta y las fuentes (citas)
        answer = response['output']['text']
        citations = response.get('citations', [])

        # Validar output antes de retornar
        answer = output_validator.filter_response(answer)

        # --- INICIO DE FILTROS REGEX PARA LIMPIEZA DE ARTEFACTOS ---
        
        # 1. Filtro RegEx para artefactos conocidos (Step 1, Step 2, etc.)
        answer = re.sub(r'Step\s*\d+', '', answer, flags=re.IGNORECASE)
        answer = re.sub(r'SEQ_(STARTX|ENDX|ANYWHERE):[\d,]+', '', answer, flags=re.IGNORECASE)
        
        # 2. NUEVO FILTRO: Eliminar marcadores de citación tipo [1], [2], etc.
        #    Esto busca un espacio (opcional) seguido de un [número]
        #    y lo reemplaza con un solo espacio para no pegar palabras.
        answer = re.sub(r'\s*\[\d+\]', ' ', answer)
        
        # 3. Limpieza de espacios y saltos de línea múltiples
        answer = re.sub(r'\s{2,}', ' ', answer)  # Reemplaza espacios múltiples por uno
        answer = re.sub(r'^\s*-\s*', '- ', answer, flags=re.MULTILINE)  # Arregla viñetas
        answer = answer.strip()
        # --- FIN DE FILTROS REGEX ---

        # Formatear y validar las fuentes (filtrado por score y cantidad)
        sources = format_sources(citations, min_score=MIN_CITATION_SCORE, max_count=MAX_CITATIONS)
        
        # Validar que haya al menos una cita válida si la respuesta requiere fuentes
        if not sources and citations:
            logger.warning(
                "No valid citations after filtering - all citations below minimum score",
                extra={
                    'request_id': request_id,
                    'min_score': MIN_CITATION_SCORE,
                    'total_citations': len(citations)
                }
            )
            # Opcional: Retornar respuesta sin fuentes o con mensaje de advertencia
            # Por ahora, retornamos sin fuentes pero logueamos la advertencia

        logger.info(
            "Respuesta y fuentes generadas exitosamente",
            extra={
                'answer_length': len(answer),
                'sources_count': len(sources),
                'query_length': len(query),
                'history_length': len(history),
                'request_id': request_id
            }
        )
        return create_response(200, {'answer': answer, 'sources': sources, 'request_id': request_id}, request_id)

    except json.JSONDecodeError as e:
        logger.error(f"Error al decodificar JSON en el cuerpo de la solicitud: {str(e)}", extra={'request_id': request_id})
        return create_response(400, {'error': 'Formato JSON inválido en la solicitud.'}, request_id)
    
    except ValueError as e:
        logger.error(f"Error de validación: {str(e)}", extra={'request_id': request_id})
        return create_response(400, {'error': str(e)}, request_id)
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(
            f"Error de Bedrock API [{error_code}]: {error_message}",
            extra={
                'error_code': error_code,
                'error_message': error_message,
                'knowledge_base_id': KNOWLEDGE_BASE_ID,
                'request_id': request_id
            }
        )
        
        if error_code == 'ThrottlingException':
            return create_response(429, {'error': 'El servicio está temporalmente no disponible. Por favor, intente más tarde.'}, request_id)
        elif error_code == 'ValidationException':
            return create_response(400, {'error': 'Parámetros de solicitud inválidos.'}, request_id)
        elif error_code == 'AccessDeniedException':
            return create_response(403, {'error': 'Acceso denegado al servicio.'}, request_id)
        else:
            return create_response(500, {'error': 'Error interno al procesar la solicitud.'}, request_id)
    
    except Exception as e:
        logger.error(f"Error inesperado en el handler: {str(e)}", exc_info=True, extra={'request_id': request_id})
        return create_response(500, {'error': 'Ocurrió un error interno al procesar tu solicitud.'}, request_id)


def extract_url_from_text(text: str) -> Optional[str]:
    """
    Extrae la primera URL encontrada en un texto.
    
    Args:
        text: Texto donde buscar URLs
        
    Returns:
        Primera URL encontrada o None si no hay URLs
    """
    if not text:
        return None
    
    # Patrón regex para detectar URLs HTTP/HTTPS
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,;!?]'
    matches = re.findall(url_pattern, text, re.IGNORECASE)
    
    if matches:
        # Retornar la primera URL encontrada
        return matches[0]
    
    return None


def extract_url_from_metadata(metadata: Dict[str, Any]) -> Optional[str]:
    """
    Extrae URL desde los metadatos de la referencia retornada por Bedrock Knowledge Bases.
    Bedrock almacena los campos del JSONL como metadatos cuando indexa documentos.
    Busca recursivamente en toda la estructura de metadatos.
    
    Args:
        metadata: Diccionario de metadatos de la referencia desde OpenSearch Serverless
        
    Returns:
        URL encontrada en metadatos o None
    """
    if not metadata:
        return None
    
    # Campos posibles donde puede estar la URL en los metadatos del JSONL
    url_fields = ['url', 'URL', 'link', 'href', 'source_url', 'document_url', 'reference_url']
    
    # Buscar directamente en el nivel superior de metadata
    for field in url_fields:
        if field in metadata:
            url_value = metadata[field]
            if url_value and isinstance(url_value, str) and url_value.strip():
                url_cleaned = url_value.strip()
                # Validar que sea una URL válida
                if url_cleaned.startswith(('http://', 'https://')):
                    logger.debug(f"URL encontrada en metadata.{field}: {url_cleaned[:100]}")
                    return url_cleaned
    
    # Buscar recursivamente en estructuras anidadas
    def search_recursive(obj, depth=0):
        if depth > 3:  # Limitar profundidad para evitar recursión infinita
            return None
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                # Si la clave sugiere que es una URL
                if any(field in key.lower() for field in ['url', 'link', 'href']):
                    if isinstance(value, str) and value.strip().startswith(('http://', 'https://')):
                        logger.debug(f"URL encontrada recursivamente en {key}: {value[:100]}")
                        return value.strip()
                
                # Buscar recursivamente en valores anidados
                result = search_recursive(value, depth + 1)
                if result:
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = search_recursive(item, depth + 1)
                if result:
                    return result
        
        return None
    
    # Buscar recursivamente en metadata
    url_found = search_recursive(metadata)
    if url_found:
        return url_found
    
    # Como último recurso, convertir todo el metadata a string y buscar URLs
    try:
        metadata_str = json.dumps(metadata)
        url_found = extract_url_from_text(metadata_str)
        if url_found:
            logger.debug(f"URL encontrada en serialización JSON de metadata: {url_found[:100]}")
            return url_found
    except Exception as e:
        logger.debug(f"Error serializando metadata para búsqueda de URL: {str(e)}")
    
    return None


def format_sources(citations: List[Dict[str, Any]], min_score: float = None, max_count: int = None) -> List[Dict[str, Any]]:
    """
    Formatea las citas de Bedrock en un formato simplificado para el frontend.
    Valida y filtra citas según score mínimo y cantidad máxima.
    Prioriza extraer URLs desde metadatos del JSONL o del contenido del texto.
    
    Args:
        citations: Lista de objetos de cita de Bedrock
        min_score: Score mínimo requerido para incluir una cita (default: MIN_CITATION_SCORE)
        max_count: Cantidad máxima de citas a retornar (default: MAX_CITATIONS)
        
    Returns:
        Lista de diccionarios con información de fuentes formateadas y validadas
    """
    if min_score is None:
        min_score = MIN_CITATION_SCORE
    if max_count is None:
        max_count = MAX_CITATIONS
    
    sources = []
    for citation in citations:
        retrieved_refs = citation.get('retrievedReferences', [])
        for ref in retrieved_refs:
            metadata = ref.get('metadata', {})
            score = metadata.get('score', 0.0)
            
            # Filtrar por score mínimo
            if score < min_score:
                logger.debug(
                    f"Citation filtered due to low score: {score:.3f} < {min_score:.3f}",
                    extra={'score': score, 'min_score': min_score}
                )
                continue
            
            excerpt = ref.get('content', {}).get('text', '')
            
            # Intentar extraer URL desde metadatos (prioritario)
            # Bedrock Knowledge Bases almacena campos del JSONL como metadatos
            url = extract_url_from_metadata(metadata)
            url_source = 'metadata' if url else None
            
            # Si no se encuentra en metadatos, buscar en toda la estructura de la referencia
            # (Bedrock puede almacenar metadatos en diferentes lugares)
            if not url:
                # Buscar en location (puede contener metadatos adicionales)
                location = ref.get('location', {})
                if location:
                    url = extract_url_from_metadata(location)
                    url_source = 'location_metadata' if url else None
            
            # Si aún no se encuentra, buscar en el excerpt (contenido del texto)
            if not url:
                url = extract_url_from_text(excerpt)
                url_source = 'content' if url else None
            
            # Si aún no hay URL, usar el fallback de S3 location
            if not url:
                s3_uri = ref.get('location', {}).get('s3Location', {}).get('uri', '')
                if s3_uri:
                    url = s3_uri
                    url_source = 's3_location'
                    logger.debug(
                        "URL no encontrada en metadatos ni contenido, usando S3 location",
                        extra={'s3_location': url[:100]}
                    )
            
            if url and url_source != 's3_location':
                logger.debug(
                    "URL extraída exitosamente desde metadatos de OpenSearch Serverless",
                    extra={'url_source': url_source, 'url': url[:100]}
                )
            
            source_info = {
                'url': url,
                'excerpt': excerpt,
                'score': score
            }
            sources.append(source_info)
    
    # Ordenar por score descendente (mayor relevancia primero)
    sources.sort(key=lambda x: x.get('score', 0.0), reverse=True)
    
    # Limitar cantidad de citas
    if len(sources) > max_count:
        logger.info(
            f"Citations limited from {len(sources)} to {max_count} (top scores)",
            extra={'original_count': len(sources), 'max_count': max_count}
        )
        sources = sources[:max_count]
    
    # Validar que haya al menos una cita válida
    if not sources:
        logger.warning(
            f"No valid citations found (all below score threshold: {min_score:.3f})",
            extra={'min_score': min_score, 'total_citations': len(citations)}
        )
    
    return sources


def create_response(status_code: int, body: Dict[str, Any], request_id: str = None) -> Dict[str, Any]:
    """
    Función de utilidad para crear respuestas HTTP consistentes con headers CORS apropiados.
    
    Args:
        status_code: Código de estado HTTP
        body: Cuerpo de la respuesta como diccionario
        request_id: Request ID para tracking (opcional)
        
    Returns:
        Diccionario con statusCode, headers y body formateado
    """
    # Agregar request_id al body si está disponible y no está ya presente
    if request_id and 'request_id' not in body:
        body['request_id'] = request_id
    
    # Determinar el origen permitido (usar '*' solo si no está configurado, para desarrollo)
    allowed_origin = ALLOWED_ORIGIN or '*'
    
    return {
        'statusCode': status_code,
        'body': json.dumps(body, ensure_ascii=False),  # Soporte para caracteres en español
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': allowed_origin,
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
            'Access-Control-Max-Age': '86400'
        }
    }