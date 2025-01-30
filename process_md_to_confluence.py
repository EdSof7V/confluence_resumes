import os
import requests
from markdown2 import Markdown

def convert_md_to_confluence(content):
    """Convierte Markdown a formato Confluence"""
    # Primero convertimos el Markdown básico a HTML
    markdowner = Markdown(extras=['fenced-code-blocks', 'tables', 'header-ids'])
    
    # Reemplazos específicos para Confluence
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
    
    import re
    content = re.sub(r'```(\w+)?\n(.*?)\n```', code_replacer, content, flags=re.DOTALL)
    
    # Convertir a HTML
    html_content = markdowner.convert(content)
    
    # Ajustes finales para Confluence
    html_content = html_content.replace('<h1>', '<h1><strong>')
    html_content = html_content.replace('</h1>', '</strong></h1>')
    
    return html_content

def create_or_get_page(base_url, username, api_token, space_key, title, content, parent_id=None):
    """Crea una página nueva o actualiza una existente"""
    existing_page_id = check_page_exists(base_url, username, api_token, space_key, title)
    
    url = f"{base_url}/rest/api/content"
    auth = (username, api_token)
    headers = {"Content-Type": "application/json"}
    
    # Convertir Markdown a formato Confluence
    confluence_content = convert_md_to_confluence(content)
    
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
        return existing_page_id
    else:
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