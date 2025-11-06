import json
import re
import os

# --- Configuración ---
INPUT_FILE = 'dataset_filtrado.json'  # El resultado del script anterior
OUTPUT_JSONL = 'chunks_para_ia.jsonl' # La materia prima para el LLM
MIN_CHUNK_WORDS = 15                  # Mínimo de palabras para ser un "chunk" válido
# ---------------------

def limpiar_texto(texto):
    """
    Limpia el texto crudo del scraper.
    """
    patterns_to_remove = [
        r'VER MÁS', r'DESCARGAR LIBRO', r'VER \d+ AÑOS', r'MATRICÚLATE',
        r'MÁS INFORMACIÓN', r'CONOCE MÁS', r'IR AL PORTAL', r'VER TODAS LAS CARRERAS',
        r'IR A EDUCACIÓN CONTINUA', r'DESCARGAR', r'IR A CENTRO DE AYUDA',
        r'IR A BIBLIOTECA', r'IR A AVA', r'IR A CORREO', r'IR A UVS',
        r'VER EMPLEOS', r'ingresa aquí', r'VER DETALLE', r'VER MÁS DE NUESTRAS ESCUELAS',
        r'Click Aquí', r'Postula Aquí', r'hola', r'DESCUBRE MÁS', r'VER TODO',
        r'ICONOGRAFÍA: CARRERA DIURNA.*', r'CARRERA PROFESIONAL', r'CARRERA TÉCNICA',
        r'Descarga AQUÍ'
    ]
    
    # Eliminar formularios de contacto
    texto = re.sub(r'TE INVITAMOS A LLENAR NUESTRO FORMULARIO.*', '', texto, flags=re.IGNORECASE | re.DOTALL)
    
    for pattern in patterns_to_remove:
        texto = re.sub(pattern, '', texto, flags=re.IGNORECASE)

    # Reemplazar múltiples saltos de línea con uno solo
    texto = re.sub(r'(\r\n|\r|\n){2,}', '\n', texto)
    # Reemplazar múltiples espacios
    texto = re.sub(r'[ \t]{2,}', ' ', texto)
    
    # Eliminar espacios en blanco extra al inicio/final de líneas
    texto = '\n'.join([line.strip() for line in texto.split('\n')])
    
    return texto

def procesar_y_chunkear(input_path, output_path):
    print(f"Iniciando limpieza y 'chunking' de '{input_path}'...")
    
    total_chunks = 0
    if not os.path.exists(input_path):
        print(f"Error: No se encontró el archivo '{input_path}'. Ejecuta 'filtrar.py' primero.")
        return

    try:
        with open(input_path, 'r', encoding='utf-8') as f_in:
            data = json.load(f_in)
        
        with open(output_path, 'w', encoding='utf-8') as f_out:
            for item in data:
                url = item.get('url', 'N/A')
                title = item.get('title', 'N/A')
                texto_sucio = item.get('text', '')
                
                if not texto_sucio:
                    continue
                    
                texto_limpio_completo = limpiar_texto(texto_sucio)
                parrafos = texto_limpio_completo.split('\n')
                
                for i, parrafo in enumerate(parrafos):
                    parrafo_limpio = parrafo.strip()
                    # Filtramos párrafos muy cortos o vacíos
                    if len(parrafo_limpio.split()) > MIN_CHUNK_WORDS: 
                        base_id = url.split('/')[-2] if url.split('/')[-2] else "doc"
                        chunk_id = f"{base_id}_{i}"
                        
                        chunk_data = {
                            "id": chunk_id,
                            "source_title": title,
                            "source_url": url,
                            "answer": parrafo_limpio # Este es el 'chunk'
                        }
                        
                        f_out.write(json.dumps(chunk_data, ensure_ascii=False) + '\n')
                        total_chunks += 1

        print("\n--- ¡Procesamiento completado! ---")
        print(f"Se generaron {total_chunks} chunks (párrafos).")
        print(f"Archivo listo para IA guardado en: '{output_path}'")

    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    procesar_y_chunkear(INPUT_FILE, OUTPUT_JSONL)