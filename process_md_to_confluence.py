import os
import requests
import markdown
import re
from bs4 import BeautifulSoup
from datetime import datetime
import base64
import json

def verify_credentials(base_url, username, api_token):
    """Verifica las credenciales de Confluence"""
    try:
        # Intentar obtener información del usuario actual
        auth_url = f"{base_url}/rest/api/user/current"
        response = requests.get(
            auth_url,
            auth=(username, api_token),
            headers={"Accept": "application/json"}
        )
        
        if response.status_code == 200:
            user_info = response.json()
            print(f"Autenticación exitosa como: {user_info.get('displayName', username)}")
            return True
        elif response.status_code == 401:
            print("Error de autenticación: Credenciales inválidas")
            return False
        elif response.status_code == 403:
            print("Error de permisos: El token no tiene los permisos necesarios")
            return False
        else:
            print(f"Error desconocido: Status code {response.status_code}")
            return False
    except Exception as e:
        print(f"Error al verificar credenciales: {str(e)}")
        return False

def check_space_access(base_url, username, api_token, space_key):
    """Verifica el acceso al espacio de Confluence"""
    try:
        space_url = f"{base_url}/rest/api/space/{space_key}"
        response = requests.get(
            space_url,
            auth=(username, api_token),
            headers={"Accept": "application/json"}
        )
        
        if response.status_code == 200:
            space_info = response.json()
            print(f"Acceso confirmado al espacio: {space_info.get('name', space_key)}")
            return True
        else:
            print(f"Error al acceder al espacio {space_key}: Status code {response.status_code}")
            return False
    except Exception as e:
        print(f"Error al verificar acceso al espacio: {str(e)}")
        return False

def create_or_update_page(base_url, username, api_token, space_key, title, content, parent_id=None):
    """Crea o actualiza una página en Confluence"""
    try:
        # Verificar si la página existe
        url = f"{base_url}/rest/api/content"
        auth = (username, api_token)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Buscar página existente
        search_params = {
            'spaceKey': space_key,
            'title': title,
            'expand': 'version'
        }
        
        search_response = requests.get(url, auth=auth, headers=headers, params=search_params)
        search_response.raise_for_status()
        
        results = search_response.json().get('results', [])
        
        if results:
            # Actualizar página existente
            page_id = results[0]['id']
            version = results[0]['version']['number']
            
            update_data = {
                "version": {"number": version + 1},
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
                update_data["ancestors"] = [{"id": parent_id}]
            
            update_response = requests.put(
                f"{url}/{page_id}",
                json=update_data,
                auth=auth,
                headers=headers
            )
            update_response.raise_for_status()
            return page_id
            
        else:
            # Crear nueva página
            create_data = {
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
                create_data["ancestors"] = [{"id": parent_id}]
            
            create_response = requests.post(
                url,
                json=create_data,
                auth=auth,
                headers=headers
            )
            create_response.raise_for_status()
            return create_response.json()["id"]
            
    except requests.exceptions.RequestException as e:
        print(f"Error en la operación de página: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"Respuesta del servidor: {e.response.text}")
        raise

def main():
    # Obtener variables de entorno
    base_url = os.environ.get("CONFLUENCE_BASE_URL", "").rstrip('/')
    username = os.environ.get("CONFLUENCE_USERNAME", "")
    api_token = os.environ.get("CONFLUENCE_API_TOKEN", "")
    space_key = os.environ.get("SPACE_KEY", "")

    # Verificar variables requeridas
    if not all([base_url, username, api_token, space_key]):
        raise ValueError("Faltan variables de entorno requeridas")

    print(f"\nIniciando proceso de carga a Confluence: {datetime.now()}")
    print(f"URL Base: {base_url}")
    print(f"Usuario: {username}")
    print(f"Space Key: {space_key}")

    # Verificar credenciales y acceso
    if not verify_credentials(base_url, username, api_token):
        raise Exception("Fallo en la verificación de credenciales")
        
    if not check_space_access(base_url, username, api_token, space_key):
        raise Exception("Fallo en la verificación de acceso al espacio")

    # Procesar archivos MD
    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                print(f"\nProcesando archivo: {file_path}")

                try:
                    with open(file_path, "r", encoding='utf-8') as f:
                        content = f.read()

                    # Convertir MD a formato Confluence
                    confluence_content = convert_md_to_confluence(content)

                    # Parsear nombre del archivo
                    parts = file.replace(".md", "").split("_")
                    if len(parts) < 3:
                        print(f"Omitiendo {file}: formato inválido")
                        continue

                    level1 = parts[0]
                    level2 = parts[1].replace("-", " ")
                    level3 = parts[2].replace("-", " ")

                    print(f"Creando/actualizando jerarquía: {level1} -> {level2} -> {level3}")

                    # Crear estructura jerárquica
                    try:
                        level1_id = create_or_update_page(
                            base_url, username, api_token, space_key,
                            level1, "<p>Documentación principal</p>"
                        )
                        print(f"Página nivel 1 creada/actualizada: {level1}")

                        level2_id = create_or_update_page(
                            base_url, username, api_token, space_key,
                            level2, "<p>Contenido de la plataforma</p>",
                            parent_id=level1_id
                        )
                        print(f"Página nivel 2 creada/actualizada: {level2}")

                        level3_id = create_or_update_page(
                            base_url, username, api_token, space_key,
                            level3, confluence_content,
                            parent_id=level2_id
                        )
                        print(f"Página nivel 3 creada/actualizada: {level3}")

                    except Exception as e:
                        print(f"Error al crear/actualizar páginas: {str(e)}")
                        raise

                except Exception as e:
                    print(f"Error procesando {file}: {str(e)}")
                    raise

if __name__ == "__main__":
    main()