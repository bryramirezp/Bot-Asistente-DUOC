import json
import re

def extract_url(text):
    url_pattern = re.compile(r'https?://[^\s\"<>\)]+')
    matches = url_pattern.findall(str(text))
    if matches:
        return matches[0]
    return None

def convert_to_markdown(jsonl_file, output_file):
    md_lines = []
    
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
                
            data = json.loads(line)
            
            md_lines.append(f"## {data['id']}")
            md_lines.append("")
            md_lines.append(f"**ID:** {data['id']}")
            md_lines.append("")
            
            if 'question' in data and 'answer' in data:
                md_lines.append(f"**Pregunta:** {data['question']}")
                md_lines.append("")
                md_lines.append(f"**Respuesta:** {data['answer']}")
                md_lines.append("")
                text_content = data.get('answer', '')
            elif 'text' in data:
                md_lines.append(f"**Texto:** {data['text']}")
                md_lines.append("")
                text_content = data.get('text', '')
            else:
                text_content = ''
            
            if 'keywords' in data and data['keywords']:
                md_lines.append(f"**Keywords:** {', '.join(data['keywords'])}")
                md_lines.append("")
            
            if 'alternative_questions' in data and data['alternative_questions']:
                md_lines.append("**Preguntas Alternativas:**")
                md_lines.append("")
                for q in data['alternative_questions']:
                    md_lines.append(f"- {q}")
                md_lines.append("")
            
            source_value = data.get('source', '')
            url = extract_url(source_value + ' ' + text_content)
            
            md_lines.append(f"**Source:** {url if url else 'No hay fuente'}")
            md_lines.append("")
            md_lines.append("---")
            md_lines.append("")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))

if __name__ == '__main__':
    convert_to_markdown('dataset/dataset_enriquecido.jsonl', 'dataset/dataset2.md')
    print("Conversión completada. Archivo creado: dataset/dataset2.md")

