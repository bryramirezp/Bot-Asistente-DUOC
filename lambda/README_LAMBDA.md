# RetrieveAndGenerate Lambda Function - Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Configuration](#configuration)
4. [Security Audit](#security-audit)
5. [Improvement Roadmap](#improvement-roadmap)
6. [Implementation Guide](#implementation-guide)
7. [Testing & Monitoring](#testing--monitoring)
8. [Deployment Checklist](#deployment-checklist)

---

## Overview

### Purpose
AWS Lambda function that orchestrates a RAG (Retrieval-Augmented Generation) workflow using Amazon Bedrock Knowledge Bases. Acts as a secure backend for the Duoc UC chatbot, providing AI-powered responses with source citations.

### Security Status
✅ **Phase 1: Security Hardening - COMPLETE**
- ✅ Prompt injection detection implemented
- ✅ CORS origin validation implemented
- ✅ Input sanitization implemented
- ✅ Output validation implemented
- ✅ Timeout handling implemented
- ✅ Request ID tracking implemented

### Current Status
- ✅ Basic RAG implementation functional
- ✅ Single-query processing with citations
- ✅ Conversational context implemented (Phase 0 complete - using sessionStorage)
- ✅ Input validation (query length, history format)
- ✅ Type hints and structured logging
- ✅ Specific exception handling (boto3 errors)
- ✅ Response structure validation
- ✅ X-Ray tracing implemented
- ✅ Prompt injection detection (Phase 1 complete)
- ✅ CORS origin validation (Phase 1 complete)
- ✅ Input sanitization (Phase 1 complete)
- ✅ Output validation (Phase 1 complete)
- ✅ Timeout handling (Phase 1 complete)
- ✅ Request ID tracking (Phase 1 complete)
- ✅ Citation validation (Phase 3 partial - score filtering implemented)
- ✅ LLM Guard integration (Phase 1 enhanced - optional)
- ✅ Query optimization (Phase 2 complete - expansion, hybrid search, decomposition)
- 🔄 Advanced response quality validation (Phase 3 partial - factuality checking pending)

---

## Architecture

### Current Flow
```
User Query → API Gateway → Lambda → Bedrock Knowledge Base → OpenSearch
                                                                    ↓
User Response ← Lambda ← LLM Generation ← Retrieved Context ← Search Results
```

**Note:** Conversational context is managed by the frontend using sessionStorage. Each request includes the conversation history.

### Proposed Flow (With Context)
```
Frontend (maintains history in sessionStorage/memory)
    ↓
User Query + Conversation History → API Gateway → Lambda
    ↓
Context-Enhanced Query → Bedrock Knowledge Base → OpenSearch
    ↓
Retrieved Context + Conversation History → LLM Generation
    ↓
Response + Citations → Lambda → Frontend (updates sessionStorage history)
```

### Components

| Component | Current Implementation | Purpose |
|-----------|----------------------|---------|
| **Input** | `query` (string) + `history` (array) | User question with conversation history |
| **Processing** | Bedrock `retrieve_and_generate()` | RAG pipeline with contextual prompts |
| **Output** | `answer` (string) + `sources` (array) | AI response with citations |
| **Context** | ✅ Frontend-managed (sessionStorage) | Conversational memory (last 10 messages) |
| **Storage** | ✅ Frontend (sessionStorage) | History management (no database needed) |
| **Security** | ✅ Complete (Phase 1 complete) | Input validation, prompt injection detection, CORS, timeout handling |

### Response Format
```json
{
  "answer": "Generated answer text with context",
  "sources": [
    {
      "document": "s3://bucket/path/to/doc.pdf",
      "excerpt": "Relevant text excerpt from document",
      "score": 0.95
    }
  ]
}
```

---

## Configuration

### Environment Variables

#### Required
| Variable | Example | Description |
|----------|---------|-------------|
| `KNOWLEDGE_BASE_ID` | `abc123xyz` | Bedrock Knowledge Base ID |
| `MODEL_ARN` | `cohere.command-r-v1:0` | Bedrock LLM model ARN |
| `ALLOWED_ORIGIN` | `https://duoc.cl` | CORS allowed origin |

#### Optional
| Variable | Default | Range | Description |
|----------|---------|-------|-------------|
| `AWS_REGION` | `us-east-1` | - | AWS region |
| `TEMPERATURE` | `0.2` | 0.0-1.0 | LLM creativity (lower = more deterministic) |
| `MAX_TOKENS` | `1024` | 1-4096 | Maximum response length |
| `MAX_QUERY_LENGTH` | `5000` | - | Query character limit |
| `MAX_CONTEXT_MESSAGES` | `10` | - | Conversation history limit (managed in frontend sessionStorage) |
| `MIN_TIMEOUT_SECONDS` | `5.0` | - | Minimum seconds remaining before Lambda timeout |
| `MIN_CITATION_SCORE` | `0.7` | 0.0-1.0 | Minimum relevance score for citations (Phase 3) |
| `MAX_CITATIONS` | `5` | 1-20 | Maximum number of citations to return (Phase 3) |
| `LLM_GUARD_ENABLED` | `false` | true/false | Enable LLM Guard for enhanced security |
| `LLM_GUARD_THRESHOLD` | `0.5` | 0.0-1.0 | Risk threshold for LLM Guard detection |
| `QUERY_OPTIMIZATION_ENABLED` | `true` | true/false | Enable query optimization (Phase 2) |
| `QUERY_EXPANSION_ENABLED` | `true` | true/false | Enable query expansion with synonyms |
| `HYBRID_SEARCH_ENABLED` | `true` | true/false | Enable hybrid search (semantic + keyword) |
| `QUERY_DECOMPOSITION_ENABLED` | `true` | true/false | Enable complex query decomposition |
| `MAX_QUERY_EXPANSIONS` | `3` | 1-10 | Maximum number of synonyms to add per query |

### IAM Permissions Required
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:RetrieveAndGenerate",
        "bedrock:InvokeModel"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": "xray:PutTraceSegments",
      "Resource": "*"
    }
  ]
}
```

---

## Security Audit

### 🔴 Critical Issues

| # | Issue | Impact | Priority | Status |
|---|-------|--------|----------|--------|
| 1 | **No input validation** | Resource exhaustion, injection attacks | Critical | ✅ Implementado |
| 2 | **Weak CORS validation** | Security bypass potential | Critical | ✅ Implementado |
| 3 | **No rate limiting** | DoS vulnerability | Critical | 📋 Planificado |
| 4 | **Generic error handling** | Information leakage | High | ✅ Implementado |
| 5 | **No authentication** | Public access (by design for duoc.cl) | N/A* | ✅ Por diseño |

*Note: Public access is intentional for student chatbot. Mitigate with API Gateway throttling and WAF rules.*

### 🟡 Medium Issues

| # | Issue | Impact | Priority | Status |
|---|-------|--------|----------|--------|
| 6 | **No request validation** | Malformed requests cause errors | Medium | ✅ Implementado |
| 7 | **Hardcoded config values** | Difficult to tune without redeployment | Medium | ✅ Implementado |
| 8 | **No timeout handling** | Hanging requests | Medium | ✅ Implementado |

### 🟢 Low Priority Issues

| # | Issue | Impact | Priority | Status |
|---|-------|--------|----------|--------|
| 9 | **Missing type hints** | Reduced maintainability | Low | ✅ Implementado |
| 10 | **No unit tests** | Difficult to validate changes | Low | 🔄 Pendiente |
| 11 | **No structured logging** | Difficult to debug | Low | ✅ Implementado |

---

## Prompt Injection Security

### Overview

**Prompt Injection** es una vulnerabilidad crítica en aplicaciones LLM donde un atacante manipula el input del usuario para inyectar instrucciones maliciosas que el modelo ejecuta, potencialmente:
- Revelando instrucciones del sistema
- Bypasseando restricciones de seguridad
- Accediendo a información confidencial
- Modificando el comportamiento del sistema

### Vulnerabilidades de Prompt Injection Identificadas

| Vulnerabilidad | Estado | Mitigación |
|----------------|--------|------------|
| **Input validation** | ✅ Implementado | Validación de longitud, sanitización y detección de injection implementadas |
| **Detección de patrones peligrosos** | ✅ Implementado | Filtro de prompt injection implementado |
| **Sanitización de inputs** | ✅ Implementado | Normalización y filtrado de caracteres peligrosos implementado |
| **Validación de CORS origin** | ✅ Implementado | Validación estricta de origen implementada |
| **Timeout handling** | ✅ Implementado | Verificación de tiempo restante implementada |
| **Output validation** | ✅ Implementado | Validación de patrones sospechosos en respuestas implementada |
| **Request ID tracking** | ✅ Implementado | Tracking de solicitudes para correlación implementado |

### Medidas de Protección Implementadas

- ✅ **Validación de longitud** de queries (MAX_QUERY_LENGTH: 5000 caracteres)
- ✅ **Validación de formato** de historial de conversación
- ✅ **Validación de estructura** de respuestas de Bedrock
- ✅ **Manejo específico de excepciones** con códigos de error apropiados
- ✅ **Logging estructurado** con contexto adicional
- ✅ **Type hints** en todas las funciones
- ✅ **Detección de prompt injection** con filtro de patrones peligrosos
- ✅ **Sanitización de inputs** con normalización y filtrado
- ✅ **Validación de outputs** para detectar fugas de información
- ✅ **Timeout handling** con verificación de tiempo restante
- ✅ **Request ID tracking** en todas las respuestas y logs

### Medidas de Protección Planificadas

- ✅ **Detección de patrones peligrosos** - `PromptInjectionFilter` implementado
- ✅ **Sanitización de inputs** - Normalización y filtrado implementado
- ✅ **Validación de CORS origin** - Validación estricta implementada
- ✅ **Timeout handling** - Verificación de tiempo restante implementada
- ✅ **Request ID tracking** - Request ID incluido en respuestas y logs
- ✅ **Validación de outputs** - Detección de fugas implementada

### Patrones Peligrosos a Detectar

Los siguientes patrones deben ser detectados y bloqueados:

```python
DANGEROUS_PATTERNS = [
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
```

### Mejores Prácticas de Seguridad

#### 1. Input Validation y Sanitización

- **Detección de patrones peligrosos** usando expresiones regulares
- **Detección fuzzy** para typoglycemia (palabras con letras mezcladas)
- **Normalización de espacios** en blanco y caracteres invisibles
- **Remoción de repetición** de caracteres (aaaa -> a)
- **Filtrado de caracteres invisibles** Unicode

#### 2. Estructuración de Prompts

- **Separación clara** entre instrucciones del sistema y datos del usuario
- **Instrucciones explícitas** para tratar input del usuario como DATA, no COMMANDOS
- **Reglas de seguridad** integradas en el system prompt
- **Rechazo automático** de solicitudes que intentan ignorar reglas

#### 3. Validación de Output

- **Detección de fugas** de system prompt en respuestas
- **Detección de exposición** de API keys o información sensible
- **Validación de patrones sospechosos** en respuestas
- **Límite de longitud** de respuestas

#### 4. Validación de CORS

- **Validación estricta** del header `Origin` del request
- **Comparación exacta** con `ALLOWED_ORIGIN` configurado
- **Rechazo de requests** con origen no autorizado
- **No usar '*' en producción** (solo para desarrollo)

#### 5. Timeout Handling

- **Verificación de tiempo restante** antes de procesar requests
- **Configuración de timeout** en cliente boto3
- **Manejo de timeouts** de Bedrock API
- **Respuesta apropiada** cuando se detecta timeout inminente

#### 6. Request ID Tracking

- **Extracción de request ID** del evento Lambda
- **Inclusión en logs** para correlación
- **Inclusión en respuestas** para debugging del cliente
- **Tracking de intentos** de injection por request ID

### Implementación Recomendada

Ver documentación detallada en: [Prompt Injection Security Guide](../docs/prompt-injection-security.md)

La documentación incluye:
- Código completo de `PromptInjectionFilter`
- Código completo de `OutputValidator`
- Funciones de validación de CORS
- Funciones de timeout handling
- Integración con LLM Guard (librería especializada)
- Checklist completo de seguridad
- Referencias a OWASP y mejores prácticas

### Integración con LLM Guard (Opcional)

✅ **IMPLEMENTADO** - Para una protección más robusta, se ha integrado [LLM Guard](https://github.com/protectai/llm-guard):

**Configuración:**
- Agregar `llm-guard>=2.0.0` a `requirements.txt`
- Configurar variables de entorno:
  - `LLM_GUARD_ENABLED=true` (default: false)
  - `LLM_GUARD_THRESHOLD=0.5` (default: 0.5)

**Funcionamiento:**
- LLM Guard se usa como primera capa de detección si está habilitado
- Si LLM Guard no está disponible o falla, se usa el filtro manual como fallback
- Proporciona risk_score para mejor logging y auditoría
- Sanitiza automáticamente el input cuando es válido

**Código implementado:**
```python
from llm_guard.input_scanners import PromptInjection
from llm_guard.input_scanners.prompt_injection import MatchType

# Inicialización automática si LLM_GUARD_ENABLED=true
llm_guard_scanner = PromptInjection(
    threshold=LLM_GUARD_THRESHOLD,
    match_type=MatchType.FULL
)

# Uso en detección de prompt injection
sanitized_query, is_valid, risk_score = llm_guard_scanner.scan(query)
```

### Referencias

- [Prompt Injection Security Guide](../docs/prompt-injection-security.md) - Documentación completa
- [LLM Guard Documentation](https://github.com/protectai/llm-guard) - Librería especializada
- [OWASP LLM Prompt Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html) - Mejores prácticas OWASP
- [Aporia Guardrails](https://gr-docs.aporia.com/) - Plataforma de guardrails para LLM

---

## Improvement Roadmap

### 🚨 Phase 0: Critical - Conversational Context (1-2 days)

**Problem:** Chatbot cannot remember previous messages, making follow-up questions impossible.

**Example:**
- ❌ Current: "When do classes start?" → "December 20th" → "And how much does it cost?" → ⚠️ No context!
- ✅ With context: "When do classes start?" → "December 20th" → "And how much does it cost?" → "Classes starting December 20th cost..."

**Solution:** Frontend-managed conversation history (no database needed!)

#### Implementation Strategy

```
Frontend (sessionStorage/memory) → Lambda → Bedrock (with context)
```

**Key Benefits:**
- ✅ No DynamoDB costs
- ✅ No additional IAM permissions
- ✅ Lower latency (no database queries)
- ✅ History persists during session (better UX)
- ✅ Optional "Clear History" button for user control

**Technical Approach:**
1. Frontend maintains last 10 messages (5 user + 5 assistant) in `sessionStorage`
2. Each request includes full conversation history
3. Lambda builds contextual query using history
4. LLM intelligently uses context only when relevant

**Behavior with Different Question Types:**

| Scenario | Example | LLM Behavior |
|----------|---------|--------------|
| **Follow-up question** | "When do classes start?" → "December 20th" → "And how much?" | Uses context: "Classes starting December 20th cost $500" |
| **Independent question** | "When do classes start?" → "December 20th" → "What careers at San Joaquín?" | Ignores context: "At San Joaquín: Medicine, Engineering" |

**Implementation Time:** 1-2 days

---

### 🔥 Phase 1: Security Hardening (2-3 days)

**Priorities:**
1. ✅ Input validation (query length) - **IMPLEMENTADO**
2. ✅ Specific exception handling (boto3 errors) - **IMPLEMENTADO**
3. ✅ CORS origin validation - **IMPLEMENTADO**
4. ✅ Response structure validation - **IMPLEMENTADO**
5. ✅ Request ID tracking - **IMPLEMENTADO**
6. ✅ Prompt injection detection - **IMPLEMENTADO**
7. ✅ Input sanitization - **IMPLEMENTADO**
8. ✅ Output validation - **IMPLEMENTADO**
9. ✅ Timeout handling - **IMPLEMENTADO**

**Estado actual:**
- ✅ Validación de longitud de query implementada
- ✅ Manejo específico de excepciones de boto3 implementado
- ✅ Validación de estructura de respuesta implementada
- ✅ Validación de CORS origin implementada
- ✅ Detección de prompt injection implementada
- ✅ Sanitización de inputs implementada
- ✅ Validación de outputs implementada
- ✅ Timeout handling implementado
- ✅ Request ID tracking implementado

**Referencias:** Ver sección [Prompt Injection Security](#prompt-injection-security) arriba para detalles completos y código de implementación.

---

### ⚡ Phase 2: Query Optimization (1 week)

**Goals:**
- ✅ Query expansion with synonyms - **IMPLEMENTADO**
- ✅ Hybrid search (semantic + keyword) - **IMPLEMENTADO**
- ✅ Complex query decomposition - **IMPLEMENTADO**
- ✅ Context-aware query enhancement - **IMPLEMENTADO**

**Estado actual:**
- ✅ Expansión de queries con sinónimos implementada
- ✅ Búsqueda híbrida (semántica + keywords) implementada
- ✅ Descomposición de queries complejas implementada
- ✅ Mejora de queries con contexto de conversación implementada
- ✅ Variables de entorno configurables para habilitar/deshabilitar optimizaciones

---

### 🎯 Phase 3: Response Quality (1 week)

**Goals:**
- ✅ Citation validation (verify sources support answer) - **IMPLEMENTADO**
- ✅ Citation relevance scoring - **IMPLEMENTADO**
- 🔄 Factuality checking (hallucination detection) - **PENDIENTE**
- 🔄 Contradiction detection - **PENDIENTE**

**Estado actual:**
- ✅ Filtrado de citas por score mínimo (MIN_CITATION_SCORE: 0.7)
- ✅ Ordenamiento de citas por relevancia (score descendente)
- ✅ Límite de cantidad de citas (MAX_CITATIONS: 5)
- ✅ Validación de que haya citas válidas
- ✅ Logging de citas filtradas para auditoría

---

### 🚀 Phase 4: Advanced Retrieval (1-2 weeks)

**Goals:**
- Cross-encoder re-ranking
- Metadata filtering
- Diversity sampling
- Context window optimization

---

## Implementation Guide

### Phase 0: Conversational Context

#### Step 1: Frontend - ChatHistory Class

```javascript
class ChatHistory {
    constructor() {
        this.messages = [];
        this.MAX_MESSAGES = 10;
        this.STORAGE_KEY = 'duocChatHistory';
        this.loadFromStorage();
    }
    
    addMessage(role, content) {
        this.messages.push({ role, content });
        if (this.messages.length > this.MAX_MESSAGES) {
            this.messages = this.messages.slice(-this.MAX_MESSAGES);
        }
        this.saveToStorage();
    }
    
    getHistory() {
        return this.messages;
    }
    
    clear() {
        this.messages = [];
        sessionStorage.removeItem(this.STORAGE_KEY);
    }
    
    saveToStorage() {
        try {
            sessionStorage.setItem(
                this.STORAGE_KEY, 
                JSON.stringify(this.messages)
            );
        } catch (e) {
            console.warn('Could not save history:', e);
        }
    }
    
    loadFromStorage() {
        try {
            const stored = sessionStorage.getItem(this.STORAGE_KEY);
            if (stored) {
                this.messages = JSON.parse(stored);
            }
        } catch (e) {
            console.warn('Could not load history:', e);
            this.messages = [];
        }
    }
}
```

#### Step 2: Frontend - Integration

**Modify `chatbot.js`:**

```javascript
// 1. Add property to chatbot object
const chatbot = {
    history: null,  // Add this line
    
    // 2. Initialize in init()
    init() {
        this.history = new ChatHistory();
        // ... rest of init code
    },
    
    // 3. Modify sendMessage()
    async sendMessage(message) {
        // BEFORE adding to UI
        this.history.addMessage('user', message);
        
        // Add to UI
        this.addMessage(message, 'user');
        
        // Modify fetch request
        const response = await fetch(API_ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                query: message,
                history: this.history.getHistory()  // Add history
            })
        });
        
        const data = await response.json();
        
        // AFTER receiving response
        this.history.addMessage('assistant', data.answer);
        
        // Add to UI
        this.addMessage(data.answer, 'bot');
    }
};
```

#### Step 3: Lambda - Context Builder

```python
def build_context_prompt(query: str, history: List[Dict]) -> str:
    """
    Builds contextual query from conversation history.
    
    Instructs LLM to use context only when relevant.
    For independent questions, LLM ignores previous context.
    """
    if not history:
        return query
    
    context_parts = [
        "Previous conversation:",
        "IMPORTANT: Use this context ONLY if relevant to the current question.",
        "If the current question is about a different topic, ignore previous context."
    ]
    
    # Add conversation history
    for msg in history[-10:]:  # Last 10 messages only
        role = msg.get('role', 'user').capitalize()
        content = msg.get('content', '').strip()
        if content:
            context_parts.append(f"{role}: {content}")
    
    # Add current question
    context_parts.extend([
        f"\nCurrent question: {query}",
        "\nInstructions: Answer the current question. Use previous context only if directly relevant."
    ])
    
    return "\n".join(context_parts)
```

#### Step 4: Lambda - Handler Update

```python
import json
import os
import boto3
from typing import Dict, List, Any

# Environment variables
KNOWLEDGE_BASE_ID = os.environ['KNOWLEDGE_BASE_ID']
MODEL_ARN = os.environ['MODEL_ARN']
TEMPERATURE = float(os.environ.get('TEMPERATURE', '0.2'))
MAX_TOKENS = int(os.environ.get('MAX_TOKENS', '1024'))
MAX_QUERY_LENGTH = int(os.environ.get('MAX_QUERY_LENGTH', '5000'))

# Initialize Bedrock client
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler with conversational context support.
    """
    try:
        # Parse request
        body = json.loads(event.get('body', '{}'))
        query = body.get('query', '').strip()
        history = body.get('history', [])
        
        # Validate query
        if not query:
            return create_response(400, {'error': 'Query is required'})
        
        if len(query) > MAX_QUERY_LENGTH:
            return create_response(400, {'error': f'Query exceeds maximum length of {MAX_QUERY_LENGTH}'})
        
        # Validate history format
        if history and not isinstance(history, list):
            history = []
        
        # Build contextual query
        contextual_query = build_context_prompt(query, history)
        
        # Call Bedrock with context
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
                        }
                    }
                }
            }
        )
        
        # Validate response structure
        if 'output' not in response or 'text' not in response['output']:
            raise ValueError("Invalid Bedrock response structure")
        
        # Extract answer and sources
        answer = response['output']['text']
        citations = response.get('citations', [])
        sources = format_sources(citations)
        
        # Return response
        return create_response(200, {
            'answer': answer,
            'sources': sources
        })
        
    except json.JSONDecodeError:
        return create_response(400, {'error': 'Invalid JSON in request body'})
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return create_response(500, {'error': 'Internal server error'})

def format_sources(citations: List[Dict]) -> List[Dict]:
    """Format citation sources for response."""
    sources = []
    for citation in citations:
        for reference in citation.get('retrievedReferences', []):
            sources.append({
                'document': reference.get('location', {}).get('s3Location', {}).get('uri', ''),
                'excerpt': reference.get('content', {}).get('text', ''),
                'score': reference.get('metadata', {}).get('score', 0.0)
            })
    return sources

def create_response(status_code: int, body: Dict) -> Dict:
    """Create HTTP response with CORS headers."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', '*'),
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(body)
    }
```

#### Step 5: Testing

**Test Cases:**

1. **Follow-up question:**
   ```
   User: "What are the enrollment requirements?"
   Bot: "Requirements are: ..."
   User: "And how much does it cost?"
   Expected: Bot uses context to understand "it" refers to enrollment
   ```

2. **Independent question:**
   ```
   User: "When do classes start?"
   Bot: "December 20th"
   User: "What careers at San Joaquín campus?"
   Expected: Bot responds only about careers, ignores class dates
   ```

3. **Context window limit:**
   ```
   Send 15 messages
   Expected: Only last 10 messages maintained in frontend
   ```

4. **Browser close:**
   ```
   Close browser tab
   Reopen chatbot
   Expected: History is cleared (sessionStorage)
   ```

---

## Testing & Monitoring

### Unit Tests

```python
# test_handler.py
import pytest
from lambda_function import build_context_prompt, handler

def test_build_context_prompt_no_history():
    query = "What is Duoc UC?"
    history = []
    result = build_context_prompt(query, history)
    assert result == query

def test_build_context_prompt_with_history():
    query = "And how much does it cost?"
    history = [
        {"role": "user", "content": "What are enrollment requirements?"},
        {"role": "assistant", "content": "Requirements are..."}
    ]
    result = build_context_prompt(query, history)
    assert "Previous conversation:" in result
    assert "enrollment requirements" in result
    assert query in result

def test_handler_missing_query():
    event = {"body": json.dumps({})}
    response = handler(event, None)
    assert response['statusCode'] == 400
    assert 'error' in json.loads(response['body'])
```

### Integration Tests

```bash
# Test with curl
curl -X POST https://your-api.execute-api.us-east-1.amazonaws.com/prod/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the enrollment requirements?",
    "history": []
  }'

# Test with history
curl -X POST https://your-api.execute-api.us-east-1.amazonaws.com/prod/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "And how much does it cost?",
    "history": [
      {"role": "user", "content": "What are enrollment requirements?"},
      {"role": "assistant", "content": "Requirements are..."}
    ]
  }'
```

### CloudWatch Metrics

**Recommended Alarms:**

| Metric | Threshold | Action |
|--------|-----------|--------|
| Error Rate | > 5% | SNS notification |
| P50 Latency | > 5 seconds | SNS notification |
| Throttle Count | > 0 | SNS notification |

**Custom Metrics to Track:**
- Requests with/without history
- Average history size
- Context window truncations
- Query length distribution

---

## Deployment Checklist

### Pre-Deployment

- [ ] **Environment Variables Configured**
  - [ ] `KNOWLEDGE_BASE_ID` set
  - [ ] `MODEL_ARN` set
  - [ ] `ALLOWED_ORIGIN` set to production domain
  - [ ] `TEMPERATURE` tuned (default 0.2)
  - [ ] `MAX_TOKENS` configured (default 1024)

- [ ] **IAM Permissions**
  - [ ] Bedrock access granted
  - [ ] CloudWatch Logs access granted
  - [ ] X-Ray tracing enabled

- [ ] **API Gateway**
  - [ ] POST endpoint configured
  - [ ] CORS headers enabled
  - [ ] Throttling configured (e.g., 100 req/second)
  - [ ] Request size limit validated (10MB max)

### Code Quality

- [ ] **Lambda Handler**
  - [ ] Context management implemented
  - [ ] Input validation added
  - [ ] Error handling improved
  - [ ] Type hints added
  - [ ] Logging configured

- [ ] **Frontend**
  - [ ] `ChatHistory` class implemented
  - [ ] sessionStorage integration working
  - [ ] History sent with each request
  - [ ] 10-message limit enforced

### Testing

- [ ] **Unit Tests**
  - [ ] `build_context_prompt` tested
  - [ ] `ChatHistory` class tested
  - [ ] Error scenarios covered

- [ ] **Integration Tests**
  - [ ] Single query tested
  - [ ] Multi-turn conversation tested
  - [ ] Context window limit tested
  - [ ] History format validated

- [ ] **Load Testing**
  - [ ] Concurrent requests tested
  - [ ] Large payloads tested
  - [ ] Rate limiting validated

### Monitoring

- [ ] **CloudWatch**
  - [ ] Error rate alarm configured
  - [ ] Latency alarm configured
  - [ ] Custom metrics dashboard created

- [ ] **X-Ray**
  - [ ] Tracing enabled
  - [ ] Service map visible

### Documentation

- [ ] API documentation updated
- [ ] Frontend integration guide created
- [ ] Troubleshooting guide written
- [ ] Runbook for common issues prepared

---

## Cost Optimization

### No Database Costs 🎉

**Frontend-managed history eliminates:**
- ❌ DynamoDB costs (read/write operations)
- ❌ Additional IAM permissions
- ❌ Database query latency

**Cost Breakdown:**
- Lambda invocations: ~$0.20 per 1M requests
- API Gateway: ~$3.50 per 1M requests
- Bedrock API: Variable (based on model and tokens)
- Additional payload: ~1-2 KB per request (negligible)

**Optimization Tips:**
- Keep history at 10 messages (balance context vs payload size)
- Monitor API Gateway payload size (10MB limit)
- Use efficient JSON serialization
- Consider compression for very long conversations

---

## Troubleshooting

### Common Issues

**1. "No context being used in responses"**
- ✅ Check: Frontend sending `history` array?
- ✅ Check: Lambda receiving history in event body?
- ✅ Check: `build_context_prompt` being called?
- ✅ Check: CloudWatch logs for contextual query

**2. "History not persisting"**
- ✅ Check: `sessionStorage` supported in browser?
- ✅ Check: `ChatHistory.saveToStorage()` being called?
- ✅ Check: Browser console for storage errors
- ✅ Check: Privacy mode disabled (blocks sessionStorage)?
- ⚠️ **Note:** sessionStorage is cleared when the browser tab is closed (unlike localStorage which persists)

**3. "CORS errors"**
- ✅ Check: `ALLOWED_ORIGIN` matches frontend domain
- ✅ Check: API Gateway CORS configured
- ✅ Check: OPTIONS preflight handler configured

**4. "Rate limiting errors"**
- ✅ Check: API Gateway throttling settings
- ✅ Check: Concurrent request count
- ✅ Check: Bedrock quota limits

---

## References

- [AWS Bedrock Knowledge Bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [Boto3 Error Handling](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/error-handling.html)
- [sessionStorage MDN Docs](https://developer.mozilla.org/en-US/docs/Web/API/Window/sessionStorage)

---

## Quick Start

### 1. Deploy Lambda
```bash
# Package and deploy
zip function.zip lambda_function.py
aws lambda update-function-code \
  --function-name RetrieveAndGenerate \
  --zip-file fileb://function.zip
```

### 2. Configure Environment
```bash
aws lambda update-function-configuration \
  --function-name RetrieveAndGenerate \
  --environment "Variables={
    KNOWLEDGE_BASE_ID=your-kb-id,
    MODEL_ARN=cohere.command-r-v1:0,
    ALLOWED_ORIGIN=https://duoc.cl,
    TEMPERATURE=0.2,
    MAX_TOKENS=1024
  }"
```

### 3. Update Frontend
```javascript
// Add ChatHistory class and integrate with chatbot
// See implementation guide above
```

### 4. Test
```bash
# Test single query
curl -X POST $API_ENDPOINT -d '{"query":"What is Duoc UC?"}'

# Test with context
curl -X POST $API_ENDPOINT -d '{
  "query":"And how much?",
  "history":[
    {"role":"user","content":"What are fees?"},
    {"role":"assistant","content":"Fees are..."}
  ]
}'
```

---

**Last Updated:** November 2024  
**Version:** 2.0 (With Conversational Context)  
**Maintainer:** Duoc UC DevOps Team