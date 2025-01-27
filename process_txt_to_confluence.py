import os
import requests

def print_masked_secrets():
    """Imprime las variables de secretos de forma segura, mostrando solo los primeros y últimos caracteres."""
    secrets = {
        "CONFLUENCE_BASE_URL": os.environ.get("CONFLUENCE_BASE_URL", ""),
        "CONFLUENCE_USERNAME": os.environ.get("CONFLUENCE_USERNAME", ""),
        "CONFLUENCE_API_TOKEN": os.environ.get("CONFLUENCE_API_TOKEN", ""),
        "SPACE_KEY": os.environ.get("SPACE_KEY", "")
    }
    
    print("\n=== Variables de Entorno ===")
    for key, value in secrets.items():
        if value:
            # Muestra solo los primeros 4 y últimos 4 caracteres si el valor es lo suficientemente largo
            masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:] if len(value) > 8 else "****"
            print(f"{key}: {masked_value}")
        else:
            print(f"{key}: No configurado")
    print("========================\n")

def create_confluence_page(base_url, username, api_token, space_key, title, content, parent_id=None):
    url = f"{base_url}/rest/api/content"
    headers = {
        "Authorization": f"Basic {requests.auth._basic_auth_str(username, api_token)}",
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
    response.raise_for_status()
    return response.json()["id"]

def main():
    # Imprimir variables de secretos de forma segura
    print_masked_secrets()
    
    # Leer variables de entorno
    base_url = os.environ["CONFLUENCE_BASE_URL"]
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
                    continue

if __name__ == "__main__":
    main()