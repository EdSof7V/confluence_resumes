import os
import requests
from markdown2 import Markdown

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

def create_or_get_page(base_url, username, api_token, space_key, title, content, parent_id=None):
    """Crea una página nueva o actualiza una existente"""
    existing_page_id = check_page_exists(base_url, username, api_token, space_key, title)
    
    url = f"{base_url}/rest/api/content"
    auth = (username, api_token)
    headers = {"Content-Type": "application/json"}
    
    # Convertir Markdown a HTML
    markdowner = Markdown(extras=['fenced-code-blocks', 'tables', 'header-ids'])
    html_content = markdowner.convert(content)
    
    if existing_page_id:
        # Si la página existe, obtener la versión actual
        page_url = f"{url}/{existing_page_id}"
        response = requests.get(page_url, auth=auth)
        response.raise_for_status()
        current_version = response.json()['version']['number']
        
        data = {
            "version": {"number": current_version + 1},
            "title": title,
            "type": "page",
            "body": {
                "storage": {
                    "value": html_content,
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
        data = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": html_content,
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
                with open(file_path, "r", encoding='utf-8') as f:
                    content = f.read()

                # Parsear el nombre del archivo para crear jerarquías
                parts = file.replace(".md", "").split("_")
                if len(parts) < 3:
                    print(f"Skipping file {file} as it doesn't follow the expected format.")
                    continue

                # Descomponer jerarquía
                level1 = parts[0]
                level2 = parts[1].replace("-", " ")
                level3 = parts[2].replace("-", " ")

                print(f"Processing file: {file}")
                print(f"Hierarchy: {level1} -> {level2} -> {level3}")

                try:
                    # Crear o obtener página principal (level 1)
                    level1_content = "# Documentación principal"
                    level1_id = create_or_get_page(
                        base_url, username, api_token, space_key, level1, level1_content
                    )
                    print(f"Level 1 page ID: {level1_id}")

                    # Crear o obtener subpágina (level 2)
                    level2_content = "# Contenido de la plataforma"
                    level2_id = create_or_get_page(
                        base_url, username, api_token, space_key, level2, level2_content, parent_id=level1_id
                    )
                    print(f"Level 2 page ID: {level2_id}")

                    # Crear la página de contenido (level 3) o actualizar si existe
                    level3_id = create_or_get_page(
                        base_url, username, api_token, space_key, level3, content, parent_id=level2_id
                    )
                    print(f"Level 3 page ID: {level3_id}")
                    
                    print(f"Successfully processed {file}")
                    
                except requests.exceptions.RequestException as e:
                    print(f"Error processing {file}: {str(e)}")
                    raise

if __name__ == "__main__":
    main()