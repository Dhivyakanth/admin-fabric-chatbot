import time
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import RetrievalQA
from dotenv import load_dotenv
import pandas as pd
import os
import re
from fetch_and_append import update_csv
from cache_manager import CacheManager
from numerical_analyzer import create_numerical_analyzer
from smart_api_handler import create_smart_api_handler
from spell_corrector import SpellCorrector
load_dotenv()

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
    print("❌ Error: GOOGLE_API_KEY not found in environment variables.")
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

# --- Setup
update_csv()
data = pd.read_csv("data/database_data.csv")
text_data = "\n".join([str(row) for row in data.to_dict(orient="records")])

# Initialize AI-powered numerical analyzer
print("🤖 Initializing AI-powered numerical analyzer...")
try:
    numerical_analyzer = create_numerical_analyzer("data/database_data.csv")
    print("✅ Numerical analyzer ready with AI models!")
except Exception as e:
    print(f"⚠️ Numerical analyzer initialization failed: {e}")
    numerical_analyzer = None

# Initialize Smart API Handler
print("🚀 Initializing Smart API Handler...")
try:
    smart_api = create_smart_api_handler("data/database_data.csv")
    print("✅ Smart API Handler ready with routing capabilities!")
except Exception as e:
    print(f"⚠️ Smart API Handler initialization failed: {e}")
    smart_api = None

# --- Chunk text and create embeddings
splitter = CharacterTextSplitter(chunk_size=1500, chunk_overlap=300)
docs = splitter.create_documents([text_data])
embedding = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

# --- Vector store
vectordb = FAISS.from_documents(docs, embedding)
retriever = vectordb.as_retriever()

# --- RAG Chain
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0)
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
        df_valid = df[df['status'] == 'Confirmed']
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
# --- Performance Analysis ---
def performance_analysis(question, analysis_type="full"):
    """
    Analyze performance of RAG pipeline for a given question.
    Returns timing, token usage (if available), and result length.
    """
    start_time = time.time()
    response = chatbot_ask(question)
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

def enhanced_chatbot_ask(question, session_id="default"):
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
            gemini_explanation = qa_chain.invoke({"query": f"Explain: {result}"})
            return extract_rag_answer(gemini_explanation)
        if 'agent' in question_lower and ('most order' in question_lower or 'most number of order' in question_lower):
            most_orders_agent = df_valid['agentName'].value_counts().idxmax()
            order_count = df_valid['agentName'].value_counts().max()
            result = f"{most_orders_agent} has handled the most orders: {order_count}"
            gemini_explanation = qa_chain.invoke({"query": f"Explain: {result}"})
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
            gemini_explanation = qa_chain.invoke({"query": f"Explain: {result}"})
            return extract_rag_answer(gemini_explanation)
        if 'customer' in question_lower and ('highest revenue' in question_lower or 'most revenue' in question_lower):
            df_valid['revenue'] = pd.to_numeric(df_valid['quantity'], errors='coerce') * pd.to_numeric(df_valid['rate'], errors='coerce')
            result_customer = df_valid.groupby('customerName')['revenue'].sum().idxmax()
            result_revenue = df_valid.groupby('customerName')['revenue'].sum().max()
            result = f"{result_customer} has generated the highest revenue: ${result_revenue:,.2f}"
            gemini_explanation = qa_chain.invoke({"query": f"Explain: {result}"})
            return extract_rag_answer(gemini_explanation)
    # Check cache for previous answer
    cached_answer = cache.get_context(question, session_id=session_id)
    if cached_answer:
        return cached_answer
    """Enhanced chatbot with Smart API routing and AI-powered analysis"""
    corrected_question = question  # Use raw question
    if smart_api:
        print("🎯 [Smart API Routing Activated]")
        try:
            smart_response = smart_api.process_query(corrected_question)
            # Most sold quality by quantity
            if "most sold quality" in corrected_question.lower():
                context_prompt = (
                    f"Question: {corrected_question}\n"
                    "Instruction: Use only the embedded tabular data below. "
                    "For each quality type, sum the total quantity sold (exclude declined orders). "
                    "Return a ranking of quality types by total quantity sold, from highest to lowest. "
                    "Clearly state which quality type is the most sold by quantity, and ensure this matches the top-ranked quality in your ranking. "
                    "If there are multiple with the same quantity, mention all. "
                    "Only show the total quantity as a single number (do not concatenate different units or show unit breakdowns). "
                    "Example format:\n"
                    "🤖 Bot: After analyzing all confirmed orders, the most sold quality type is **[quality]** with a total of [quantity] units sold.\n"
                    "Ranking:\n1. [quality1]: [quantity1]\n2. [quality2]: [quantity2]"
                )
            # Most sold composition by quantity
            elif "most sold composition" in corrected_question.lower():
                # Use pandas for correct ranking and answer
                df_valid = smart_api.data.copy()
                df_valid = df_valid[df_valid['status'] == 'Confirmed']
                df_valid['quantity_num'] = pd.to_numeric(df_valid['quantity'], errors='coerce')
                composition_group = df_valid.groupby('composition')['quantity_num'].sum().sort_values(ascending=False)
                most_sold_composition = composition_group.idxmax()
                most_sold_quantity = composition_group.max()
                ranking = "\n".join([f"{i+1}. {comp}: {int(qty)}" for i, (comp, qty) in enumerate(composition_group.items())])
                rag_answer = (
                    f"🤖 Bot: After analyzing all confirmed orders, the most sold composition is **{most_sold_composition}** with a total of {int(most_sold_quantity)} units sold.\n"
                    f"Ranking:\n{ranking}"
                )
                cache.update_context(corrected_question, rag_answer)
                return rag_answer
            # Most sold weave by quantity
            elif "most sold weave" in corrected_question.lower():
                context_prompt = (
                    f"Question: {corrected_question}\n"
                    "Instruction: Use only the embedded tabular data below. "
                    "For each weave type, sum the total quantity sold (exclude declined orders). "
                    "Return a ranking of weave types by total quantity sold, from highest to lowest. "
                    "Clearly state which weave type is the most sold by quantity, and ensure this matches the top-ranked weave in your ranking. "
                    "If there are multiple with the same quantity, mention all. "
                    "Only show the total quantity as a single number (do not concatenate different units or show unit breakdowns). "
                    "Example format:\n"
                    "🤖 Bot: After analyzing all confirmed orders, the most sold weave type is **[weave]** with a total of [quantity] units sold.\n"
                    "Ranking:\n1. [weave1]: [quantity1]\n2. [weave2]: [quantity2]"
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

def fallback_analysis(question, session_id="default"):
    """Fallback to original enhanced analysis if Smart API fails"""
    is_numerical = detect_numerical_query(question)
    if is_numerical and numerical_analyzer:
        print("🔢 [AI Numerical Analysis Mode Activated]")
        try:
            ai_analysis = numerical_analyzer.comprehensive_analysis(question)
            context_prompt = f"Question: {question}"
            rag_response = qa_chain.invoke({"query": context_prompt})
            rag_answer = extract_rag_answer(rag_response)
            combined_response = f"{ai_analysis}\n\n{rag_answer}"
            cache.update_context(question, combined_response, session_id=session_id)
            return combined_response
        except Exception as e:
            print(f"⚠️ AI analysis failed: {e}")
            return standard_chatbot_ask(question, session_id=session_id)
    else:
        return standard_chatbot_ask(question, session_id=session_id)

def standard_chatbot_ask(question, session_id="default"):
    """Standard RAG chatbot function"""
    context_prompt = f"Question: {question}"
    answer = qa_chain.invoke({"query": context_prompt})
    rag_answer = extract_rag_answer(answer)
    cache.update_context(question, rag_answer, session_id=session_id)
    return rag_answer

def chatbot_ask(question, session_id="default"):
    """Main chatbot function with AI enhancement"""
    return enhanced_chatbot_ask(question, session_id=session_id)

def format_customer_names(customers):
    """Convert a list of dicts with 'customerName' to plain text format."""
    return "\n".join([c['customerName'].strip() for c in customers if 'customerName' in c])

# --- CLI Loop
if __name__ == "__main__":
    print("🤠 Enhanced RAG Chatbot with SMART API ROUTING!")
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
            response = chatbot_ask(corrected_q, session_id=session_id)
            print("\n🤖 Bot:", response)
            print("=" *60)
        except KeyboardInterrupt:
            print("\n👋 Goodbye! Thanks for using the enhanced RAG chatbot!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            print("Please try again with a different question.")
