import json
import os

# --- Configuración ---
INPUT_FILE = 'datasets\combined_dataset.json'
OUTPUT_FILE = 'dataset_filtrado.json'
# Lista de campos a mantener en el nuevo archivo
FIELDS_TO_KEEP = ['url', 'title', 'text']
# ---------------------

def copy_and_select_fields(input_path, output_path):
    """
    Lee el archivo JSON de entrada, selecciona solo los campos clave (url, title, text)
    y guarda el resultado en el archivo de salida.
    """
    print(f"Iniciando la copia y selección de campos clave de '{input_path}'...")

    if not os.path.exists(input_path):
        print(f"Error: No se encontró el archivo '{input_path}'. Asegúrate de que está en la misma carpeta.")
        return

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        total_items = len(data)
        selected_data = []

        for item in data:
            # Crea un nuevo diccionario conteniendo solo los campos seleccionados
            new_item = {key: item.get(key, 'N/A') for key in FIELDS_TO_KEEP}
            selected_data.append(new_item)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(selected_data, f, indent=2, ensure_ascii=False)
            
        print("\n--- ¡Copia y selección de campos completada! ---")
        print(f"Items totales leídos: {total_items}")
        print(f"Campos mantenidos: {FIELDS_TO_KEEP}")
        print(f"Archivo '{OUTPUT_FILE}' creado con éxito.")

    except json.JSONDecodeError:
        print(f"Error: El archivo '{input_path}' no es un JSON válido.")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    copy_and_select_fields(INPUT_FILE, OUTPUT_FILE)