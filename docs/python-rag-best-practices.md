# Python & RAG Architecture Best Practices

## Table of Contents
1. [Python Best Practices for Lambda](#python-best-practices-for-lambda)
2. [RAG Architecture Best Practices](#rag-architecture-best-practices)
3. [Error Handling Patterns](#error-handling-patterns)
4. [Type Hints & Code Quality](#type-hints--code-quality)
5. [Structured Logging](#structured-logging)
6. [Input Validation](#input-validation)
7. [Context Management in RAG](#context-management-in-rag)
8. [AWS Bedrock Best Practices](#aws-bedrock-best-practices)

---

## Python Best Practices for Lambda

### Type Annotations

**Always use type hints for function parameters and return types:**

```python
from typing import Dict, List, Any, Optional

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler with type annotations.
    
    Args:
        event: Lambda event dictionary
        context: Lambda context object
        
    Returns:
        Response dictionary with statusCode and body
    """
    pass
```

**Use `| None` for optional types (Python 3.10+):**

```python
def process_query(query: str | None = None) -> str:
    if query is None:
        return ""
    return query.strip()
```

**Avoid implicit None in default parameters:**

```python
# Bad
def func(value: str = None) -> str:
    pass

# Good
def func(value: str | None = None) -> str:
    pass
```

### Annotated Assignments

**Use annotated assignments when type inference is difficult:**

```python
from typing import Annotated

# When type is hard to infer
response: Dict[str, Any] = bedrock_client.retrieve_and_generate(...)
```

---

## Error Handling Patterns

### Specific Exception Handling

**Handle specific exceptions, not generic `Exception`:**

```python
import json
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        body = json.loads(event.get('body', '{}'))
        query = body.get('query', '').strip()
        
        if not query:
            raise ValueError('Query is required')
        
        # Bedrock API call
        response = bedrock_client.retrieve_and_generate(...)
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request body: {e}")
        return create_error_response(400, "Invalid JSON in request body")
    
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return create_error_response(400, str(e))
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"Bedrock API error [{error_code}]: {error_message}")
        
        if error_code == 'ThrottlingException':
            return create_error_response(429, "Service temporarily unavailable")
        elif error_code == 'ValidationException':
            return create_error_response(400, "Invalid request parameters")
        else:
            return create_error_response(500, "Internal server error")
    
    except Exception as e:
        logger.exception("Unexpected error occurred", exc_info=e)
        return create_error_response(500, "Internal server error")
```

### Error Messages

**Use clear, precise error messages with context:**

```python
# Good: Clear error message with context
if not 0 <= temperature <= 1:
    raise ValueError(f'Temperature must be between 0 and 1, got {temperature}')

# Bad: Vague error message
if not 0 <= temperature <= 1:
    raise ValueError('Invalid temperature')
```

**Include error details in logs but not in user-facing messages:**

```python
try:
    response = bedrock_client.retrieve_and_generate(...)
except ClientError as e:
    # Log full details
    logger.error(
        "Bedrock API call failed",
        extra={
            "error_code": e.response['Error']['Code'],
            "error_message": e.response['Error']['Message'],
            "request_id": e.response.get('ResponseMetadata', {}).get('RequestId'),
        }
    )
    # Return generic message to user
    return create_error_response(500, "Internal server error")
```

---

## Type Hints & Code Quality

### Function Signatures

**Always annotate function parameters and return types:**

```python
from typing import Dict, List, Any, Optional

def build_context_prompt(query: str, history: List[Dict[str, str]]) -> str:
    """
    Builds contextual query from conversation history.
    
    Args:
        query: Current user query
        history: List of conversation messages with 'role' and 'content' keys
        
    Returns:
        Contextual prompt string
        
    Raises:
        ValueError: If query is empty or history format is invalid
    """
    if not query:
        raise ValueError("Query cannot be empty")
    
    if not isinstance(history, list):
        raise ValueError("History must be a list")
    
    # Implementation
    return contextual_query
```

### Class Methods

**Use `Self` for class methods that return the same class:**

```python
from typing import Self

class ChatHistory:
    def add_message(self, role: str, content: str) -> Self:
        self.messages.append({"role": role, "content": content})
        return self
```

---

## Structured Logging

### AWS Lambda Powertools Logger

**Use AWS Powertools for structured logging:**

```python
from aws_lambda_powertools import Logger
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="retrieve-and-generate")

@logger.inject_lambda_context(
    correlation_id_path=correlation_paths.API_GATEWAY_REST,
    log_event=True
)
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    logger.info("Processing request", extra={"query_length": len(query)})
    
    try:
        response = bedrock_client.retrieve_and_generate(...)
        logger.info("Request processed successfully")
        return response
    except Exception as e:
        logger.exception("Error processing request", exc_info=e)
        raise
```

### Logging Best Practices

**Log exceptions with context:**

```python
try:
    response = bedrock_client.retrieve_and_generate(...)
except ClientError as e:
    logger.error(
        "Bedrock API error",
        extra={
            "error_code": e.response['Error']['Code'],
            "knowledge_base_id": KNOWLEDGE_BASE_ID,
            "query_length": len(query),
        },
        exc_info=True
    )
    raise
```

**Flush logs on uncaught exceptions:**

```python
@logger.inject_lambda_context(flush_buffer_on_uncaught_error=True)
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    # Logs will be flushed automatically on uncaught exceptions
    pass
```

---

## Input Validation

### Request Validation with Pydantic

**Use Pydantic models for request validation:**

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional

class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=10000)

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=5000)
    history: Optional[List[Message]] = Field(default=None, max_items=10)
    temperature: Optional[float] = Field(default=0.2, ge=0.0, le=1.0)
    
    @validator('history')
    def validate_history(cls, v):
        if v and len(v) > 10:
            raise ValueError('History cannot contain more than 10 messages')
        return v

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        body = json.loads(event.get('body', '{}'))
        request = ChatRequest(**body)
        
        # Process validated request
        response = process_query(request.query, request.history)
        
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return create_error_response(400, "Invalid request parameters")
```

### Manual Validation

**Validate inputs before processing:**

```python
def validate_query(query: str, max_length: int = 5000) -> None:
    """
    Validates query string.
    
    Args:
        query: Query string to validate
        max_length: Maximum allowed length
        
    Raises:
        ValueError: If query is invalid
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    
    if len(query) > max_length:
        raise ValueError(f"Query exceeds maximum length of {max_length} characters")
    
    # Additional validation (e.g., no injection attempts)
    if any(char in query for char in ['<', '>', '{', '}']):
        logger.warning(f"Potentially malicious query detected: {query[:100]}")
```

---

## RAG Architecture Best Practices

### Context Management

**Build contextual prompts that instruct the LLM to use context only when relevant:**

```python
def build_context_prompt(query: str, history: List[Dict[str, str]]) -> str:
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
        "If the current question is about a different topic, ignore previous context.",
        ""
    ]
    
    # Add conversation history (last 10 messages)
    for msg in history[-10:]:
        role = msg.get('role', 'user').capitalize()
        content = msg.get('content', '').strip()
        if content:
            context_parts.append(f"{role}: {content}")
    
    # Add current question
    context_parts.extend([
        "",
        f"Current question: {query}",
        "",
        "Instructions: Answer the current question. Use previous context only if directly relevant."
    ])
    
    return "\n".join(context_parts)
```

### Document Chunking

**Use appropriate chunk sizes and overlap:**

```python
# Recommended chunk sizes for RAG
CHUNK_SIZE = 1000  # characters
CHUNK_OVERLAP = 200  # characters

# For Bedrock Knowledge Bases, chunking is handled automatically
# but you can configure it during knowledge base creation
```

### Retrieval Configuration

**Configure retrieval parameters for optimal results:**

```python
retrieval_config = {
    "vectorSearchConfiguration": {
        "numberOfResults": 5,  # Retrieve top 5 results
        "rerankingConfiguration": {
            "modelArn": "arn:aws:bedrock:us-east-1::foundation-model/cohere.rerank-english-v1:0",
            "numberOfRerankedResults": 3  # Return top 3 after reranking
        }
    }
}
```

### Response Formatting

**Format sources with metadata for transparency:**

```python
def format_sources(citations: List[Dict]) -> List[Dict]:
    """
    Format citation sources for response.
    
    Args:
        citations: List of citation objects from Bedrock
        
    Returns:
        List of formatted source dictionaries
    """
    sources = []
    for citation in citations:
        for reference in citation.get('retrievedReferences', []):
            source = {
                "document": reference.get('location', {}).get('s3Location', {}).get('uri', ''),
                "excerpt": reference.get('content', {}).get('text', ''),
                "score": reference.get('metadata', {}).get('score', 0.0),
                "metadata": reference.get('metadata', {})
            }
            sources.append(source)
    return sources
```

---

## Context Management in RAG

### Conversation History

**Maintain conversation history in frontend (no database needed):**

```python
# Frontend manages history in localStorage/sessionStorage
# Lambda receives history and builds contextual query

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    body = json.loads(event.get('body', '{}'))
    query = body.get('query', '').strip()
    history = body.get('history', [])
    
    # Validate history format
    if history and not isinstance(history, list):
        history = []
    
    # Limit history to last 10 messages
    history = history[-10:] if len(history) > 10 else history
    
    # Build contextual query
    contextual_query = build_context_prompt(query, history)
    
    # Call Bedrock with contextual query
    response = bedrock_client.retrieve_and_generate(
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
    
    return create_response(200, {
        'answer': response['output']['text'],
        'sources': format_sources(response.get('citations', []))
    })
```

### Session Management

**Use Bedrock session management for conversational context:**

```python
# Bedrock supports session-based context management
# Use sessionId to maintain conversation state

response = bedrock_client.retrieve_and_generate(
    input={'text': query},
    retrieveAndGenerateConfiguration={
        'type': 'KNOWLEDGE_BASE',
        'knowledgeBaseConfiguration': {
            'knowledgeBaseId': KNOWLEDGE_BASE_ID,
            'modelArn': MODEL_ARN,
        },
        'sessionId': session_id  # Reuse same session ID for conversation
    }
)

# Bedrock returns sessionId in response for subsequent requests
session_id = response.get('sessionId')
```

---

## AWS Bedrock Best Practices

### Error Handling

**Handle Bedrock-specific errors:**

```python
from botocore.exceptions import ClientError

try:
    response = bedrock_client.retrieve_and_generate(...)
except ClientError as e:
    error_code = e.response['Error']['Code']
    
    if error_code == 'ThrottlingException':
        # Handle throttling
        logger.warning("Bedrock throttling detected")
        return create_error_response(429, "Service temporarily unavailable")
    
    elif error_code == 'ValidationException':
        # Handle validation errors
        logger.error(f"Validation error: {e.response['Error']['Message']}")
        return create_error_response(400, "Invalid request parameters")
    
    elif error_code == 'AccessDeniedException':
        # Handle access denied
        logger.error("Access denied to Bedrock")
        return create_error_response(403, "Access denied")
    
    else:
        # Handle other errors
        logger.error(f"Bedrock error: {error_code}")
        return create_error_response(500, "Internal server error")
```

### Configuration

**Use environment variables for configuration:**

```python
import os
from typing import Optional

# Required environment variables
KNOWLEDGE_BASE_ID = os.environ['KNOWLEDGE_BASE_ID']
MODEL_ARN = os.environ['MODEL_ARN']
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')

# Optional with defaults
TEMPERATURE = float(os.environ.get('TEMPERATURE', '0.2'))
MAX_TOKENS = int(os.environ.get('MAX_TOKENS', '1024'))
MAX_QUERY_LENGTH = int(os.environ.get('MAX_QUERY_LENGTH', '5000'))
MAX_CONTEXT_MESSAGES = int(os.environ.get('MAX_CONTEXT_MESSAGES', '10'))
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
```

### Response Validation

**Validate Bedrock response structure:**

```python
def validate_bedrock_response(response: Dict[str, Any]) -> None:
    """
    Validates Bedrock response structure.
    
    Args:
        response: Bedrock API response
        
    Raises:
        ValueError: If response structure is invalid
    """
    if 'output' not in response:
        raise ValueError("Missing 'output' in Bedrock response")
    
    if 'text' not in response['output']:
        raise ValueError("Missing 'text' in Bedrock response output")
    
    if not isinstance(response['output']['text'], str):
        raise ValueError("Bedrock response 'text' must be a string")
```

### Retry Logic

**Implement retry logic for transient errors:**

```python
import time
from botocore.exceptions import ClientError

def retrieve_with_retry(
    bedrock_client,
    query: str,
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> Dict[str, Any]:
    """
    Retrieve and generate with retry logic for transient errors.
    
    Args:
        bedrock_client: Bedrock client
        query: Query string
        max_retries: Maximum number of retries
        retry_delay: Delay between retries in seconds
        
    Returns:
        Bedrock response
        
    Raises:
        ClientError: If all retries fail
    """
    for attempt in range(max_retries):
        try:
            response = bedrock_client.retrieve_and_generate(...)
            return response
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            # Retry on throttling or service errors
            if error_code in ['ThrottlingException', 'ServiceUnavailableException']:
                if attempt < max_retries - 1:
                    logger.warning(f"Retrying after {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
            raise
```

---

## Complete Example

### Improved Lambda Handler

```python
import json
import os
import boto3
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field, ValidationError
from aws_lambda_powertools import Logger
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext

# Initialize logger
logger = Logger(service="retrieve-and-generate")

# Environment variables
KNOWLEDGE_BASE_ID = os.environ['KNOWLEDGE_BASE_ID']
MODEL_ARN = os.environ['MODEL_ARN']
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', '*')
TEMPERATURE = float(os.environ.get('TEMPERATURE', '0.2'))
MAX_TOKENS = int(os.environ.get('MAX_TOKENS', '1024'))
MAX_QUERY_LENGTH = int(os.environ.get('MAX_QUERY_LENGTH', '5000'))
MAX_CONTEXT_MESSAGES = int(os.environ.get('MAX_CONTEXT_MESSAGES', '10'))

# Initialize Bedrock client
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))


# Pydantic models for validation
class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=10000)


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH)
    history: Optional[List[Message]] = Field(default=None, max_items=MAX_CONTEXT_MESSAGES)


def build_context_prompt(query: str, history: List[Dict[str, str]]) -> str:
    """Builds contextual query from conversation history."""
    if not history:
        return query
    
    context_parts = [
        "Previous conversation:",
        "IMPORTANT: Use this context ONLY if relevant to the current question.",
        "If the current question is about a different topic, ignore previous context.",
        ""
    ]
    
    for msg in history[-MAX_CONTEXT_MESSAGES:]:
        role = msg.get('role', 'user').capitalize()
        content = msg.get('content', '').strip()
        if content:
            context_parts.append(f"{role}: {content}")
    
    context_parts.extend([
        "",
        f"Current question: {query}",
        "",
        "Instructions: Answer the current question. Use previous context only if directly relevant."
    ])
    
    return "\n".join(context_parts)


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
            'Access-Control-Allow-Origin': ALLOWED_ORIGIN,
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(body)
    }


@logger.inject_lambda_context(
    correlation_id_path=correlation_paths.API_GATEWAY_REST,
    log_event=True
)
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Lambda handler with conversational context support."""
    try:
        # Parse and validate request
        body = json.loads(event.get('body', '{}'))
        request = ChatRequest(**body)
        
        # Convert Pydantic models to dictionaries
        history = [msg.dict() for msg in request.history] if request.history else []
        
        # Build contextual query
        contextual_query = build_context_prompt(request.query, history)
        
        # Call Bedrock
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
        
        # Validate response
        if 'output' not in response or 'text' not in response['output']:
            raise ValueError("Invalid Bedrock response structure")
        
        # Extract answer and sources
        answer = response['output']['text']
        citations = response.get('citations', [])
        sources = format_sources(citations)
        
        logger.info("Request processed successfully", extra={
            "query_length": len(request.query),
            "history_length": len(history),
            "answer_length": len(answer),
            "sources_count": len(sources)
        })
        
        return create_response(200, {
            'answer': answer,
            'sources': sources
        })
        
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in request body", exc_info=e)
        return create_response(400, {'error': 'Invalid JSON in request body'})
    
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return create_response(400, {'error': 'Invalid request parameters', 'details': str(e)})
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        logger.error(
            "Bedrock API error",
            extra={
                'error_code': error_code,
                'error_message': error_message,
                'knowledge_base_id': KNOWLEDGE_BASE_ID
            }
        )
        
        if error_code == 'ThrottlingException':
            return create_response(429, {'error': 'Service temporarily unavailable'})
        elif error_code == 'ValidationException':
            return create_response(400, {'error': 'Invalid request parameters'})
        else:
            return create_response(500, {'error': 'Internal server error'})
    
    except Exception as e:
        logger.exception("Unexpected error occurred", exc_info=e)
        return create_response(500, {'error': 'Internal server error'})
```

---

## References

- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [AWS Lambda Powertools for Python](https://github.com/aws-powertools/powertools-lambda-python)
- [LangChain RAG Documentation](https://docs.langchain.com/oss/python/langchain/rag)
- [Amazon Bedrock Knowledge Bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
- [RAG From Scratch](https://github.com/langchain-ai/rag-from-scratch)

