import os
import requests
import markdown
import re
from bs4 import BeautifulSoup
from datetime import datetime

def convert_md_to_confluence(content):
    """Convierte Markdown a formato Confluence Storage"""
    # Convertir MD a HTML básico
    html = markdown.markdown(content, extensions=[
        'fenced_code',
        'tables',
        'nl2br',
        'attr_list'
    ])
    
    # Crear objeto BeautifulSoup para manipular el HTML
    soup = BeautifulSoup(html, 'html.parser')
    
    # Convertir bloques de código
    for code_block in soup.find_all('pre'):
        code = code_block.find('code')
        if code:
            language = ''
            if 'class' in code.attrs:
                for class_name in code['class']:
                    if class_name.startswith('language-'):
                        language = class_name.replace('language-', '')
            
            ac_block = soup.new_tag('ac:structured-macro')
            ac_block['ac:name'] = 'code'
            
            if language:
                param = soup.new_tag('ac:parameter')
                param['ac:name'] = 'language'
                param.string = language
                ac_block.append(param)
            
            cdata = soup.new_tag('ac:plain-text-body')
            cdata.string = code.get_text()
            ac_block.append(cdata)
            
            code_block.replace_with(ac_block)
    
    # Convertir imágenes
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if src:
            ac_image = soup.new_tag('ac:image')
            ri_attr = soup.new_tag('ri:attachment')
            ri_attr['ri:filename'] = os.path.basename(src)
            ac_image.append(ri_attr)
            img.replace_with(ac_image)
    
    # Convertir bloques de información
    info_blocks = {
        'info': 'info',
        'note': 'note',
        'warning': 'warning',
        'tip': 'tip'
    }
    
    for block_type, macro_name in info_blocks.items():
        pattern = rf'::: {block_type}\n(.*?)\n:::'
        content = re.sub(pattern, 
                        rf'<ac:structured-macro ac:name="{macro_name}">'
                        r'<ac:rich-text-body>\1</ac:rich-text-body>'
                        r'</ac:structured-macro>', 
                        content, 
                        flags=re.DOTALL)

    return str(soup)

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

def create_or_update_page(base_url, username, api_token, space_key, title, content, parent_id=None):
    """Crea una página nueva o actualiza una existente"""
    existing_page_id = check_page_exists(base_url, username, api_token, space_key, title)
    
    url = f"{base_url}/rest/api/content"
    auth = (username, api_token)
    headers = {"Content-Type": "application/json"}
    
    if existing_page_id:
        # Obtener versión actual
        page_url = f"{url}/{existing_page_id}"
        response = requests.get(page_url, auth=auth)
        response.raise_for_status()
        current_version = response.json()['version']['number']
        
        # Actualizar página
        data = {
            "version": {"number": current_version + 1},
            "title": title,
            "type": "page",
            "body": {
                "storage": {
                    "value": content,
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
        return existing_page_id
    else:
        # Crear página nueva
        data = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": content,
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

def main():
    # Configuración desde variables de entorno
    base_url = os.environ["CONFLUENCE_BASE_URL"].rstrip('/')
    username = os.environ["CONFLUENCE_USERNAME"]
    api_token = os.environ["CONFLUENCE_API_TOKEN"]
    space_key = os.environ["SPACE_KEY"]

    # Log de inicio
    print(f"Starting MD to Confluence process at {datetime.now()}")

    # Buscar archivos .md
    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                print(f"\nProcessing file: {file_path}")

                try:
                    # Leer contenido del archivo
                    with open(file_path, "r", encoding='utf-8') as f:
                        content = f.read()

                    # Convertir MD a formato Confluence
                    confluence_content = convert_md_to_confluence(content)

                    # Parsear nombre del archivo para jerarquía
                    parts = file.replace(".md", "").split("_")
                    if len(parts) < 3:
                        print(f"Skipping {file}: Invalid format")
                        continue

                    # Crear estructura jerárquica
                    level1 = parts[0]
                    level2 = parts[1].replace("-", " ")
                    level3 = parts[2].replace("-", " ")

                    print(f"Creating/updating hierarchy: {level1} -> {level2} -> {level3}")

                    # Crear/actualizar páginas
                    level1_id = create_or_update_page(
                        base_url, username, api_token, space_key,
                        level1, "<p>Documentación principal</p>"
                    )

                    level2_id = create_or_update_page(
                        base_url, username, api_token, space_key,
                        level2, "<p>Contenido de la plataforma</p>",
                        parent_id=level1_id
                    )

                    level3_id = create_or_update_page(
                        base_url, username, api_token, space_key,
                        level3, confluence_content,
                        parent_id=level2_id
                    )

                    print(f"Successfully processed {file}")

                except Exception as e:
                    print(f"Error processing {file}: {str(e)}")
                    raise

    print(f"\nProcess completed at {datetime.now()}")

if __name__ == "__main__":
    main()