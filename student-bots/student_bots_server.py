from flask import Flask, request, jsonify
from adhoc_metrics.metrics_exporter import MetricsExporter
import os
from threading import Thread
from werkzeug.utils import secure_filename
from langchain_community.document_loaders.llmsherpa import LLMSherpaFileLoader
from langchain_qdrant import QdrantVectorStore
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_qdrant import Qdrant
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from langchain.retrievers import ContextualCompressionRetriever
from langchain.prompts import PromptTemplate
from functools import lru_cache
import hashlib
import logging
import traceback
from ragatouille import RAGPretrainedModel
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from langchain_huggingface import HuggingFaceEmbeddings
from langfuse.callback import CallbackHandler

# Set up logging at the top of the file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

llmsherpa_api_url = "http://llmsherpa.service.consul:15001/api/parseDocument?renderFormat=all"
qdrant_url = "http://qdrant.service.consul:16333"
qdrant_api_key = "qdrant"
embedding_model_name = "BAAI/bge-base-en-v1.5"
embedding_dimension = 768
collection_prefix = "student_bots"
model_name_HuggingFace_768 = "sentence-transformers/all-mpnet-base-v2"

# Add this at the top level with other global variables
qa_cache = {}

app, metrics_exporter, tracer = MetricsExporter.initialize_flask_app(
    service_key="student-bots-service",
    otlp_endpoint="http://10.77.0.12:14317",
    service_port=19191,
    push_interval=10
)

def get_langfuse_callback() -> CallbackHandler:
    """Get a configured Langfuse callback handler."""
    return CallbackHandler(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY", "pk-lf-54c0f131-7e61-434c-a058-057f4846a99b"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY", "sk-lf-73bab8d9-c024-4d82-8185-cbe0a3bb58fc"),
        host=os.getenv("LANGFUSE_HOST", "http://langfuse.service.consul:23002/")
    )

# Configure upload folder
UPLOAD_FOLDER = 'tmp/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def fast_embedding(model_name):
    embeddings = FastEmbedEmbeddings(model_name=model_name)
    return embeddings

model_name_HuggingFace_768 = "sentence-transformers/all-mpnet-base-v2"

def get_embedding_HuggingFace(model_name):
    model_name = model_name
    model_kwargs = {'device': 'cpu'}
    encode_kwargs = {'normalize_embeddings': False}
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )
    return embeddings

def store_to_qdrant(docs, embeddings, metadata):
    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    collection_name = f"{collection_prefix}_{metadata['id']}_{metadata['lecture_id']}_{metadata['student_id']}"

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
    

    # Add documents if the collection is empty
    if client.get_collection(collection_name).points_count == 0 or client.get_collection(collection_name).points_count is None:
        qdrant.add_documents(docs)
    print(f"Added {len(docs)} documents to collection {collection_name}")

# Flask routes
@app.route("/ingest-file", methods=['POST'])
def ingest_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and file.filename.lower().endswith('.pdf'):
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
        
        # Convert PDF to text using LLMSherpa
        try:
            loader = LLMSherpaFileLoader(
                file_path=file_path,
                new_indent_parser=True,
                apply_ocr=True,
                strategy="sections",
                llmsherpa_api_url=llmsherpa_api_url,
            )
            docs = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=2048, chunk_overlap=128)
            docs = text_splitter.split_documents(docs)
            store_to_qdrant(docs, get_embedding_HuggingFace(model_name_HuggingFace_768), metadata)
            # Here you would typically process the extracted text and metadata
            # For now, we'll just return a success message with the metadata and a preview of the text
            return jsonify({ 
                "message": f"File {filename} uploaded and processed successfully",
                "metadata": metadata
            }), 200
        except Exception as e:
            return jsonify({"error": f"Error processing PDF: {str(e)}"}), 500
    else:
        return jsonify({"error": "Invalid file format. Please upload a PDF file."}), 400

RAG = RAGPretrainedModel.from_pretrained("colbert-ir/colbertv2.0")

def create_compression_retriever(collection_name, embeddings):
    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    qdrant = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings,
    )
    compressor = RAG.as_langchain_document_compressor()
    
    retriever = qdrant.as_retriever(search_kwargs={"k": 5})
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=compressor, base_retriever=retriever
    )
    return compression_retriever

# Get OpenAI API key from environment
api_key_gpt = os.getenv('OPENAI_API_KEY')
if not api_key_gpt:
    logger.error("OPENAI_API_KEY environment variable is not set")
    raise ValueError("OPENAI_API_KEY environment variable is required")

def create_AI_agent(LLM, compression_retriever,prompt,verbose):
    verbose = False
    qa = RetrievalQA.from_chain_type(
        llm=LLM,
        chain_type="stuff",
        retriever=compression_retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt, "verbose": verbose},
    )
    return qa

prompt_template = """
Use the following pieces of information to answer the user's question.
If you don't know the answer, just say that you don't know, don't try to make up an answer.

Context: {context}
Question: {question}

{skill_prompt}
"""

@lru_cache(maxsize=100)
def get_qa_agent(student_id, skill_prompt):
    if skill_prompt is None:
        skill_prompt = ""
    cache_key = f"{student_id}_{hashlib.md5(skill_prompt.encode()).hexdigest()}"
    
    if cache_key in qa_cache:
        return qa_cache[cache_key]
    
    llmGPT = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        api_key=api_key_gpt,
    )
    
    # Combine the base prompt template with the skill prompt
    combined_prompt = prompt_template.format(
        context="{context}",
        question="{question}",
        skill_prompt=skill_prompt
    )
    
    print(f"Combined prompt: {combined_prompt}")
    
    prompt = PromptTemplate(
        template=combined_prompt,
        input_variables=["context", "question"]
    )

    # studentCollectionName = '12345_CS101_123459'
    collection_name = "student-bots-pdf-20250112"
    compression_retriever = create_compression_retriever(collection_name, get_embedding_HuggingFace(model_name_HuggingFace_768))
    qa = create_AI_agent(llmGPT, compression_retriever, prompt, verbose=True)
    
    qa_cache[cache_key] = qa
    return qa

@app.route("/process-message", methods=['POST'])
def process_message():
    try:
        data = request.get_json()
        logger.info(f"Received request data: {data}")
        
        # Extract data from request body
        student_id = data.get('student_id')
        question = data.get('question')
        skill_prompt = data.get('skill_prompt')
        
        if not all([student_id, question]):
            logger.error(f"Missing required fields. student_id: {student_id}, question: {question}")
            return jsonify({"error": "Missing required fields"}), 400
        
        try:
            # Get or create QA agent from cache
            logger.info(f"Getting QA agent for student_id: {student_id}")
            qa = get_qa_agent(student_id, skill_prompt)
            
            # Get response
            logger.info(f"Invoking QA with question: {question}")
            response = qa.invoke(question, {"callbacks": [get_langfuse_callback()]})
            
            logger.info(f"Successfully generated response for student_id: {student_id}")
            return jsonify({
                'student_id': student_id,
                'question': question,
                'output': response['result']
            })
        
        except Exception as e:
            logger.error(f"Error in QA processing: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({
                "error": f"QA processing error: {str(e)}",
                "traceback": traceback.format_exc()
            }), 500
    
    except Exception as e:
        logger.error(f"Error in request processing: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            "error": f"Request processing error: {str(e)}",
            "traceback": traceback.format_exc()
        }), 500

@app.route("/status")
def status():
    return {"status": "Service is running!"}

if __name__ == "__main__":
    # Run the metrics collection in a separate thread
    Thread(daemon=True, target=metrics_exporter.start_collect_and_push_metrics).start()

    # Run the Flask app
    app.run(host='0.0.0.0', port=metrics_exporter.PORT)
