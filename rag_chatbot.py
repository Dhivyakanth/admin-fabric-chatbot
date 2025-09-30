import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import RetrievalQA
from dotenv import load_dotenv
import pandas as pd
import os
import re
import hashlib
import json
from fetch_and_append import update_csv
from cache_manager import CacheManager
from numerical_analyzer import create_numerical_analyzer
from smart_api_handler import create_smart_api_handler
from spell_corrector import SpellCorrector
import calendar
from datetime import datetime
load_dotenv()
def get_data_hash(csv_path):
    """
    Generate a hash of the CSV data to detect changes.
    
    Args:
        csv_path (str): Path to the CSV file
        
    Returns:
        str: MD5 hash of the CSV data
    """
    try:
        # Read the CSV file and sort by _id to ensure consistent ordering
        df = pd.read_csv(csv_path)
        if '_id' in df.columns:
            df = df.sort_values('_id').reset_index(drop=True)
        
        # Convert to JSON string for hashing
        data_string = df.to_json()
        
        # Generate and return hash
        return hashlib.md5(data_string.encode('utf-8')).hexdigest()
    except Exception as e:
        print(f"[!] Error generating data hash: {e}")
        return None


def save_embedding_metadata(embedding_cache_path, data_hash):
    """
    Save metadata about the embeddings including the data hash.
    
    Args:
        embedding_cache_path (str): Path to the embedding cache directory
        data_hash (str): Hash of the data used to create embeddings
    """
    try:
        metadata = {
            'data_hash': data_hash,
            'created_at': time.time()
        }
        metadata_path = os.path.join(embedding_cache_path, 'metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)
    except Exception as e:
        print(f"[!] Error saving embedding metadata: {e}")


def load_embedding_metadata(embedding_cache_path):
    """
    Load metadata about the embeddings including the data hash.
    
    Args:
        embedding_cache_path (str): Path to the embedding cache directory
        
    Returns:
        dict: Metadata dictionary or None if not found
    """
    try:
        metadata_path = os.path.join(embedding_cache_path, 'metadata.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"[!] Error loading embedding metadata: {e}")
        return None

def strip_summary_sections(response_text):
    """
    Remove summary sections from response text.
    Removes patterns like "**Summary:**", "**Key Insights:**", etc.
    """
    if not isinstance(response_text, str):
        return response_text
        
    # Remove common summary section headers
    patterns_to_remove = [
        r'\*\* Best Performance Analysis \*\*',
        r'\*\* Key Insights:\*\*',
        r'\*\* Recommendations:\*\*',
        r'\*\*Summary:\*\*',
        r'\*\*Detailed Breakdown:\*\*',
        r'\*\*Insights:\*\*',
        r'\*\*Best Performance Analysis\*\*',
        r'\*\*Key Insights\*\*',
        r'\*\*Recommendations\*\*'
    ]
    
    result = response_text
    for pattern in patterns_to_remove:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    result = re.sub(r'\n\s*\n', '\n\n', result)
    return result.strip()

# Check if Google API key is set
if not os.getenv("GOOGLE_API_KEY"):
    print("[X] Error: GOOGLE_API_KEY not found in environment variables.")
    print("Please add your Google API key to the .env file:")
    print("GOOGLE_API_KEY=your_actual_api_key_here")
    print("\nYou can get an API key from: https://makersuite.google.com/app/apikey")
    exit(1)

def detect_numerical_query(question):
    """Detect if the question requires numerical analysis"""
    numerical_keywords = [
        'total', 'sum', 'average', 'mean', 'count', 'how many', 'how much',
        'maximum', 'minimum', 'highest', 'lowest', 'greater than', 'less than',
        'calculate', 'add up', 'statistics', 'compare', 'trend', 'revenue',
        'performance', 'analysis', 'breakdown'
    ]
    return any(keyword in question.lower() for keyword in numerical_keywords)


update_csv()
data = pd.read_csv("data/database_data.csv")


text_data = "\n".join([str(row) for row in data.to_dict(orient="records")])

# Initialize AI-powered numerical analyzer
print("Initializing AI-powered numerical analyzer...")
try:
    numerical_analyzer = create_numerical_analyzer("data/database_data.csv")
    print("[OK] Numerical analyzer ready with AI models!")
except Exception as e:
    print(f"[!] Numerical analyzer initialization failed: {e}")
    numerical_analyzer = None

# Initialize Smart API Handler
print("[>] Initializing Smart API Handler...")
try:
    smart_api = create_smart_api_handler("data/database_data.csv")
    print("[OK] Smart API Handler ready with routing capabilities!")
except Exception as e:
    print(f"[!] Smart API Handler initialization failed: {e}")
    smart_api = None

# --- Chunk text and create embeddings
splitter = CharacterTextSplitter(chunk_size=1500, chunk_overlap=300)
docs = splitter.create_documents([text_data])

# Use local embedding model to avoid rate limits with Google API
# Also implement caching to avoid recreating embeddings every time
import os
embedding_cache_path = "chromadb/faiss_index"

try:
    # Generate hash of current data
    current_data_hash = get_data_hash("data/database_data.csv")
    print(f"[#] Current data hash: {current_data_hash}")
    
    # Check if we have cached embeddings and metadata
    if os.path.exists(embedding_cache_path) and os.path.isdir(embedding_cache_path):
        # Load metadata to check if data has changed
        metadata = load_embedding_metadata(embedding_cache_path)
        
        if metadata and 'data_hash' in metadata:
            cached_data_hash = metadata['data_hash']
            print(f"[#] Cached data hash: {cached_data_hash}")
            
            # Compare hashes to determine if data has changed
            if current_data_hash == cached_data_hash:
                print("[#] Loading embeddings from cache (data unchanged)...")
                embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
                vectordb = FAISS.load_local(embedding_cache_path, embedding, allow_dangerous_deserialization=True)
                print("[OK] Embeddings loaded from cache!")
            else:
                print("[#] Data has changed, creating new embeddings...")
                embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
                vectordb = FAISS.from_documents(docs, embedding)
                # Save embeddings to cache for next time
                os.makedirs(embedding_cache_path, exist_ok=True)
                vectordb.save_local(embedding_cache_path)
                # Save metadata with new hash
                save_embedding_metadata(embedding_cache_path, current_data_hash)
                print("[OK] New embeddings created and cached!")
        else:
            # No metadata or no hash in metadata, recreate embeddings
            print("[#] No metadata found, creating new embeddings...")
            embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            vectordb = FAISS.from_documents(docs, embedding)
            # Save embeddings to cache for next time
            os.makedirs(embedding_cache_path, exist_ok=True)
            vectordb.save_local(embedding_cache_path)
            # Save metadata with new hash
            save_embedding_metadata(embedding_cache_path, current_data_hash)
            print("[OK] Embeddings created and cached!")
    else:
        # No cache exists, create new embeddings
        print("[#] No cache found, creating new embeddings...")
        embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectordb = FAISS.from_documents(docs, embedding)
        # Save embeddings to cache for next time
        os.makedirs(embedding_cache_path, exist_ok=True)
        vectordb.save_local(embedding_cache_path)
        # Save metadata with new hash
        save_embedding_metadata(embedding_cache_path, current_data_hash)
        print("[OK] Embeddings created and cached!")
except Exception as e:
    print(f"[X] Error with local embeddings: {e}")
    print("[X] Critical Error: Could not initialize local embeddings. Please ensure sentence_transformers is installed: pip install sentence-transformers")
    print("[X] The application will now exit to prevent using Google API embeddings which may hit rate limits")
    exit(1)


# --- Retriever
retriever = vectordb.as_retriever()

# --- RAG Chain
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

# --- Cache
cache = CacheManager()

def get_top_documents(question, k=3):
    """Retrieve top k documents for the question (for debugging/inspection)"""
    docs = retriever.get_relevant_documents(question)
    return "\n---\n".join([str(doc.page_content) for doc in docs[:k]])

def extract_rag_answer(rag_response):
    """Extract the answer/result from the RAG response dict or string"""
    if isinstance(rag_response, dict):
        return rag_response.get("result", str(rag_response))
    return str(rag_response)
# --- Best Performance Analysis ---
def format_best_performance_response(agent_perf, weave_perf, quality_perf, composition_perf):
    """
    Format best performance data into a professional text format.
    
    Args:
        agent_perf (dict): Agent performance data
        weave_perf (dict): Weave performance data
        quality_perf (dict): Quality performance data
        composition_perf (dict): Composition performance data
    
    Returns:
        str: Formatted professional text response
    """
    # Format agent performance
    agent_orders = f"{agent_perf['most_orders'][0]} ({agent_perf['most_orders'][1]} orders)"
    agent_revenue = f"{agent_perf['highest_revenue'][0]} (${agent_perf['highest_revenue'][1]:,.2f})"
    
    # Format weave performance
    weave_orders = f"{weave_perf['most_orders'][0]} ({weave_perf['most_orders'][1]} orders)"
    weave_revenue = f"{weave_perf['highest_revenue'][0]} (${weave_perf['highest_revenue'][1]:,.2f})"
    
    # Format quality performance
    quality_orders = f"{quality_perf['most_orders'][0]} ({quality_perf['most_orders'][1]} orders)"
    quality_revenue = f"{quality_perf['highest_revenue'][0]} (${quality_perf['highest_revenue'][1]:,.2f})"
    
    # Format composition performance
    composition_orders = f"{composition_perf['most_orders'][0]} ({composition_perf['most_orders'][1]} orders)"
    composition_revenue = f"{composition_perf['highest_revenue'][0]} (${composition_perf['highest_revenue'][1]:,.2f})"
    
    # Create professional formatted response using ASCII characters instead of Unicode emojis
    formatted_response = (
        f"Best Performing Agent\n\n"
        f"Most Confirmed Orders: {agent_orders}\n"
        f"Highest Revenue: {agent_revenue}\n\n"
        f"Best Performing Weave\n\n"
        f"Most Confirmed Orders: {weave_orders}\n"
        f"Highest Revenue: {weave_revenue}\n\n"
        f"Best Performing Quality\n\n"
        f"Most Confirmed Orders: {quality_orders}\n"
        f"Highest Revenue: {quality_revenue}\n\n"
        f"Best Performing Composition\n\n"
        f"Most Confirmed Orders: {composition_orders}\n"
        f"Highest Revenue: {composition_revenue}\n\n"
        f"* {agent_perf['most_orders'][0]} is the top-performing agent with {agent_perf['most_orders'][1]} confirmed orders\n"
        f"* {weave_perf['most_orders'][0]} is the most popular weave type generating ${weave_perf['highest_revenue'][1]:,.2f} in revenue\n"
        f"* {quality_perf['most_orders'][0]} quality products show strong customer preference\n"
        f"* {composition_perf['most_orders'][0]} composition is driving significant sales volume\n\n"
        f"* Focus marketing efforts on {agent_perf['most_orders'][0]}'s successful strategies\n"
        f"* Increase inventory of {weave_perf['most_orders'][0]} and {composition_perf['most_orders'][0]} products\n"
        f"* Consider promoting {quality_perf['most_orders'][0]} products in upcoming campaigns\n"
        f"* Analyze {agent_perf['most_orders'][0]}'s techniques to train other agents"
    )
    
    # Strip summary sections from the response
    return strip_summary_sections(formatted_response)

def best_performance_analysis():
    """
    Analyze and report best performing agent, weave, quality, and composition
    based on confirmed orders and total revenue.
    """
    if smart_api and hasattr(smart_api, 'data'):
        df = smart_api.data.copy()
        df_valid = df[df['status'] != 'Declined']
        df_valid['quantity_num'] = pd.to_numeric(df_valid['quantity'], errors='coerce')
        df_valid['rate_num'] = pd.to_numeric(df_valid['rate'], errors='coerce')
        df_valid['revenue'] = df_valid['quantity_num'] * df_valid['rate_num']

        def get_best(df, col):
            count = df[col].value_counts().idxmax()
            count_num = df[col].value_counts().max()
            rev = df.groupby(col)['revenue'].sum().idxmax()
            rev_num = df.groupby(col)['revenue'].sum().max()
            return {
                'most_orders': (count, count_num),
                'highest_revenue': (rev, rev_num)
            }

        agent_perf = get_best(df_valid, 'agentName')
        weave_perf = get_best(df_valid, 'weave')
        quality_perf = get_best(df_valid, 'quality')
        composition_perf = get_best(df_valid, 'composition')

        # Use the formatting function to create a professional response
        formatted_report = format_best_performance_response(agent_perf, weave_perf, quality_perf, composition_perf)
        return formatted_report
    else:
        return "Performance analysis is not available. Data or Smart API missing."

# --- Revenue Calculation Functions ---
def calculate_revenue_by_year(df, year):
    """
    Calculate total revenue for a specific year.
    Only includes orders with status 'Confirmed' or 'Processed'.
    
    Args:
        df (pandas.DataFrame): The data frame containing order data
        year (int): The year for which to calculate revenue
    
    Returns:
        float: Total revenue for the specified year
    """
    # Filter for confirmed or processed orders
    filtered_df = df[df['status'].isin(['Confirmed', 'Processed'])]
    
    # Convert date column to datetime if it's not already
    filtered_df['date'] = pd.to_datetime(filtered_df['date'])
    
    # Filter for the specified year
    filtered_df = filtered_df[filtered_df['date'].dt.year == year]
    
    # Convert quantity and rate to numeric
    filtered_df['quantity_num'] = pd.to_numeric(filtered_df['quantity'], errors='coerce')
    filtered_df['rate_num'] = pd.to_numeric(filtered_df['rate'], errors='coerce')
    
    # Calculate revenue for each order
    filtered_df['revenue'] = filtered_df['quantity_num'] * filtered_df['rate_num']
    
    # Return total revenue
    return filtered_df['revenue'].sum()

def calculate_revenue_by_month(df, year, month):
    """
    Calculate total revenue for a specific month and year.
    Only includes orders with status 'Confirmed' or 'Processed'.
    
    Args:
        df (pandas.DataFrame): The data frame containing order data
        year (int): The year for which to calculate revenue
        month (int): The month for which to calculate revenue (1-12)
    
    Returns:
        float: Total revenue for the specified month and year
    """
    # Filter for confirmed or processed orders
    filtered_df = df[df['status'].isin(['Confirmed', 'Processed'])]
    
    # Convert date column to datetime if it's not already
    filtered_df['date'] = pd.to_datetime(filtered_df['date'])
    
    # Filter for the specified year and month
    filtered_df = filtered_df[
        (filtered_df['date'].dt.year == year) &
        (filtered_df['date'].dt.month == month)
    ]
    
    # Convert quantity and rate to numeric
    filtered_df['quantity_num'] = pd.to_numeric(filtered_df['quantity'], errors='coerce')
    filtered_df['rate_num'] = pd.to_numeric(filtered_df['rate'], errors='coerce')
    
    # Calculate revenue for each order
    filtered_df['revenue'] = filtered_df['quantity_num'] * filtered_df['rate_num']
    
    # Return total revenue
    return filtered_df['revenue'].sum()

def calculate_revenue_by_order_id(df, order_id):
    """
    Calculate revenue for a specific order ID.
    Only includes orders with status 'Confirmed' or 'Processed'.
    
    Args:
        df (pandas.DataFrame): The data frame containing order data
        order_id (str): The ID of the order for which to calculate revenue
    
    Returns:
        float: Revenue for the specified order ID, or 0 if not found
    """
    # Filter for the specific order ID and confirmed or processed status
    filtered_df = df[
        (df['_id'] == order_id) &
        (df['status'].isin(['Confirmed', 'Processed']))
    ]
    
    if filtered_df.empty:
        return 0.0
    
    # Convert quantity and rate to numeric
    filtered_df['quantity_num'] = pd.to_numeric(filtered_df['quantity'], errors='coerce')
    filtered_df['rate_num'] = pd.to_numeric(filtered_df['rate'], errors='coerce')
    
    # Calculate revenue for the order
    filtered_df['revenue'] = filtered_df['quantity_num'] * filtered_df['rate_num']
    
    # Return revenue (should be just one row)
    return filtered_df['revenue'].iloc[0] if not filtered_df.empty else 0.0

# --- Performance Analysis ---
def performance_analysis(question, analysis_type="full"):
    """
    Analyze performance of RAG pipeline for a given question.
    Returns timing, token usage (if available), and result length.
    """
    start_time = time.time()
    response = chatbot_ask(question, chat_history=None)
    end_time = time.time()
    elapsed = end_time - start_time
    result_length = len(str(response))
    perf_report = {
        "question": question,
        "analysis_type": analysis_type,
        "elapsed_seconds": round(elapsed, 3),
        "result_length": result_length,
        "response_preview": str(response)[:200] + ("..." if result_length > 200 else "")
    }
    # If LLM or retriever exposes token usage, add here
    # Example: perf_report["llm_tokens"] = getattr(llm, "last_token_usage", None)
    return perf_report

def replace_current_month_in_question(question: str) -> str:
    """
    Replace 'current month' in the question with the actual month name.
    """
    now = datetime.now()
    month_name = calendar.month_name[now.month]
    # Replace all variants of 'current month' (case-insensitive)
    return re.sub(r'current month', month_name, question, flags=re.IGNORECASE)

def enhanced_chatbot_ask(question, session_id="default", chat_history=None):
    # Always replace 'current month' with actual month name
    question = replace_current_month_in_question(question)


    question_lower = question.lower()
    # --- Best Performing Feature Routing ---
    bp_features = ["agent", "weave", "quality", "composition"]
    if "best performing" in question_lower:
        for feature in bp_features:
            if feature in question_lower:
                report = best_performance_analysis()
                section_map = {
                    "agent": "Best Performing Agent:",
                    "weave": "Best Performing Weave:",
                    "quality": "Best Performing Quality:",
                    "composition": "Best Performing Composition:"
                }
                section_title = section_map[feature]
                section = report.split(section_title)[-1].split("Best Performing ")[0].strip()
                return f"{section_title}\n{section}"
    # --- Pandas analytics for common business scenarios ---
    if smart_api and hasattr(smart_api, 'data'):
        df = smart_api.data.copy()
        df_valid = df[df['status'] != 'Declined']
        if 'customer' in question_lower and ('most order' in question_lower or 'most number of order' in question_lower):
            most_orders_customer = df_valid['customerName'].value_counts().idxmax()
            order_count = df_valid['customerName'].value_counts().max()
            result = f"{most_orders_customer} has placed the most orders: {order_count}"
            # Build context with chat history if available
            if chat_history and len(chat_history) > 0:
                # Format chat history for context
                history_text = "\n"
                for msg in chat_history:
                    role = msg.get("role", "")
                    content = msg.get("parts", [{}])[0].get("text", "") if msg.get("parts") else ""
                    if role and content:
                        history_text += f"{role}: {content}\n"
                context_prompt = f"Chat History:\n{history_text}\nExplain: {result}"
            else:
                context_prompt = f"Explain: {result}"
            gemini_explanation = qa_chain.invoke({"query": context_prompt})
            return extract_rag_answer(gemini_explanation)
        # Handle specific agent queries without grouping
        if 'agent' in question_lower and ('confirmed orders' in question_lower or 'declined orders' in question_lower or 'pending orders' in question_lower):
            # Check if a specific agent is mentioned in the question
            agent_names = ['mukilan', 'devaraj', 'boopalan']
            for agent in agent_names:
                if agent in question_lower:
                    # Filter by specific agent (case-insensitive) and status if mentioned
                    agent_df = df[df['agentName'].str.lower() == agent.lower()]
                    if 'confirmed orders' in question_lower:
                        agent_df = agent_df[agent_df['status'].str.lower() == 'confirmed']
                    elif 'declined orders' in question_lower:
                        agent_df = agent_df[agent_df['status'].str.lower() == 'declined']
                    elif 'pending orders' in question_lower:
                        agent_df = agent_df[agent_df['status'].str.lower() == 'pending']
                    
                    order_count = len(agent_df)
                    status_text = ''
                    if 'confirmed orders' in question_lower:
                        status_text = 'confirmed'
                    elif 'declined orders' in question_lower:
                        status_text = 'declined'
                    elif 'pending orders' in question_lower:
                        status_text = 'pending'
                    else:
                        status_text = 'total'
                    result = f"{agent.title()} has {order_count} {status_text} orders."
                    # Build context with chat history if available
                    if chat_history and len(chat_history) > 0:
                        # Format chat history for context
                        history_text = "\n"
                        for msg in chat_history:
                            role = msg.get("role", "")
                            content = msg.get("parts", [{}])[0].get("text", "") if msg.get("parts") else ""
                            if role and content:
                                history_text += f"{role}: {content}\n"
                        context_prompt = f"Chat History:\n{history_text}\nExplain: {result}"
                    else:
                        context_prompt = f"Explain: {result}"
                    gemini_explanation = qa_chain.invoke({"query": context_prompt})
                    return extract_rag_answer(gemini_explanation)
        
        if 'agent' in question_lower and ('most order' in question_lower or 'most number of order' in question_lower):
            most_orders_agent = df_valid['agentName'].value_counts().idxmax()
            order_count = df_valid['agentName'].value_counts().max()
            result = f"{most_orders_agent} has handled the most orders: {order_count}"
            # Build context with chat history if available
            if chat_history and len(chat_history) > 0:
                # Format chat history for context
                history_text = "\n"
                for msg in chat_history:
                    role = msg.get("role", "")
                    content = msg.get("parts", [{}])[0].get("text", "") if msg.get("parts") else ""
                    if role and content:
                        history_text += f"{role}: {content}\n"
                context_prompt = f"Chat History:\n{history_text}\nExplain: {result}"
            else:
                context_prompt = f"Explain: {result}"
            gemini_explanation = qa_chain.invoke({"query": context_prompt})
            return extract_rag_answer(gemini_explanation)
        if 'weave' in question_lower and ('most order' in question_lower or 'most number of order' in question_lower):
            most_orders_weave = df_valid['weave'].value_counts().idxmax()
            order_count = df_valid['weave'].value_counts().max()
            return f"Most sold weave: **{most_orders_weave}** ({order_count:,} units)"
        if 'quality' in question_lower and ('most order' in question_lower or 'most number of order' in question_lower):
            most_orders_quality = df_valid['quality'].value_counts().idxmax()
            order_count = df_valid['quality'].value_counts().max()
            return f"Most sold quality: **{most_orders_quality}** ({order_count:,} units)"
        if 'composition' in question_lower and ('most order' in question_lower or 'most number of order' in question_lower):
            most_orders_composition = df_valid['composition'].value_counts().idxmax()
            order_count = df_valid['composition'].value_counts().max()
            return f"Most sold composition: **{most_orders_composition}** ({order_count:,} units)"
        if 'customer' in question_lower and ('highest quantity' in question_lower or 'most quantity' in question_lower):
            df_valid['quantity_num'] = pd.to_numeric(df_valid['quantity'], errors='coerce')
            result_customer = df_valid.groupby('customerName')['quantity_num'].sum().idxmax()
            result_quantity = df_valid.groupby('customerName')['quantity_num'].sum().max()
            result = f"{result_customer} has ordered the highest quantity: {int(result_quantity)} units"
            # Build context with chat history if available
            if chat_history and len(chat_history) > 0:
                # Format chat history for context
                history_text = "\n"
                for msg in chat_history:
                    role = msg.get("role", "")
                    content = msg.get("parts", [{}])[0].get("text", "") if msg.get("parts") else ""
                    if role and content:
                        history_text += f"{role}: {content}\n"
                context_prompt = f"Chat History:\n{history_text}\nExplain: {result}"
            else:
                context_prompt = f"Explain: {result}"
            gemini_explanation = qa_chain.invoke({"query": context_prompt})
            return extract_rag_answer(gemini_explanation)
        if 'customer' in question_lower and ('highest revenue' in question_lower or 'most revenue' in question_lower):
            df_valid['revenue'] = pd.to_numeric(df_valid['quantity'], errors='coerce') * pd.to_numeric(df_valid['rate'], errors='coerce')
            result_customer = df_valid.groupby('customerName')['revenue'].sum().idxmax()
            result_revenue = df_valid.groupby('customerName')['revenue'].sum().max()
            result = f"{result_customer} has generated the highest revenue: ${result_revenue:,.2f}"
            # Build context with chat history if available
            if chat_history and len(chat_history) > 0:
                # Format chat history for context
                history_text = "\n"
                for msg in chat_history:
                    role = msg.get("role", "")
                    content = msg.get("parts", [{}])[0].get("text", "") if msg.get("parts") else ""
                    if role and content:
                        history_text += f"{role}: {content}\n"
                context_prompt = f"Chat History:\n{history_text}\nExplain: {result}"
            else:
                context_prompt = f"Explain: {result}"
            gemini_explanation = qa_chain.invoke({"query": context_prompt})
            return extract_rag_answer(gemini_explanation)
        # Revenue calculation queries
        if 'revenue' in question_lower:
            # Check for customer-specific revenue query
            customer_match = re.search(r'for customer ([\w\s]+?)(?:\s|$)|for ([\w\s]+?) customer|([A-Za-z\s]+?)(?:\'s|s\') revenue|revenue for ([A-Za-z\s]+?)$', question_lower)
            if customer_match:
                # Extract customer name from the match groups
                customer_name = next((g for g in customer_match.groups() if g and g not in ["'s", "s'"]), None)
                if customer_name:
                    customer_name = customer_name.strip()
                    # Find the best matching customer name from the dataset (case-insensitive)
                    possible_customers = df['customerName'].dropna().unique()
                    matched_customer = None
                    for cust in possible_customers:
                        if cust.lower() == customer_name.lower():
                            matched_customer = cust
                            break
                        elif customer_name.lower() in cust.lower() or cust.lower() in customer_name.lower():
                            matched_customer = cust
                            break
                    if matched_customer:
                        # Filter for specific customer
                        customer_df = df[df['customerName'].str.lower() == matched_customer.lower()]
                        customer_df = customer_df[customer_df['status'].isin(['Confirmed', 'Processed'])]
                        customer_df['quantity_num'] = pd.to_numeric(customer_df['quantity'], errors='coerce')
                        customer_df['rate_num'] = pd.to_numeric(customer_df['rate'], errors='coerce')
                        customer_df['revenue'] = customer_df['quantity_num'] * customer_df['rate_num']
                        customer_revenue = customer_df['revenue'].sum()
                        return f"Revenue for customer {matched_customer}: ${customer_revenue:,.2f}"
            
            # Check for agent-specific revenue query
            agent_match = re.search(r'for agent ([\w\s]+?)(?:\s|$)|for ([\w\s]+?) agent|([A-Za-z\s]+?)(?:\'s|s\') revenue|revenue for ([A-Za-z\s]+?)$', question_lower)
            if agent_match:
                # Extract agent name from the match groups
                agent_name = next((g for g in agent_match.groups() if g and g not in ["'s", "s'"]), None)
                if agent_name:
                    agent_name = agent_name.strip()
                    # Find the best matching agent name from the dataset (case-insensitive)
                    possible_agents = df['agentName'].dropna().unique()
                    matched_agent = None
                    for ag in possible_agents:
                        if ag.lower() == agent_name.lower():
                            matched_agent = ag
                            break
                        elif agent_name.lower() in ag.lower() or ag.lower() in agent_name.lower():
                            matched_agent = ag
                            break
                    if matched_agent:
                        # Filter for specific agent
                        agent_df = df[df['agentName'].str.lower() == matched_agent.lower()]
                        agent_df = agent_df[agent_df['status'].isin(['Confirmed', 'Processed'])]
                        agent_df['quantity_num'] = pd.to_numeric(agent_df['quantity'], errors='coerce')
                        agent_df['rate_num'] = pd.to_numeric(agent_df['rate'], errors='coerce')
                        agent_df['revenue'] = agent_df['quantity_num'] * agent_df['rate_num']
                        agent_revenue = agent_df['revenue'].sum()
                        return f"Revenue for agent {matched_agent}: ${agent_revenue:,.2f}"
            
            # Check for date-specific revenue query
            date_match = re.search(r'on (\d{4}-\d{2}-\d{2})|for date (\d{4}-\d{2}-\d{2})|revenue on (\d{4}-\d{2}-\d{2})|revenue for (\d{4}-\d{2}-\d{2})', question_lower)
            if date_match:
                # Extract date from the match groups
                date_str = next((g for g in date_match.groups() if g), None)
                if date_str:
                    # Filter for specific date
                    date_df = df[pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d') == date_str]
                    date_df = date_df[date_df['status'].isin(['Confirmed', 'Processed'])]
                    date_df['quantity_num'] = pd.to_numeric(date_df['quantity'], errors='coerce')
                    date_df['rate_num'] = pd.to_numeric(date_df['rate'], errors='coerce')
                    date_df['revenue'] = date_df['quantity_num'] * date_df['rate_num']
                    date_revenue = date_df['revenue'].sum()
                    return f"Revenue for date {date_str}: ${date_revenue:,.2f}"
            # Check for year-specific query
            year_match = re.search(r'\b(19|20)\d{2}\b', question)
            if year_match:
                year = int(year_match.group())
                # Check if it's a month query (e.g., "revenue for january 2025")
                month_names = ['january', 'february', 'march', 'april', 'may', 'june',
                              'july', 'august', 'september', 'october', 'november', 'december']
                month_name_match = re.search(r'(\b(?:' + '|'.join(month_names) + r')\b)', question_lower)
                if month_name_match:
                    month_name = month_name_match.group(1)
                    month_number = month_names.index(month_name) + 1
                    revenue = calculate_revenue_by_month(df, year, month_number)
                    return f"Revenue for {month_name.capitalize()} {year}: ${revenue:,.2f}"
                else:
                    # Year-only query
                    revenue = calculate_revenue_by_year(df, year)
                    return f"Revenue for {year}: ${revenue:,.2f}"
            
            # Check for order ID query
            # Look for order ID pattern (MongoDB ObjectId format - 24-character hex string)
            order_id_match = re.search(r'\b([a-f0-9]{24})\b', question)
            if order_id_match:
                order_id = order_id_match.group(1)
                revenue = calculate_revenue_by_order_id(df, order_id)
                if revenue > 0:
                    return f"Revenue for order {order_id}: ${revenue:,.2f}"
                else:
                    return f"No revenue found for order {order_id} (order may not exist or not be confirmed/processed)"
            
            # General revenue query - calculate for all confirmed/processed orders
            filtered_df = df[df['status'].isin(['Confirmed', 'Processed'])]
            filtered_df['quantity_num'] = pd.to_numeric(filtered_df['quantity'], errors='coerce')
            filtered_df['rate_num'] = pd.to_numeric(filtered_df['rate'], errors='coerce')
            filtered_df['revenue'] = filtered_df['quantity_num'] * filtered_df['rate_num']
            total_revenue = filtered_df['revenue'].sum()
            return f"Total revenue for all confirmed and processed orders: ${total_revenue:,.2f}"
    # Check cache for previous answer
    cached_answer = cache.get_context(question, session_id=session_id)
    if cached_answer:
        return cached_answer
    """Enhanced chatbot with Smart API routing and AI-powered analysis"""
    corrected_question = question  # Use raw question
    if smart_api:
        print("[Target] [Smart API Routing Activated]")
        try:
            # Check if this is a revenue query for specific customer, agent, or date before using Smart API
            question_lower = corrected_question.lower()
            if 'revenue' in question_lower:
                # Check for customer-specific revenue query
                customer_match = re.search(r'for customer ([\w\s]+?)(?:\s|$)|for ([\w\s]+?) customer|([A-Za-z\s]+?)(?:\'s|s\') revenue|revenue for ([A-Za-z\s]+?)$', question_lower)
                if customer_match:
                    # Extract customer name from the match groups
                    customer_name = next((g for g in customer_match.groups() if g and g not in ["'s", "s'"]), None)
                    if customer_name:
                        customer_name = customer_name.strip()
                        # Find the best matching customer name from the dataset (case-insensitive)
                        possible_customers = smart_api.data['customerName'].dropna().unique()
                        matched_customer = None
                        for cust in possible_customers:
                            if cust.lower() == customer_name.lower():
                                matched_customer = cust
                                break
                            elif customer_name.lower() in cust.lower() or cust.lower() in customer_name.lower():
                                matched_customer = cust
                                break
                        if matched_customer:
                            # Filter for specific customer
                            customer_df = smart_api.data[smart_api.data['customerName'].str.lower() == matched_customer.lower()]
                            customer_df = customer_df[customer_df['status'].isin(['Confirmed', 'Processed'])]
                            customer_df['quantity_num'] = pd.to_numeric(customer_df['quantity'], errors='coerce')
                            customer_df['rate_num'] = pd.to_numeric(customer_df['rate'], errors='coerce')
                            customer_df['revenue'] = customer_df['quantity_num'] * customer_df['rate_num']
                            customer_revenue = customer_df['revenue'].sum()
                            return f"Revenue for customer {matched_customer}: ${customer_revenue:,.2f}"
                
                # Check for agent-specific revenue query
                agent_match = re.search(r'for agent ([\w\s]+?)(?:\s|$)|for ([\w\s]+?) agent|([A-Za-z\s]+?)(?:\'s|s\') revenue|revenue for ([A-Za-z\s]+?)$', question_lower)
                if agent_match:
                    # Extract agent name from the match groups
                    agent_name = next((g for g in agent_match.groups() if g and g not in ["'s", "s'"]), None)
                    if agent_name:
                        agent_name = agent_name.strip()
                        # Find the best matching agent name from the dataset (case-insensitive)
                        possible_agents = smart_api.data['agentName'].dropna().unique()
                        matched_agent = None
                        for ag in possible_agents:
                            if ag.lower() == agent_name.lower():
                                matched_agent = ag
                                break
                            elif agent_name.lower() in ag.lower() or ag.lower() in agent_name.lower():
                                matched_agent = ag
                                break
                        if matched_agent:
                            # Filter for specific agent
                            agent_df = smart_api.data[smart_api.data['agentName'].str.lower() == matched_agent.lower()]
                            agent_df = agent_df[agent_df['status'].isin(['Confirmed', 'Processed'])]
                            agent_df['quantity_num'] = pd.to_numeric(agent_df['quantity'], errors='coerce')
                            agent_df['rate_num'] = pd.to_numeric(agent_df['rate'], errors='coerce')
                            agent_df['revenue'] = agent_df['quantity_num'] * agent_df['rate_num']
                            agent_revenue = agent_df['revenue'].sum()
                            return f"Revenue for agent {matched_agent}: ${agent_revenue:,.2f}"
                
                # Check for date-specific revenue query
                date_match = re.search(r'on (\d{4}-\d{2}-\d{2})|for date (\d{4}-\d{2}-\d{2})|revenue on (\d{4}-\d{2}-\d{2})|revenue for (\d{4}-\d{2}-\d{2})', question_lower)
                if date_match:
                    # Extract date from the match groups
                    date_str = next((g for g in date_match.groups() if g), None)
                    if date_str:
                        # Filter for specific date
                        date_df = smart_api.data[pd.to_datetime(smart_api.data['date']).dt.strftime('%Y-%m-%d') == date_str]
                        date_df = date_df[date_df['status'].isin(['Confirmed', 'Processed'])]
                        date_df['quantity_num'] = pd.to_numeric(date_df['quantity'], errors='coerce')
                        date_df['rate_num'] = pd.to_numeric(date_df['rate'], errors='coerce')
                        date_df['revenue'] = date_df['quantity_num'] * date_df['rate_num']
                        date_revenue = date_df['revenue'].sum()
                        return f"Revenue for date {date_str}: ${date_revenue:,.2f}"
            smart_response = smart_api.process_query(corrected_question)
            # Most sold quality by quantity
            if "most sold quality" in corrected_question.lower():
                # Use pandas for correct ranking and answer
                df_valid = smart_api.data.copy()
                df_valid = df_valid[df_valid['status'] != 'Declined']
                df_valid = df_valid.copy()  # Create a copy to avoid SettingWithCopyWarning
                df_valid['quality_normalized'] = df_valid['quality'].str.lower()
                df_valid['quantity_num'] = pd.to_numeric(df_valid['quantity'], errors='coerce')
                quality_group = df_valid.groupby('quality_normalized')['quantity_num'].sum().sort_values(ascending=False)
                most_sold_quality = quality_group.idxmax()
                most_sold_quantity = quality_group.max()
                ranking = "\n".join([f"{i+1}. {quality.title()}: {int(qty)}" for i, (quality, qty) in enumerate(quality_group.head(3).items())])
                rag_answer = (
                    f"After analyzing all confirmed orders, the most sold quality type is **{most_sold_quality}** with a total of {int(most_sold_quantity)} units sold.\n"
                    f"Ranking:\n{ranking}"
                )
                cache.update_context(corrected_question, rag_answer)
                return rag_answer
            # Most sold composition by quantity
            elif "most sold composition" in corrected_question.lower():
                # Use pandas for correct ranking and answer
                df_valid = smart_api.data.copy()
                df_valid = df_valid[df_valid['status'] != 'Declined']
                df_valid = df_valid.copy()  # Create a copy to avoid SettingWithCopyWarning
                df_valid['composition_normalized'] = df_valid['composition'].str.lower()
                df_valid['quantity_num'] = pd.to_numeric(df_valid['quantity'], errors='coerce')
                composition_group = df_valid.groupby('composition_normalized')['quantity_num'].sum().sort_values(ascending=False)
                most_sold_composition = composition_group.idxmax()
                most_sold_quantity = composition_group.max()
                ranking = "\n".join([f"{i+1}. {comp.title()}: {int(qty)}" for i, (comp, qty) in enumerate(composition_group.head(3).items())])
                rag_answer = (
                    f"After analyzing all confirmed orders, the most sold composition is **{most_sold_composition}** with a total of {int(most_sold_quantity)} units sold.\n"
                    f"Ranking:\n{ranking}"
                )
                cache.update_context(corrected_question, rag_answer)
                return rag_answer
            # Most sold weave by quantity
            elif "most sold weave" in corrected_question.lower():
                # Use pandas for correct ranking and answer
                df_valid = smart_api.data.copy()
                df_valid = df_valid[df_valid['status'] != 'Declined']
                df_valid = df_valid.copy()  # Create a copy to avoid SettingWithCopyWarning
                df_valid['weave_normalized'] = df_valid['weave'].str.lower()
                df_valid['quantity_num'] = pd.to_numeric(df_valid['quantity'], errors='coerce')
                weave_group = df_valid.groupby('weave_normalized')['quantity_num'].sum().sort_values(ascending=False)
                most_sold_weave = weave_group.idxmax()
                most_sold_quantity = weave_group.max()
                ranking = "\n".join([f"{i+1}. {weave.title()}: {int(qty)}" for i, (weave, qty) in enumerate(weave_group.head(3).items())])
                rag_answer = (
                    f"After analyzing all confirmed orders, the most sold weave type is **{most_sold_weave}** with a total of {int(most_sold_quantity)} units sold.\n"
                    f"Ranking:\n{ranking}"
                )
                cache.update_context(corrected_question, rag_answer)
                return rag_answer
            # Handle specific agent queries without grouping
            elif "confirmed orders" in corrected_question.lower() and any(agent in corrected_question.lower() for agent in ['mukilan', 'devaraj', 'boopalan']):
                # Extract specific agent from question
                agent_names = ['mukilan', 'devaraj', 'boopalan']
                for agent in agent_names:
                    if agent in corrected_question.lower():
                        agent_data = smart_api.data[smart_api.data['agentName'].str.lower() == agent.lower()]
                        confirmed_data = agent_data[agent_data['status'] == 'Confirmed']
                        order_count = len(confirmed_data)
                        return f"{agent.title()} has {order_count} confirmed orders."
                # If we couldn't identify a specific agent, return general info
                context_prompt = (
                    f"Question: {corrected_question}\n"
                    "Instruction: Use only the embedded tabular data below. "
                    "Count orders with status 'Confirmed' for the specified agent. "
                    "Return the exact count for the specific agent mentioned in the question. "
                    "Do not group or aggregate by other fields. "
                    "Example output:\n"
                    "Mukilan has 12 confirmed orders."
                )
            # Concise agent-wise confirmation summary
            elif "agent wise order confirmation list" in corrected_question.lower():
                context_prompt = (
                    f"Question: {corrected_question}\n"
                    "Instruction: Use only the embedded tabular data below. "
                    "For each agent, count the number of orders with status 'Confirmed'. "
                    "Return a concise summary listing each agent and their confirmed order count. "
                    "Do not include detailed order information. "
                    "Example output:\n"
                    "Mukilan: 9 confirmed orders\nDevaraj: 1 confirmed order\nBoopalan: 1 confirmed order"
                )
            elif "for each composition, list the highest quantity order and the customer who placed it" in corrected_question.lower():
                context_prompt = (
                    f"Question: {corrected_question}\n"
                    "Instruction: Use only the embedded tabular data below. "
                    "For each unique composition, find the order with the highest quantity (status must be 'Confirmed'). "
                    "Return only the composition, the highest quantity (as a number), and the customer name. "
                    "Ignore declined or processed orders. "
                    "Output format:\n"
                    "Composition: [composition], Highest Quantity: [quantity], Customer: [customerName]\n"
                    "Example:\n"
                    "Composition: cc x cc, Highest Quantity: 100000, Customer: Nandhakumar T\n"
                    "Composition: mxm, Highest Quantity: 84000, Customer: palaniappan"
                )
            # Refined prompt for confirmed order count
            elif "how many orders confirmed" in corrected_question.lower() or \
                 "number of confirmed orders" in corrected_question.lower():
                context_prompt = (
                    f"Question: {corrected_question}\n"
                    "Instruction: Use only the embedded tabular data below. "
                    "Count only rows where status is 'Confirmed'. "
                    "Return the exact count of confirmed orders in the dataset. "
                    "Data schema: date, quality, weave, quantity, composition, status, _id, rate, agentName, customerName\n"
                    "Example reasoning:\n"
                    "If there are 11 rows with status 'Confirmed', answer:\n"
                    "'There are 11 orders with the status \"Confirmed\".'"
                )
            elif "confirmed by agents other than mukilan" in corrected_question.lower():
                context_prompt = (
                    f"Question: {corrected_question}\n"
                    "Instruction: Use only the embedded tabular data below. "
                    "Count only rows where status is 'Confirmed' and agentName is NOT 'Mukilan'. "
                    "Group by agentName and count confirmed orders for each agent (excluding Mukilan). "
                    "List each agent and their confirmed order count. "
                    "Data schema: date, quality, weave, quantity, composition, status, _id, rate, agentName, customerName\n"
                    "Example reasoning:\n"
                    "If Devaraj has 1 confirmed order and Boopalan has 1 confirmed order, answer:\n"
                    "'Agent Devaraj: 1 order\nAgent Boopalan: 1 order'"
                )
            elif "most confirmed orders" in corrected_question.lower():
                context_prompt = (
                    f"Question: {corrected_question}\n"
                    "Instruction: Use only the embedded data. "
                    "Identify the agent with the most confirmed orders and provide both the agent's name and the exact number of confirmed orders for that agent. "
                    "Also, report the total number of confirmed orders in the dataset for transparency. "
                    "Example format: '[AgentName] handled the most confirmed orders with [AgentOrderCount] confirmed orders. Total confirmed orders in dataset: [TotalConfirmedOrders].'"
                )
            else:
                context_prompt = f"Question: {corrected_question}"
            # Build context with chat history if available
            if chat_history and len(chat_history) > 0:
                # Format chat history for context
                history_text = "\n"
                for msg in chat_history:
                    role = msg.get("role", "")
                    content = msg.get("parts", [{}])[0].get("text", "") if msg.get("parts") else ""
                    if role and content:
                        history_text += f"{role}: {content}\n"
                context_prompt = f"Chat History:\n{history_text}\n{context_prompt}"
            rag_response = qa_chain.invoke({"query": context_prompt})
            rag_answer = extract_rag_answer(rag_response)
            combined_response = f"{rag_answer}"
            cache.update_context(corrected_question, combined_response)
            return combined_response
        except Exception as e:
            print(f"⚠️ Smart API failed: {e}")
            return fallback_analysis(corrected_question)
    else:
        return fallback_analysis(corrected_question)

def fallback_analysis(question, session_id="default", chat_history=None):
    """Fallback to original enhanced analysis if Smart API fails"""
    is_numerical = detect_numerical_query(question)
    if is_numerical and numerical_analyzer:
        print("[#] [AI Numerical Analysis Mode Activated]")
        try:
            ai_analysis = numerical_analyzer.comprehensive_analysis(question)
            # Build context with chat history if available
            if chat_history and len(chat_history) > 0:
                # Format chat history for context
                history_text = "\n"
                for msg in chat_history:
                    role = msg.get("role", "")
                    content = msg.get("parts", [{}])[0].get("text", "") if msg.get("parts") else ""
                    if role and content:
                        history_text += f"{role}: {content}\n"
                context_prompt = f"Chat History:\n{history_text}\nQuestion: {question}"
            else:
                context_prompt = f"Question: {question}"
            rag_response = qa_chain.invoke({"query": context_prompt})
            rag_answer = extract_rag_answer(rag_response)
            combined_response = f"{ai_analysis}\n\n{rag_answer}"
            cache.update_context(question, combined_response, session_id=session_id)
            return combined_response
        except Exception as e:
            print(f"⚠️ AI analysis failed: {e}")
            return standard_chatbot_ask(question, session_id=session_id, chat_history=chat_history)
    else:
        return standard_chatbot_ask(question, session_id=session_id, chat_history=chat_history)

def standard_chatbot_ask(question, session_id="default", chat_history=None):
    """Standard RAG chatbot function"""
    # Build context with chat history if available
    if chat_history and len(chat_history) > 0:
        # Format chat history for context
        history_text = "\n"
        for msg in chat_history:
            role = msg.get("role", "")
            content = msg.get("parts", [{}])[0].get("text", "") if msg.get("parts") else ""
            if role and content:
                history_text += f"{role}: {content}\n"
        context_prompt = f"Chat History:\n{history_text}\nQuestion: {question}"
    else:
        context_prompt = f"Question: {question}"
    answer = qa_chain.invoke({"query": context_prompt})
    rag_answer = extract_rag_answer(answer)
    cache.update_context(question, rag_answer, session_id=session_id)
    return rag_answer

def chatbot_ask(question, session_id="default", chat_history=None):
    """Main chatbot function with AI enhancement"""
    return enhanced_chatbot_ask(question, session_id=session_id, chat_history=chat_history)

def format_customer_names(customers):
    """Convert a list of dicts with 'customerName' to plain text format."""
    return "\n".join([c['customerName'].strip() for c in customers if 'customerName' in c])

# --- CLI Loop
if __name__ == "__main__":
    print("Enhanced RAG Chatbot with SMART API ROUTING!")
    corrector = SpellCorrector()
    session_id = "default"
    while True:
        try:
            user_q = input("\n🙋 You: ")
            if user_q.lower() in ["exit", "quit", "bye"]:
                print("👋 Goodbye! Thanks for using the enhanced RAG chatbot!")
                break
            if user_q.lower().startswith("perf:"):
                perf_question = user_q[5:].strip()
                corrected_q = corrector.correct(perf_question)
                print(f"[SpellCorrector] Corrected question: {corrected_q}")
                print(f"⚡ Running performance analysis for: {corrected_q}")
                perf = performance_analysis(corrected_q)
                print("\n📊 Performance Report:")
                for k, v in perf.items():
                    print(f"{k}: {v}")
                print("=" * 60)
                continue
            corrected_q = corrector.correct(user_q)
            if corrected_q != user_q:
                print(f"[SpellCorrector] Corrected question: {corrected_q}")
            print(f"🤔 Processing your query... (Raw: {user_q})")
            response = chatbot_ask(corrected_q, session_id=session_id, chat_history=None)
            print("\n🤖 Bot:", response)
            print("=" *60)
        except KeyboardInterrupt:
            print("\n👋 Goodbye! Thanks for using the enhanced RAG chatbot!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            print("Please try again with a different question.")
