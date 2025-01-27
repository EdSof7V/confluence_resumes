import os
import requests
import base64

def print_environment_variables():
    """Imprime las variables de entorno sin enmascarar"""
    secrets = {
        "CONFLUENCE_BASE_URL": os.environ.get("CONFLUENCE_BASE_URL", ""),
        "CONFLUENCE_USERNAME": os.environ.get("CONFLUENCE_USERNAME", ""),
        "CONFLUENCE_API_TOKEN": os.environ.get("CONFLUENCE_API_TOKEN", ""),
        "SPACE_KEY": os.environ.get("SPACE_KEY", "")
    }
    
    print("\n=== Variables de Entorno ===")
    for key, value in secrets.items():
        print(f"{key}: {value}")
    print("========================\n")

def test_confluence_connection(base_url, username, api_token):
    """Prueba la conexión a Confluence y muestra información detallada en caso de error"""
    url = f"{base_url}/rest/api/content"
    
    # Crear el header de autorización manualmente para debugging
    auth_string = f"{username}:{api_token}"
    auth_bytes = auth_string.encode('ascii')
    base64_auth = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        "Authorization": f"Basic {base64_auth}",
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        print("\n=== Test de Conexión ===")
        print(f"URL: {url}")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 401:
            print("\nError de Autenticación detectado:")
            print("1. Verifica que el username sea el correo completo")
            print("2. Confirma que el API token sea válido")
            print("3. Asegúrate que la URL de Confluence sea correcta")
            print(f"4. Auth Header (for debugging): Basic {base64_auth}")
        
        response.raise_for_status()
        print("Conexión exitosa!")
        print("========================\n")
        
    except requests.exceptions.RequestException as e:
        print(f"\nError de conexión: {str(e)}")
        print("========================\n")
        raise

def create_confluence_page(base_url, username, api_token, space_key, title, content, parent_id=None):
    url = f"{base_url}/rest/api/content"
    
    # Crear el header de autorización manualmente
    auth_string = f"{username}:{api_token}"
    auth_bytes = auth_string.encode('ascii')
    base64_auth = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        "Authorization": f"Basic {base64_auth}",
        "Content-Type": "application/json",
    }
    
    data = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {
            "storage": {
                "value": content,
                "representation": "storage",
            }
        },
    }
    if parent_id:
        data["ancestors"] = [{"id": parent_id}]

    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code != 200:
        print(f"\nError en create_confluence_page:")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        print(f"Request URL: {url}")
        print(f"Request Headers: {headers}")
        print(f"Request Data: {data}")
    
    response.raise_for_status()
    return response.json()["id"]

def main():
    # Imprimir variables de entorno
    print_environment_variables()
    
    # Leer variables de entorno
    base_url = os.environ["CONFLUENCE_BASE_URL"].rstrip('/')  # Eliminar trailing slash si existe
    username = os.environ["CONFLUENCE_USERNAME"]
    api_token = os.environ["CONFLUENCE_API_TOKEN"]
    space_key = os.environ["SPACE_KEY"]

    # Probar conexión antes de procesar archivos
    test_confluence_connection(base_url, username, api_token)

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
                level3 = parts[2].replace("-", " ")  # Ej: "Databricks 01052025"

                print(f"Processing file: {file}")
                print(f"Hierarchy: {level1} -> {level2} -> {level3}")

                try:
                    # Crear páginas en Confluence
                    print("Creating level 1 page...")
                    level1_id = create_confluence_page(
                        base_url, username, api_token, space_key, level1, f"<p>{level1} summary</p>"
                    )

                    print("Creating level 2 page...")
                    level2_id = create_confluence_page(
                        base_url, username, api_token, space_key, level2, f"<p>{level2} summary</p>", parent_id=level1_id
                    )

                    print("Creating level 3 page...")
                    create_confluence_page(
                        base_url, username, api_token, space_key, level3, f"<p>{content}</p>", parent_id=level2_id
                    )
                    print(f"Uploaded hierarchy for {file} successfully.")
                    
                except requests.exceptions.RequestException as e:
                    print(f"Error uploading {file}: {str(e)}")
                    raise  # Re-raise the exception to fail the workflow

if __name__ == "__main__":
    main()