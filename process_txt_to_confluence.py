import os
import requests

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
    
    if existing_page_id:
        # Si la página existe, obtener la versión actual
        page_url = f"{url}/{existing_page_id}"
        response = requests.get(page_url, auth=auth)
        response.raise_for_status()
        current_version = response.json()['version']['number']
        
        # Actualizar la página existente
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
        # Crear nueva página
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

def update_page_content(base_url, username, api_token, page_id, new_content):
    """Actualiza el contenido de una página existente"""
    url = f"{base_url}/rest/api/content/{page_id}"
    auth = (username, api_token)
    
    # Obtener la versión actual
    response = requests.get(url, auth=auth)
    response.raise_for_status()
    current_version = response.json()['version']['number']
    current_content = response.json()['body']['storage']['value']
    
    # Agregar el nuevo contenido al existente
    updated_content = current_content + "\n" + new_content
    
    # Actualizar la página
    data = {
        "version": {"number": current_version + 1},
        "title": response.json()['title'],
        "type": "page",
        "body": {
            "storage": {
                "value": updated_content,
                "representation": "storage"
            }
        }
    }
    
    response = requests.put(
        url,
        json=data,
        auth=(username, api_token),
        headers={"Content-Type": "application/json"}
    )
    response.raise_for_status()

def main():
    # Leer variables de entorno
    base_url = os.environ["CONFLUENCE_BASE_URL"].rstrip('/')
    username = os.environ["CONFLUENCE_USERNAME"]
    api_token = os.environ["CONFLUENCE_API_TOKEN"]
    space_key = os.environ["SPACE_KEY"]

    # Buscar archivos .txt en el repositorio
    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith(".txt"):
                file_path = os.path.join(root, file)
                with open(file_path, "r") as f:
                    content = f.read()

                # Parsear el nombre del archivo para crear jerarquías
                parts = file.replace(".txt", "").split("_")
                if len(parts) < 3:
                    print(f"Skipping file {file} as it doesn't follow the expected format.")
                    continue

                # Descomponer jerarquía
                level1 = parts[0]  # Ej: "BCP"
                level2 = parts[1].replace("-", " ")  # Ej: "Data Platform"
                level3 = parts[2].replace("-", " ")  # Ej: "Databricks 31 10 2024"

                print(f"Processing file: {file}")
                print(f"Hierarchy: {level1} -> {level2} -> {level3}")

                try:
                    # Crear o obtener página principal (level 1)
                    level1_content = "<p>Documentación principal</p>"
                    level1_id = create_or_get_page(
                        base_url, username, api_token, space_key, level1, level1_content
                    )
                    print(f"Level 1 page ID: {level1_id}")

                    # Crear o obtener subpágina (level 2)
                    level2_content = "<p>Contenido de la plataforma</p>"
                    level2_id = create_or_get_page(
                        base_url, username, api_token, space_key, level2, level2_content, parent_id=level1_id
                    )
                    print(f"Level 2 page ID: {level2_id}")

                    # Crear la página de contenido (level 3) o actualizar si existe
                    level3_content = f"<p>{content}</p>"
                    level3_id = create_or_get_page(
                        base_url, username, api_token, space_key, level3, level3_content, parent_id=level2_id
                    )
                    print(f"Level 3 page ID: {level3_id}")
                    
                    print(f"Successfully processed {file}")
                    
                except requests.exceptions.RequestException as e:
                    print(f"Error processing {file}: {str(e)}")
                    raise

if __name__ == "__main__":
    main()