# RAG Chatbot using Gemini LLM, LangChain, and ChromaDB
# Requires: langchain, chromadb, pandas, openai (for Gemini API placeholder)
# Install: pip install langchain chromadb pandas openai


import pandas as pd
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load Gemini API key
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)





# Gemini embedding function
def gemini_embed(texts):
	embeddings = []
	for text in texts:
		response = genai.embed_content(model="models/embedding-001", content=text)
		embeddings.append(response['embedding'])
	return embeddings

# Gemini LLM function

def gemini_llm(prompt):
	model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
	response = model.generate_content(prompt)
	return response.text


# 1. Data Ingestion & Chunking
df = pd.read_csv(r'data/database_data.csv')
documents = df.apply(lambda row: ' '.join([str(x) for x in row]), axis=1).tolist()

text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = []
for doc in documents:
	chunks.extend(text_splitter.split_text(doc))


# 2 & 3. Vector Database Storage with Gemini embedding function

class GeminiEmbeddingFunction:
	def embed_documents(self, texts):
		return gemini_embed(texts)

	def embed_query(self, text):
		return gemini_embed([text])[0]

embedding_function = GeminiEmbeddingFunction()
vector_db = Chroma.from_texts(chunks, embedding_function, persist_directory="chromadb")


# 4. Retrieval Mechanism
def retrieve_context(query, k=3):
	query_embedding = gemini_embed([query])[0]
	docs = vector_db.similarity_search_by_vector(query_embedding, k=k)
	return [doc.page_content for doc in docs]


# 5. Augmentation & Generation
def generate_response(query):
	context_chunks = retrieve_context(query)
	context = '\n'.join(context_chunks)
	prompt = f"""
	You are a helpful assistant. Use ONLY the following context to answer the user's question. If the answer is not in the context, say 'I don't know based on the provided data.'
	Context:
	{context}
	Question: {query}
	"""
	return gemini_llm(prompt)


# 6. Dynamic Data Updates (simple reload function)
def reload_data():
	global vector_db
	df = pd.read_csv(r'data/database_data.csv')
	documents = df.apply(lambda row: ' '.join([str(x) for x in row]), axis=1).tolist()
	chunks = []
	for doc in documents:
		chunks.extend(text_splitter.split_text(doc))
	embeddings = gemini_embed(chunks)
	vector_db = Chroma.from_embeddings(chunks, embeddings, persist_directory="chromadb")

# --- Example Usage ---
if __name__ == "__main__":
	print("RAG Chatbot Ready. Type your question (or 'exit' to quit):")
	while True:
		user_query = input("You: ")
		if user_query.lower() == 'exit':
			break
		response = generate_response(user_query)
		print("Bot:", response)
