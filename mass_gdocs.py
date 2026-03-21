import os
import json
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
# Put your path to the JSON here
SERVICE_ACCOUNT_FILE = r'C:\Users\Utilisateur\Documents\Helium\credentials.json'

PROJECTS = [
    "AEther", "Automatons", "Kapok", "Iroko", "Verbose", "Vault", "TokenWise",
    "Helium", "Astral", "Charmed", "CADAM", "OpenQuant", "Sagittarius", 
    "Project-Dirac", "Playground", "Echo", "Dissect", "Datalint", "BloomDB",
    "NeuroDose", "NeuralPaper", "NeuralDSL", "OpenMind", "NeuralDBG",
    "kuro-rules", "Lemniscate-world", "Neural-Research", "Neural-Aquarium",
    "Neural-Again", "Metatron"
]

def get_service():
    """Authenticates and returns the Google Docs and Drive services."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    docs_service = build('docs', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    return docs_service, drive_service

def create_project_document(drive_service, title):
    """
    Creates a new Google Doc mapped to a specific folder.
    Returns the document ID.
    """
    file_metadata = {
        'name': title,
        'mimeType': 'application/vnd.google-apps.document'
    }
    
    file = drive_service.files().create(body=file_metadata, fields='id').execute()
    doc_id = file.get('id')
    
    # Share it with anyone having the link as a writer
    permission = {
        'type': 'anyone',
        'role': 'writer'
    }
    drive_service.permissions().create(fileId=doc_id, body=permission).execute()
    return doc_id

if __name__ == '__main__':
    doc_mapping = {}
    MAPPING_FILE = r'C:\Users\Utilisateur\Documents\kuro-rules\gdocs_mapping.json'
    
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, 'r') as f:
            doc_mapping = json.load(f)
            
    print("Starting Mass GDocs Generation...")
    
    try:
        _, drive_service = get_service()
        
        for project in PROJECTS:
            if project in doc_mapping:
                print(f"Skipping {project}: Already exists at {doc_mapping[project]}")
                continue
                
            title = f"{project} - IA Session Logs"
            print(f"Creating doc for: {project}...")
            
            try:
                doc_id = create_project_document(drive_service, title)
                link = f"https://docs.google.com/document/d/{doc_id}/edit"
                
                doc_mapping[project] = link
                print(f" -> Success! {link}")
                
                # Save mapping step by step in case it crashes on Drive quotas
                with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
                    json.dump(doc_mapping, f, indent=4)
                    
                time.sleep(2) # Avoid hitting API limits
            except Exception as e:
                print(f" -> Error creating {project}: {e}")
                print("Stopping generation due to error (Likely Quota). Try again later.")
                break
                
        print("\nAll processing finished. The mapping is saved in gdocs_mapping.json!")
    except Exception as e:
        print(f"FATAL ERROR Initializing Google API: {e}. Check your credentials.json file or connection.")
