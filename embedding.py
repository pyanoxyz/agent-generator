import os
import json
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_community.llms import Together
from langchain_together import Together
import logging
from dotenv import load_dotenv
from tqdm.auto import tqdm
import time
from concurrent.futures import ThreadPoolExecutor

load_dotenv() 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up model cache
cache_dir = "./models"
os.makedirs(cache_dir, exist_ok=True)

MODELS_CACHE = os.getenv('MODELS_CACHE', './models')
# os.environ['TRANSFORMERS_CACHE'] = MODELS_CACHE
os.environ['HF_HOME'] = "./models"
os.makedirs(MODELS_CACHE, exist_ok=True)

# Download model
embeddings = HuggingFaceEmbeddings(model_name="togethercomputer/m2-bert-80M-32k-retrieval",
                                   cache_folder=MODELS_CACHE,
                                   model_kwargs = {'trust_remote_code': True})

# Initialize text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200,
    chunk_overlap=200,
    length_function=len,
)

# chroma_client = Chroma.Client()
    
# # Create or get collection
collection_name = "eliza_docs"
# collection = chroma_client.create_collection(
#     name=collection_name,
#     metadata={"hnsw:space": "cosine"}
# )
    
def process_document(doc):
    return text_splitter.split_documents([doc])

def setup_vectorstore(source_dir: str):
    """Initialize and return the vector store with the document collection."""
    # Load documents from the source directory
    loader = DirectoryLoader(source_dir,
                             glob=["**/*.ts", "**/*.json", "**/*.md"],
                             exclude=["**/package.json", "**/tsconfig.json", "**/vite.config.ts"],
                             loader_cls=TextLoader,
                             show_progress=True,
                             use_multithreading=True)
    
    documents = loader.load()
    
    if len(documents) == 0:
        raise ValueError(f"No documents found in {source_dir}")
    logger.info(f"Loaded {len(documents)} documents")
    
    logger.info("Splitting documents...")
    with ThreadPoolExecutor() as executor:
        texts = list(tqdm(
            executor.map(process_document, documents),
            total=len(documents),
            desc="Splitting documents"
        ))
    texts = [item for sublist in texts for item in sublist]
    logger.info(f"Created {len(texts)} text chunks")

    
    logger.info("Creating embeddings and vector store...")
    
    # texts = texts[0:10]
    

    # Create vector store
    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory="./data/chroma_db"
    )
    
    # Process embeddings with visible progress
    embeddings_list = []
    for doc in tqdm(texts, desc="Generating embeddings"):
        embedding = embeddings.embed_documents([doc.page_content])
        vectorstore.add_documents(documents=[doc], desc="Adding documents to Chroma")

        # embeddings_list.append(embedding[0])
    
    # vectorstore.add_documents(documents=texts, desc="Adding documents to Chroma")
    # vectorstore = chroma_client.from_documents(
    #     documents=texts,
    #     embeddings=embeddings,
    #     persist_directory="./data/chroma_db"
    # )
    
    return vectorstore


# Main execution
if __name__ == "__main__":
    try:
        # Ensure data directory exists
        os.makedirs("./data/chroma_db", exist_ok=True)
        start_time = time.time()
        # Setup vector store
        vectorstore = setup_vectorstore("./eliza-source")
        elapsed_time = time.time() - start_time
        logger.info("RAG system initialized successfully in {elapsed_time:.2f}")
        
    except Exception as e:
        logger.error(f"Error initializing RAG system: {str(e)}")
        raise
    
    
    # Setup vector store

