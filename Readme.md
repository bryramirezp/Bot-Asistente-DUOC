# Optimización de la Mesa de Servicio Estudiantil mediante un Asistente Inteligente

![AWS](https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white)
![Amazon Bedrock](https://img.shields.io/badge/Amazon_Bedrock-FF9900?style=for-the-badge&logo=amazon-aws&logoColor=white)
![AWS Lambda](https://img.shields.io/badge/AWS_Lambda-FF9900?style=for-the-badge&logo=aws-lambda&logoColor=white)
![API Gateway](https://img.shields.io/badge/API_Gateway-FF4F8B?style=for-the-badge&logo=amazon-api-gateway&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-7B42BC?style=for-the-badge&logo=terraform&logoColor=white)
![OpenSearch](https://img.shields.io/badge/OpenSearch-005EB8?style=for-the-badge&logo=opensearch&logoColor=white)
![SharePoint](https://img.shields.io/badge/SharePoint-0078D4?style=for-the-badge&logo=microsoft-sharepoint&logoColor=white)

## 📋 Resumen del Proyecto

Este proyecto de título aborda la sobrecarga operativa crítica que experimenta la Mesa de Servicio Estudiantil de Duoc UC durante períodos de alta demanda, donde los niveles de atención han caído hasta un **31%** en períodos críticos. El problema se origina en el volumen masivo de consultas repetitivas, donde requerimientos como "Inscripción de Asignaturas" e "Información General" representan el **57%** de todos los llamados gestionados.

### Solución Propuesta

Diseño y validación de un **Asistente Conversacional Inteligente** basado en:

- **Arquitectura 100% serverless** en Amazon Web Services (AWS)
- **Inteligencia Artificial Generativa** mediante Amazon Bedrock
- **Patrón RAG** (Retrieval Augmented Generation) para respuestas precisas
- Conexión directa y segura a la base de conocimientos oficial en SharePoint

### Impacto Esperado

- **Para estudiantes**: Respuestas inmediatas 24/7, eliminando tiempos de espera en períodos peak
- **Para la institución**: Optimización de recursos humanos (más de 70 personas movilizadas en períodos críticos) y mejora significativa en la eficiencia operativa

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

### Componentes Principales

1. **Widget del Chatbot** (HTML/CSS/JavaScript)
   - Interfaz de usuario para interacción con estudiantes
   
2. **Amazon API Gateway**
   - Punto de acceso seguro con configuración CORS
   - Protección con AWS WAF y AWS Shield
   
3. **AWS Lambda**
   - Orquestación de la lógica RAG en Python
   - Invocación de la API RetrieveAndGenerate
   
4. **Amazon Bedrock Knowledge Bases**
   - Motor RAG totalmente gestionado
   - Conexión nativa a SharePoint
   - Vectorización con Amazon Titan Text Embeddings
   - Almacenamiento en Amazon OpenSearch Serverless
   - Generación con Anthropic Claude 3

5. **Servicios de Seguridad**
   - AWS KMS para cifrado de datos
   - AWS Secrets Manager para gestión de credenciales
   - Amazon CloudWatch para monitoreo
   - AWS X-Ray para trazabilidad

### Flujo de Datos

```
Usuario → Widget → API Gateway → Lambda → Bedrock KB → SharePoint
↓
LLM (Claude 3)
↓
OpenSearch
```

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
4. **AWS SAM** - Simulación de Lambda y API Gateway local

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