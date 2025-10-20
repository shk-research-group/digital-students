from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
from langchain_community.document_loaders.llmsherpa import LLMSherpaFileLoader
from langchain_community.document_loaders import UnstructuredPowerPointLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from langchain_qdrant import Qdrant
import concurrent.futures

# Configure upload folder
UPLOAD_FOLDER = 'tmp/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

llmsherpa_api_url = "http://llmsherpa.service.consul:15001/api/parseDocument?renderFormat=all"
qdrant_url = "http://qdrant.service.consul:16333"
qdrant_api_key = "qdrant"
embedding_model_name = "BAAI/bge-base-en-v1.5"
embedding_dimension = 768
collection_prefix = "student_bots"
model_name_HuggingFace_768 = "sentence-transformers/all-mpnet-base-v2"
# ollama_embedding_model_name = "chroma/all-minilm-l6-v2-f32"
ollama_embedding_model_name = "nomic-embed-text"

# Supported file extensions
SUPPORTED_EXTENSIONS = ['.pdf', '.pptx']

def get_embedding_HuggingFace(model_name):
    model_kwargs = {'device': 'cpu'}
    encode_kwargs = {'normalize_embeddings': False}
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )
    return embeddings

def get_embedding_Ollama(model_name):
    from langchain_community.embeddings import OllamaEmbeddings
    embeddings = OllamaEmbeddings(
        model=model_name,
        base_url="http://192.168.0.108:11434"  # Update with your Ollama service URL
    )
    return embeddings

def store_to_qdrant(docs, embeddings, metadata):
    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    # collection_name = "student-bots-pdf-20250112"
    # collection_name = "student-bots-pdf-20250216"
    # collection_name = "student-bots-ollama-pdf-20250216"
    collection_name = "student-bots-ollama-pdf-vimo-20250316"

    # Check if collection exists, if not, create it
    collections = client.get_collections().collections
    if not any(collection.name == collection_name for collection in collections):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=rest.VectorParams(size=embedding_dimension, distance=rest.Distance.COSINE),
        )

    qdrant = Qdrant(
        client=client,
        collection_name=collection_name,
        embeddings=embeddings,
    )

    # Add metadata to each document
    for doc in docs:
        doc.metadata.update({
            'file_id': metadata['id'],
            'lecture_id': metadata['lecture_id'],
            'student_id': metadata['student_id'],
            'filename': metadata['filename']
        })
    
    # Add documents regardless of collection status
    qdrant.add_documents(docs)
    print(f"Added {len(docs)} documents to collection {collection_name}")

def load_document(file_path, file_extension):
    """
    Load a document based on its file extension
    Args:
        file_path (str): Path to the file
        file_extension (str): File extension (e.g., '.pdf', '.pptx')
    Returns:
        list: List of document objects
    """
    if file_extension.lower() == '.pdf':
        loader = LLMSherpaFileLoader(
            file_path=file_path,
            new_indent_parser=True,
            apply_ocr=True,
            strategy="sections",
            llmsherpa_api_url=llmsherpa_api_url,
        )
    elif file_extension.lower() == '.pptx':
        loader = UnstructuredPowerPointLoader(file_path)
    else:
        raise ValueError(f"Unsupported file extension: {file_extension}")
    
    return loader.load()

def process_single_file(file_info):
    """
    Process a single document file
    Args:
        file_info (tuple): (file_path, filename, metadata)
    Returns:
        dict: Processing result for the file
    """
    file_path, filename, metadata = file_info
    print(f"Processing file: {filename}")
    
    try:
        file_extension = os.path.splitext(filename)[1].lower()
        print(f"{filename}: Loading file and converting to text...")
        
        docs = load_document(file_path, file_extension)
        
        print(f"{filename}: Splitting text into chunks...")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2048, chunk_overlap=128)
        docs = text_splitter.split_documents(docs)
        
        print(f"{filename}: Storing documents to Qdrant...")
        store_to_qdrant(docs, get_embedding_Ollama(ollama_embedding_model_name), metadata)
        
        result = {
            "filename": filename,
            "status": "success",
            "message": f"File {filename} processed successfully",
            "metadata": metadata
        }
        print(f"File {filename} processed successfully.\n")
        
    except Exception as e:
        result = {
            "filename": filename,
            "status": "error",
            "message": f"Error processing {filename}: {str(e)}",
            "metadata": metadata
        }
        print(f"Error processing {filename}: {str(e)}\n")
    
    return result

def process_document_folder(folder_path, metadata_list=None, max_workers=5):
    """
    Process all supported document files in the given folder in parallel
    Args:
        folder_path (str): Path to folder containing document files
        metadata_list (list, optional): List of metadata dictionaries corresponding to each file.
        max_workers (int): Maximum number of parallel processes
    Returns:
        list: List of processing results with success/failure status for each file
    """
    # Get all files with supported extensions
    document_files = []
    for f in os.listdir(folder_path):
        ext = os.path.splitext(f)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            document_files.append(f)
    
    file_infos = []
    
    for idx, filename in enumerate(document_files):
        file_path = os.path.join(folder_path, filename)
        
        # Get or create metadata for this file
        if metadata_list and idx < len(metadata_list):
            metadata = metadata_list[idx]
        else:
            metadata = {
                'id': str(idx),
                'filename': filename,
                'lecture_id': '',
                'student_id': ''
            }
        
        file_infos.append((file_path, filename, metadata))
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(process_single_file, file_info): file_info for file_info in file_infos}
        
        for future in concurrent.futures.as_completed(future_to_file):
            result = future.result()
            results.append(result)
    
    return results

@app.route("/ingest-file", methods=['POST'])
def ingest_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file and file_extension in SUPPORTED_EXTENSIONS:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Get metadata from form data
        metadata = {
            'id': request.form.get('id', ''),
            'filename': request.form.get('filename', ''),
            'lecture_id': request.form.get('lecture_id', ''),
            'student_id': request.form.get('student_id', '')
        }
        
        # Process the single file using the folder processing function
        results = process_document_folder(
            app.config['UPLOAD_FOLDER'],
            metadata_list=[metadata]
        )
        
        # Return the result for the single file
        if results[0]['status'] == 'success':
            return jsonify(results[0]), 200
        else:
            return jsonify({"error": results[0]['message']}), 500
    else:
        return jsonify({"error": f"Invalid file format. Please upload one of the supported file types: {', '.join(SUPPORTED_EXTENSIONS)}"}), 400

# Example usage of the folder processing function:
"""
# Process all documents in a folder
folder_path = "path/to/document/folder"
metadata_list = [
    {
        'id': '1',
        'filename': 'doc1.pdf',
        'lecture_id': 'lecture1',
        'student_id': 'student1'
    },
    {
        'id': '2',
        'filename': 'presentation.pptx',
        'lecture_id': 'lecture2',
        'student_id': 'student2'
    }
]
results = process_document_folder(folder_path, metadata_list)
for result in results:
    print(f"{result['filename']}: {result['status']}")
"""

if __name__ == "__main__":
    # Process all documents in a folder
    folder_path = "/Users/khiemfle/Downloads/archives/kinhtevimo-pdf"  # You can change this path as needed
    
    print(f"Processing document files in folder: {folder_path}")
    print(f"Processing 5 files in parallel...\n")
    
    results = process_document_folder(folder_path, max_workers=5)
    
    print("\nProcessing Results:")
    for result in results:
        print(f"File: {result['filename']}")
        print(f"Status: {result['status']}")
        print(f"Message: {result['message']}")
        print("---")