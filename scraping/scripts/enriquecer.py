import os
import json
import requests
from dotenv import load_dotenv

# --- Configuración ---
load_dotenv() 

API_KEY = "xD"
API_URL = "xD"
MODELO = "glm-4.6"
INPUT_FILE = 'chunks_para_ia.jsonl'
OUTPUT_FILE = 'dataset_final_scraper.jsonl'
# ---------------------

SYSTEM_PROMPT = """
Eres un asistente de IA experto en procesar texto para un sistema RAG.
Tu tarea es leer un fragmento de texto ('answer') y generar un objeto JSON con:
1.  "category": Una categoría corta en español (ej. "escuela_diseno", "sobre_duoc", "admision").
2.  "questions": Una lista de 5 preguntas de ejemplo que un usuario haría y que este texto responde.
3.  "keywords": Una lista de 5-7 palabras clave relevantes.

Responde ÚNICAMENTE con el objeto JSON, sin explicaciones.
"""

def llamar_llm(chunk_text):
    if not API_KEY:
        raise ValueError("No se encontró ZHIPU_API_KEY en el archivo .env")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODELO,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Texto a procesar:\n\n{chunk_text}"}
        ],
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status() 
        
        llm_response_data = response.json()
        json_string = llm_response_data['choices'][0]['message']['content']
        enriquecimiento = json.loads(json_string)
        return enriquecimiento

    except requests.exceptions.RequestException as e:
        print(f"Error de API: {e}")
        return None
    except Exception as e:
        print(f"Error general en llamar_llm: {e}")
        return None

def enriquecer_dataset():
    print(f"Iniciando enriquecimiento con LLM desde '{INPUT_FILE}'...")
    
    if not os.path.exists(INPUT_FILE):
        print(f"Error: No se encontró el archivo '{INPUT_FILE}'. Ejecuta 'procesar_chunks.py' primero.")
        return

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f_in:
            for i, line in enumerate(f_in):
                try:
                    chunk_data = json.loads(line)
                    answer_text = chunk_data.get("answer")
                    
                    if not answer_text:
                        continue
                    
                    print(f"Procesando chunk {i+1} (ID: {chunk_data.get('id')})...")
                    datos_ia = llamar_llm(answer_text)
                    
                    if datos_ia:
                        documento_final = {
                            "id": chunk_data.get("id"),
                            "type": "info",
                            "category": datos_ia.get("category", "general"),
                            "questions": datos_ia.get("questions", []),
                            "answer": answer_text,
                            "source": chunk_data.get("source_title", "Duoc UC"),
                            "url": chunk_data.get("source_url"),
                            "keywords": datos_ia.get("keywords", [])
                        }
                        f_out.write(json.dumps(documento_final, ensure_ascii=False) + '\n')
                    else:
                        print(f"Skipping chunk {i+1} due to enrichment error.")

                except Exception as e:
                    print(f"Error procesando la línea {i+1}: {e}")

    print(f"\n--- ¡Enriquecimiento completado! ---")
    print(f"Dataset final guardado en: '{OUTPUT_FILE}'")

if __name__ == "__main__":
    enriquecer_dataset()