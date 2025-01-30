import os
import requests
from markdown2 import Markdown
import re

def check_page_exists(base_url, username, api_token, space_key, title):
    """Verifica si una página existe y retorna su ID si existe"""
    url = f"{base_url}/rest/api/content"
    auth = (username, api_token)
    params = {
        'spaceKey': space_key,
        'title': title,
        'expand': 'version'
    }
    
    response = requests.get(url, auth=auth, params=params)
    response.raise_for_status()
    
    results = response.json().get('results', [])
    return results[0]['id'] if results else None

def convert_md_to_confluence(content):
    """Convierte Markdown a formato Confluence"""
    markdowner = Markdown(extras=['fenced-code-blocks', 'tables', 'header-ids'])
    
    # Reemplazos para paneles de información
    content = content.replace("::: info", "<ac:structured-macro ac:name=\"info\"><ac:rich-text-body>")
    content = content.replace(":::", "</ac:rich-text-body></ac:structured-macro>")
    
    # Convertir checkboxes
    content = content.replace("- [x]", "✅")
    content = content.replace("- [ ]", "⬜")
    
    # Convertir bloques de código
    def code_replacer(match):
        language = match.group(1) if match.group(1) else ''
        code = match.group(2)
        return f"<ac:structured-macro ac:name=\"code\"><ac:parameter ac:name=\"language\">{language}</ac:parameter><ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body></ac:structured-macro>"
    
    content = re.sub(r'```(\w+)?\n(.*?)\n```', code_replacer, content, flags=re.DOTALL)
    
    # Convertir a HTML con formato Confluence
    html_content = markdowner.convert(content)
    return html_content

def create_or_update_page(base_url, username, api_token, space_key, title, content, parent_id=None):
    """Crea una página nueva o actualiza una existente"""
    existing_page_id = check_page_exists(base_url, username, api_token, space_key, title)
    
    url = f"{base_url}/rest/api/content"
    auth = (username, api_token)
    headers = {"Content-Type": "application/json"}
    
    # Convertir Markdown a formato Confluence
    confluence_content = convert_md_to_confluence(content)
    
    if existing_page_id:
        # Obtener contenido actual para comparar
        page_url = f"{url}/{existing_page_id}?expand=body.storage,version"
        response = requests.get(page_url, auth=auth)
        response.raise_for_status()
        current_data = response.json()
        current_version = current_data['version']['number']
        current_content = current_data['body']['storage']['value']
        
        # Solo actualizar si el contenido ha cambiado
        if current_content != confluence_content:
            print(f"Actualizando página existente: {title}")
            data = {
                "version": {"number": current_version + 1},
                "title": title,
                "type": "page",
                "body": {
                    "storage": {
                        "value": confluence_content,
                        "representation": "storage"
                    }
                }
            }
            if parent_id:
                data["ancestors"] = [{"id": parent_id}]
                
            response = requests.put(
                f"{url}/{existing_page_id}",
                json=data,
                auth=auth,
                headers=headers
            )
            response.raise_for_status()
        else:
            print(f"No hay cambios en la página: {title}")
        return existing_page_id
    else:
        print(f"Creando nueva página: {title}")
        data = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": confluence_content,
                    "representation": "storage"
                }
            }
        }
        if parent_id:
            data["ancestors"] = [{"id": parent_id}]
            
        response = requests.post(
            url,
            json=data,
            auth=auth,
            headers=headers
        )
        response.raise_for_status()
        return response.json()["id"]

def process_markdown_file(file_path, base_url, username, api_token, space_key):
    """Procesa un archivo markdown y lo sube a Confluence manteniendo la jerarquía"""
    # Extraer nombre del archivo sin extensión
    file_name = os.path.basename(file_path).replace('.md', '')
    
    # Separar los niveles por guion bajo
    levels = file_name.split('_')
    
    if len(levels) < 2:
        print(f"Ignorando {file_path}: debe tener al menos dos niveles separados por _")
        return
    
    # Leer contenido del archivo
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Crear o actualizar páginas en orden jerárquico
    parent_id = None
    for i, level in enumerate(levels):
        # Formatear título reemplazando guiones por espacios
        title = level.replace('-', ' ')
        
        if i == len(levels) - 1:
            # Es la última página (contenido real)
            page_id = create_or_update_page(base_url, username, api_token, space_key, title, content, parent_id)
        else:
            # Es una página padre
            template_content = f"<h1>{title}</h1>\n<p>Página de organización para {title}</p>"
            page_id = create_or_update_page(base_url, username, api_token, space_key, title, template_content, parent_id)
        
        parent_id = page_id
        print(f"Procesado nivel {i+1}: {title} (ID: {page_id})")

def main():
    # Leer variables de entorno
    base_url = os.environ["CONFLUENCE_BASE_URL"].rstrip('/')
    username = os.environ["CONFLUENCE_USERNAME"]
    api_token = os.environ["CONFLUENCE_API_TOKEN"]
    space_key = os.environ["SPACE_KEY"]

    # Buscar archivos .md en el repositorio
    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                print(f"\nProcesando archivo: {file_path}")
                try:
                    process_markdown_file(file_path, base_url, username, api_token, space_key)
                    print(f"✅ Archivo procesado exitosamente: {file_path}")
                except Exception as e:
                    print(f"❌ Error procesando {file_path}: {str(e)}")
                    raise

if __name__ == "__main__":
    main()