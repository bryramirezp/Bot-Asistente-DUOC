# Optimización de la Mesa de Servicio Estudiantil mediante un Asistente Inteligente

![AWS](https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon_Bedrock-FF9900?style=for-the-badge&logo=amazon-aws&logoColor=white)
![AWS Lambda](https://img.shields.io/badge/AWS_Lambda-FF9900?style=for-the-badge&logo=aws-lambda&logoColor=white)
![API Gateway](https://img.shields.io/badge/API_Gateway-FF4F8B?style=for-the-badge&logo=amazon-api-gateway&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![OpenSearch](https://img.shields.io/badge/OpenSearch-005EB8?style=for-the-badge&logo=opensearch&logoColor=white)

## 📋 Resumen Ejecutivo

Este proyecto de título aborda la sobrecarga operativa crítica que experimenta la Mesa de Servicio Estudiantil de Duoc UC durante períodos de alta demanda, particularmente en los inicios de semestre académico.

### Problemática Identificada

Durante el período 2024-1 (específicamente marzo), la Mesa de Servicio experimentó:

- 29,550 contactos telefónicos ingresados
- Solo 11,307 fueron atendidos
- Nivel de atención del 38% (mínimo crítico)
- Más del 60% de usuarios sin respuesta

El análisis histórico revela un patrón cíclico predecible con picos de saturación en enero, marzo y agosto, donde el volumen de interacciones supera ampliamente la capacidad del equipo humano de soporte.

### Solución Propuesta

Diseño, desarrollo y validación de un **Asistente Conversacional Inteligente** basado en:

- Arquitectura 100% serverless nativa en Amazon Web Services (AWS)
- Inteligencia Artificial Generativa mediante AWS Bedrock
- Patrón RAG (Retrieval-Augmented Generation) para garantizar precisión
- Conexión directa y segura a la base de conocimientos oficial de Duoc UC

### Impacto y Valor Agregado

**Para los estudiantes:**

- Respuestas inmediatas y precisas 24/7
- Eliminación de tiempos de espera en períodos críticos
- Mejora significativa en la experiencia de atención

**Para la institución:**

- Optimización de recursos humanos y tecnológicos
- Reducción de la carga operativa sobre el personal de soporte
- Liberación del equipo para casos de alta complejidad
- Escalabilidad automática durante picos de demanda

---

## 🎯 Objetivos del Proyecto

### Objetivo General

Validar, a través de un proyecto piloto, la efectividad de un asistente conversacional inteligente para disminuir la sobrecarga operativa de la Mesa de Servicio de Duoc UC, mediante la automatización de respuestas a consultas frecuentes.

### Objetivos Específicos

1. Diseñar una arquitectura de solución moderna, eficiente y basada en la nube
2. Establecer una conexión automática y segura a la base de conocimientos oficial
3. Implementar el motor de inteligencia artificial que procesa la información y genera respuestas
4. Desarrollar la lógica de comunicación entre el usuario y el motor inteligente
5. Crear un punto de acceso seguro para la interacción con el asistente
6. Realizar pruebas funcionales para demostrar resolución coherente de consultas reales

---

## 🏗️ Arquitectura de la Solución

### Principios Arquitectónicos

La arquitectura se fundamenta en dos pilares estratégicos:

- Modelo Serverless: Eliminación de gestión de infraestructura, escalabilidad automática y optimización de costos mediante pago por uso
- Patrón RAG: Mitigación de "alucinaciones" del LLM mediante recuperación de información verificable

### Componentes Tecnológicos Clave

1. **Núcleo Cognitivo: Amazon Bedrock Knowledge Bases**
   - Motor RAG totalmente gestionado que implementa:
     - Ingesta y Vectorización: Conexión a SharePoint con procesamiento mediante Amazon Titan Text Embeddings V2
     - Almacenamiento Vectorial: Amazon OpenSearch Serverless para búsquedas semánticas de baja latencia
     - Orquestación RAG: API RetrieveAndGenerate que automatiza el flujo completo
     - Generación de Respuesta: Modelo de lenguaje Llama 3.1 8B para síntesis contextualizada

2. **Orquestación y Capa de API**
   - Amazon API Gateway: Punto de entrada RESTful seguro con gestión de CORS
   - AWS Lambda: Orquestador principal en Python que invoca Bedrock y formatea respuestas

3. **Servicios de Seguridad y Observabilidad**
   - AWS WAF y Shield: Protección contra ataques web y DDoS
   - AWS KMS: Cifrado de datos en reposo
   - AWS Secrets Manager: Gestión segura de credenciales
   - Amazon CloudWatch y X-Ray: Monitorización y trazabilidad distribuida

4. **Frontend**
   - Widget de Chatbot: Interfaz HTML/CSS/JavaScript integrada con API Gateway
   - **Demo desplegado**: [http://frontend-duocuc-mesa-de-servicio.s3-website-us-east-1.amazonaws.com](http://frontend-duocuc-mesa-de-servicio.s3-website-us-east-1.amazonaws.com)
     - *Nota*: El widget está creado y desplegado, pero OpenSearch y la parte de IA no están funcionando para evitar incurrir en gastos.

### Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (Cliente)                         │
│                  Widget Chatbot (HTML/JS)                       │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP POST
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Amazon API Gateway (REST)                     │
│              • CORS habilitado                                  │
│              • Protección WAF/Shield                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AWS Lambda (Python)                         │
│              • Orquestador del flujo RAG                        │
│              • Invoca RetrieveAndGenerate API                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Amazon Bedrock Knowledge Bases                     │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  1. Vectorización (Titan Embeddings V2)                   │ │
│  │  2. Búsqueda Semántica (OpenSearch Serverless)            │ │
│  │  3. Recuperación de Contexto                              │ │
│  │  4. Generación LLM (Llama 3.1 8B)                         │ │
│  └───────────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Fuente de Datos: SharePoint Duoc UC                │
│          • Manuales institucionales                             │
│          • Reglamentos académicos                               │
│          • FAQs oficiales                                       │
└─────────────────────────────────────────────────────────────────┘
```

### Flujos de Datos Fundamentales

#### Flujo de Ingesta (Asíncrono)

SharePoint → Bedrock KB → Chunking → Titan Embeddings → OpenSearch Serverless

- Sincronización programada desde SharePoint
- Procesamiento y fragmentación de documentos
- Conversión a vectores (embeddings)
- Indexación en OpenSearch para búsquedas

#### Flujo de Consulta (Tiempo Real)

Usuario → Widget → API Gateway → Lambda → Bedrock RetrieveAndGenerate
                                              ↓
                                    OpenSearch (recuperación)
                                              ↓
                                    LLM (generación) → Respuesta

---

## 📅 Carta Gantt - Plan de Trabajo Detallado

### Fase 1: Planificación y Diseño (2 semanas)

| Actividad | Responsable | Inicio | Fin | Duración | Entregables |
|-----------|-------------|--------|-----|----------|-------------|
| **1.1 Definición y documentación** | Bryan R.P | 01/09/25 | 07/09/25 | 6 días | Guía APT completa y documentada |
| **1.2 Diseño de Arquitectura** | Bryan R.P | 08/09/25 | 14/09/25 | 6 días | Diagrama de arquitectura final de la solución |

**Competencias aplicadas**: Control y gestión de Proyectos, Diseño de Soluciones de Infraestructura

---

### Fase 2: Implementación y Desarrollo (4 semanas)

| Actividad | Responsable | Inicio | Fin | Duración | Entregables |
|-----------|-------------|--------|-----|----------|-------------|
| **2.1 Configuración de Bedrock KB** | Bryan R.P | 15/09/25 | 28/09/25 | 13 días | Knowledge Base funcional y sincronizada con datos |
| **2.2 Desarrollo de función Lambda** | Bryan R.P | 29/09/25 | 12/10/25 | 13 días | Código fuente de la función Lambda desplegada |

**Competencias aplicadas**: Gestión de Servicios TI, Programación de Scripting

**Detalles técnicos**:
- Configuración del conector nativo a SharePoint
- Vectorización automática de documentos
- Desarrollo en Python con AWS SDK (Boto3)
- Configuración de variables de entorno y permisos IAM

---

### Fase 3: Integración y Validación (4 semanas)

| Actividad | Responsable | Inicio | Fin | Duración | Entregables |
|-----------|-------------|--------|-----|----------|-------------|
| **3.1 Configuración de API Gateway** | Bryan R.P | 13/10/25 | 19/10/25 | 6 días | Endpoint HTTP funcional e integrado con Lambda |
| **3.2 Desarrollo de Widget de chatbot** | Bryan R.P | 20/10/25 | 02/11/25 | 13 días | Código fuente del widget del chatbot integrado |
| **3.3 Pruebas de integración** | Bryan R.P | 03/11/25 | 09/11/25 | 6 días | Informe de resultados de pruebas end-to-end |

**Competencias aplicadas**: Administración de aplicaciones corporativas

**Alcance de pruebas**:
- Validación de flujo extremo a extremo
- Evaluación de calidad de respuestas
- Mitigación de alucinaciones del modelo
- Monitoreo con CloudWatch y X-Ray

---

### Fase 4: Cierre del Proyecto (2 semanas)

| Actividad | Responsable | Inicio | Fin | Duración | Entregables |
|-----------|-------------|--------|-----|----------|-------------|
| **4.1 Creación de evidencias finales** | Bryan R.P | 10/11/25 | 16/11/25 | 6 días | Vídeo de demostración y presentación final |
| **4.2 Redacción de informe final** | Bryan R.P | 17/11/25 | 23/11/25 | 6 días | Documento "Portafolio de Título" finalizado |

---

## 🧪 Estrategia de Pruebas y Control de Costos

### Arquitectura de Simulación Local

Para validar el sistema sin incurrir en costos de AWS, se implementa un ecosistema Docker con:

1. **OpenSearch** - Base de datos vectorial local
2. **Servicio de Embeddings** - Modelo `sentence-transformers/all-MiniLM-L6-v2` (~100 MB)
3. **LLM Local** - Llama 3.1 8B via Ollama (quantized)
4. **Serveless Framework** - Simulación de Lambda y API Gateway local

### Conjunto de Datos de Prueba

- 3-5 documentos PDF clave (Reglamento Académico, guías de inscripción, FAQs)
- Segmentación en chunks con metadatos
- Casos de prueba representativos de consultas reales

---

## 🔐 Seguridad y Mejores Prácticas

- **Principio de mínimo privilegio** en roles IAM
- **Cifrado en reposo** con AWS KMS
- **Gestión segura de secretos** con AWS Secrets Manager
- **Protección perimetral** con AWS WAF y AWS Shield
- **Infraestructura como Código** (IaC) con CloudFormation/Terraform
- **Entornos efímeros** para optimización de costos

---

## 📊 Análisis de Riesgos y Mitigación

| Riesgo | Nivel | Estrategia de Mitigación |
|--------|-------|--------------------------|
| Comunicación a distancia (México) | Medio | Agenda proactiva con reuniones periódicas y reportes semanales |
| Dependencia de acceso a SharePoint oficial | Alto | Entorno de pruebas en instancia propia con datos de ejemplo |
| Alucinaciones del modelo de IA | Alto | Arquitectura RAG + pruebas de calidad + ajuste de parámetros |
| Baja adopción por UX deficiente | Medio | Pruebas con preguntas reales extraídas de informes históricos |

---

## 🎓 Competencias Profesionales Aplicadas

1. **Control y gestión de proyectos** - Metodología híbrida PMBOK + Ágil
2. **Diseño de infraestructura tecnológica** - Arquitectura serverless moderna
3. **Seguridad informática** - Implementación de políticas y controles
4. **Administración de aplicaciones** - Desarrollo y despliegue de chatbot
5. **Innovación en servicios** - Solución novedosa con IA generativa
6. **Tecnologías de nube e IA** - Aplicación intensiva de AWS y RAG

---

## 📚 Metodología

### Enfoque Híbrido

- **PMBOK (Predictivo)**: Planificación estructurada, gestión de costos, documentación
- **Ágil (Adaptativo)**: Desarrollo iterativo, entregas incrementales, retroalimentación continua

### Dominios de Desempeño PMBOK Aplicados

- Planificación
- Trabajo del Proyecto
- Entrega
- Medición
- Interesados

---

## 👨‍💻 Autor

**Bryan Ramírez Palacios**
Ingeniería en Infraestructura y Plataformas Tecnológicas
Duoc UC - Escuela de Informática y Telecomunicaciones

**Docente Guía**: Claudio Núñez

### 📁 Recursos del Proyecto

- **Carpeta completa del proyecto**: [Google Drive](https://drive.google.com/drive/folders/1ajL1A5PTd4-0Wlte4YdRQdZ-uh3eWy5K)
- **Bitácora de trabajo**: [Google Docs](https://docs.google.com/document/d/1_n-UU1rDAuizTucAiZUDNYJATKrEnnpawhlmRTQ4XVc/edit?usp=sharing)
- **Informe final (Word)**: [Google Docs](https://docs.google.com/document/d/1sDiCfvqCBfJyFz_vuaKyieyLOIPPmjjt/edit?usp=sharing&ouid=103942992173874091609&rtpof=true&sd=true)

---

## 📖 Referencias

- Project Management Institute. (2021). *PMBOK Guide* (7.ª ed.)
- Amazon Web Services. *AWS Well-Architected Framework*
- Amazon Web Services. *AWS Service Terms*
- Duoc UC. (2025). Informes internos de Mesa de Servicios

---

**Fecha de inicio**: Agosto 2025  
**Fecha estimada de finalización**: Noviembre 2025  
**Ubicación**: Monterrey, Nuevo León, México