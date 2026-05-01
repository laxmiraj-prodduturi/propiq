import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma

load_dotenv()

CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "pdf_documents"
PDF_PATH = "/Users/laxmirajreddy/work/sample_data/4008_Gunnar_2.pdf"

docs = PyMuPDFLoader(PDF_PATH).load()

chunks = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150).split_documents(docs)

vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
    persist_directory=CHROMA_DIR,
    collection_name=COLLECTION_NAME,
)

print(f"Loaded {len(docs)} pages, stored {len(chunks)} chunks")

results = vectorstore.similarity_search("What is this document about?", k=5)
response = ChatOpenAI(model="gpt-4o-mini", temperature=0).invoke(f"{results} What is this document about")

print("======")
print(response.content)
