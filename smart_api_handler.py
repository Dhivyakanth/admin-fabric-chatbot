import pandas as pd
import os
import re
from datetime import datetime
from dotenv import load_dotenv

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
        r'\*\*Recommendations\*\*',
        r'\*\*Summary\*\*',
        r'\*\*Detailed Breakdown\*\*',
        r'\*\*Insights\*\*',
        r'\*\*Best performing agent\*\*',
        r'\*\*Best performing customer\*\*',
        r'\*\*{[^}]*} Summary:\*\*'
    ]
    
    result = response_text
    for pattern in patterns_to_remove:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    result = re.sub(r'\n\s*\n', '\n\n', result)
    return result.strip()

load_dotenv()

class SmartAPIHandler:
    def get_dynamic_keywords(self):
        """Extract all unique keywords from the dataset for routing and understanding."""
        keywords = set()
        for col in ['agentName', 'weave', 'quality', 'composition', 'customerName']:
            if col in self.data.columns:
                keywords.update(str(val).lower() for val in self.data[col].dropna().unique())
        return keywords
    def get_question_context(self, question):
        """Analyze the question and return its context (intent, entities, type, etc.)"""
        context = {}
        q = question.lower()
        # Example context extraction
        if any(word in q for word in ["weave", "quality", "composition"]):
            context["category"] = next((word for word in ["weave", "quality", "composition"] if word in q), None)
        if any(word in q for word in ["total", "sum", "average", "count", "how many", "most sold", "highest", "best selling", "least sold", "lowest"]):
            context["math"] = True
        if "agent" in q:
            context["agent"] = True
        # Add more context extraction as needed
        context["raw"] = question
        return context
    def build_prompt(self, question, previous_context=None):
        """Builds a prompt with clear instructions and examples for the model."""
        context = self.data.to_string(index=False)
        prompt = f"""
DATASET:
{context}

QUESTION: {question}

INSTRUCTIONS:
- Analyze the dataset and answer the question using relevant business metrics.
- If the question contains a name present in the dataset, summarize their business profile (orders, quantity, revenue).
- For mathematical queries, perform calculations using the data.
- For category queries (weave, quality, composition), filter and summarize accordingly.
- If the question is general, provide a summary or list as appropriate.
- If the answer cannot be found, state that clearly.

EXAMPLES:
Q: WHO IS MUKILAN?
A: Mukilan is an agent/customer in the dataset. Business profile:
   - Total Orders: [count]
   - Total Quantity: [sum]
   - Total Revenue: [sum]

Q: WHAT IS THE MOST SOLD WEAVE TYPE?
A: The most sold weave type is [type] with [quantity] units sold.

Q: BEST CUSTOMER?
A: The best customer is [name] with [revenue] from [orders] orders.

Q: WHO IS XYZ?
A: No records found for XYZ in the dataset.
"""
        return prompt
    def __init__(self, csv_path="data/database_data.csv"):
        self.csv_path = csv_path
        self.data = pd.read_csv(csv_path)
    
    def detect_query_type(self, question):
        """Detect what type of query this is"""
        question_lower = question.lower()
        
        # Mathematical operation keywords
        math_keywords = [
            'total', 'sum', 'add', 'calculate', 'average', 'mean', 'count', 
            'how many', 'how much', 'maximum', 'minimum', 'highest', 'lowest',
            'greater than', 'less than', 'statistics', 'analysis', 'breakdown',
            'revenue', 'performance', 'trend', 'compare', 'sales', 'best', 'worst',
            'top', 'bottom', 'ranking', 'leader', 'winner', 'performing', 'most'
        ]
        
        # Customer-related keywords
        customer_keywords = ['customer', 'customers', 'client', 'clients', 'buyer', 'buyers', 'ordered', 'placed orders', 'details', 'show', 'list', 'give me']
        
        # Category keywords
        weave_keywords = ['weave', 'weaving', 'plain', 'twill', 'satin', 'linen', 'spandex']
        quality_keywords = ['quality', 'premium', 'standard', 'primium', 'premier']
        composition_keywords = ['composition', 'cotton', 'material', 'fabric', 'percent', '%']
        
        # Check for mathematical operations first (higher priority)
        if any(keyword in question_lower for keyword in math_keywords):
            return "math"
        
        # Check for customer-related queries
        if any(keyword in question_lower for keyword in customer_keywords):
            return "customer"
        
        # Check for specific categories
        if any(keyword in question_lower for keyword in weave_keywords):
            return "weave"
        elif any(keyword in question_lower for keyword in quality_keywords):
            return "quality"
        elif any(keyword in question_lower for keyword in composition_keywords):
            return "composition"
        
        # Default to general query
        return "general"
    
    def detect_agent_context(self, question, previous_context=""):
        """Detect if the question is about a specific agent"""
        question_lower = question.lower()
        full_context = f"{previous_context} {question}".lower()
        
        # Agent variations (handle common misspellings)
        agent_variations = {
            'mukilan': ['mukilan'],
            'devaraj': ['devaraj', 'deveraj', 'devaraj'],  # Handle common typo
            'boopalan': ['boopalan']
        }
        
        # First check current question for direct agent mentions
        for agent, variations in agent_variations.items():
            for variation in variations:
                if variation in question_lower:
                    return agent.title()
        
        # Then check for pronoun references with context
        pronouns = ['he', 'his', 'him']
        if any(pronoun in question_lower for pronoun in pronouns):
            # Check previous context for agent mentions (only if no direct mention in question)
            for agent, variations in agent_variations.items():
                for variation in variations:
                    if variation in full_context:
                        return agent.title()
        
        return None
    
    def filter_data_by_agent(self, agent_name):
        """Filter data for specific agent with case-insensitive matching"""
        return self.data[self.data['agentName'].str.lower() == agent_name.lower()].copy()
    
    def get_weave_data(self):
        """Get data focused on weave information"""
        columns = ['date', 'weave', 'quantity', 'status', '_id', 'rate', 'agentName', 'customerName']
        return self.data[columns].copy()
    
    def get_quality_data(self):
        """Get data focused on quality information"""
        columns = ['date', 'quality', 'quantity', 'status', '_id', 'rate', 'agentName', 'customerName']
        return self.data[columns].copy()
    
    def get_composition_data(self):
        """Get data focused on composition information"""
        columns = ['date', 'composition', 'quantity', 'status', '_id', 'rate', 'agentName', 'customerName']
        return self.data[columns].copy()
    
    def clean_quantity_data(self, df):
        """Clean and standardize quantity data from mixed formats"""
        def extract_quantity(value):
            """Extract numeric quantity from various formats"""
            if pd.isna(value):
                return 0
            
            # Convert to string and clean
            value_str = str(value).strip().lower()
            
            # Handle obvious non-numeric values
            if value_str in ['g', 'tyy', 'fhy', 'something', 'rbi', 'ftg', 'h', 'gfh', 'nm', 'mxm']:
                return 0
            
            # Extract numbers using regex
            import re
            numbers = re.findall(r'[\d,]+\.?\d*', value_str)
            
            if not numbers:
                return 0
            
            # Take the first number found
            try:
                # Remove commas and convert to float
                number = float(numbers[0].replace(',', ''))
                
                # Handle unit conversions
                if 'yards' in value_str or 'yard' in value_str:
                    return number  # Keep yards as is
                elif 'm' in value_str and 'm' != 'mxm':  # meters
                    return number  # Keep meters as is for now
                else:
                    return number
                    
            except (ValueError, IndexError):
                return 0
        
        # Apply cleaning function
        df = df.copy()
        df['quantity_clean'] = df['quantity'].apply(extract_quantity)
        
        # Clean rate data as well
        df['rate_clean'] = pd.to_numeric(df['rate'], errors='coerce').fillna(0)
        
        return df
    
    def filter_by_date(self, df, question):
        """Filter data by date based on question keywords"""
        question_lower = question.lower()
        
        # Convert date column to datetime if it's not already
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        
        import re
        
        # Check for specific date patterns first (highest priority)
        # Pattern: DD-MM-YYYY or DD/MM/YYYY or MM-DD-YYYY or MM/DD/YYYY
        date_patterns = [
            r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b',  # DD-MM-YYYY or DD/MM/YYYY or MM-DD-YYYY
            r'\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b',  # YYYY-MM-DD or YYYY/MM/DD
        ]
        
        for pattern in date_patterns:
            date_match = re.search(pattern, question)
            if date_match:
                if pattern.startswith(r'\b(\d{4})'):  # YYYY-MM-DD format
                    year, month, day = date_match.groups()
                else:  # DD-MM-YYYY or MM-DD-YYYY format
                    part1, part2, year = date_match.groups()
                    # Try both DD-MM and MM-DD interpretations
                    try:
                        # First try DD-MM-YYYY (common in many countries)
                        test_date = pd.to_datetime(f"{year}-{part2}-{part1}")
                        month, day = part2, part1
                    except:
                        try:
                            # Then try MM-DD-YYYY (US format)
                            test_date = pd.to_datetime(f"{year}-{part1}-{part2}")
                            month, day = part1, part2
                        except:
                            continue
                
                try:
                    target_date = pd.to_datetime(f"{year}-{month}-{day}")
                    filtered_df = df[df['date'].dt.date == target_date.date()]
                    if len(filtered_df) > 0:
                        return filtered_df, f"on {target_date.strftime('%B %d, %Y')}"
                except:
                    continue
        
        # Extract month names and numbers
        month_keywords = {
            'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
            'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6,
            'july': 7, 'jul': 7, 'august': 8, 'aug': 8, 'september': 9, 'sep': 9,
            'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12
        }
        
        # Check for month-based filtering
        for month_name, month_num in month_keywords.items():
            if month_name in question_lower or f" {month_name} " in question_lower or f"on {month_name}" in question_lower:
                filtered_df = df[df['date'].dt.month == month_num]
                return filtered_df, f"in {month_name.title()}"
        
        # Check for year-based filtering
        year_match = re.search(r'\b(20\d{2})\b', question_lower)
        if year_match:
            year = int(year_match.group(1))
            filtered_df = df[df['date'].dt.year == year]
            return filtered_df, f"in {year}"
        
        # No date filter found, return original data
        return df, ""
    def call_math_api(self, question, data_subset=None):
        """Perform accurate mathematical operations with proper filtering"""
        try:
            # Use specific data subset if provided, otherwise use full data
            analysis_data = data_subset if data_subset is not None else self.data.copy()
            
            # Apply date filtering if question contains date keywords
            analysis_data, date_filter_text = self.filter_by_date(analysis_data, question)
            
            # Clean quantity and rate data using robust cleaning function
            analysis_data = self.clean_quantity_data(analysis_data)
            
            # IMPORTANT: Filter out declined orders for accurate calculations
            valid_data = analysis_data[analysis_data['status'] != 'Declined'].copy()
            
            question_lower = question.lower()
            
            # Handle performance queries (agent vs customer)
            if (('best' in question_lower or 'top' in question_lower or 'highest' in question_lower or 
                 'performing' in question_lower or 'leader' in question_lower or 'winner' in question_lower)):
                
                # Check if it's about customers
                if ('customer' in question_lower or 'client' in question_lower or 'buyer' in question_lower):
                    return self._handle_customer_performance_query(valid_data, date_filter_text)
                # Check if it's about agents
                elif ('agent' in question_lower or 'person' in question_lower or 'who' in question_lower):
                    return self._handle_agent_performance_query(valid_data, date_filter_text)
                # Default to agent if ambiguous (maintain backward compatibility)
                else:
                    return self._handle_agent_performance_query(valid_data, date_filter_text)
            
            # Handle specific queries about weave, quality, composition
            elif 'most sold' in question_lower or ('highest' in question_lower and ('weave' in question_lower or 'quality' in question_lower or 'composition' in question_lower)) or 'best selling' in question_lower:
                return self._handle_most_sold_query(question_lower, valid_data, date_filter_text)
            elif 'least sold' in question_lower or ('lowest' in question_lower and ('weave' in question_lower or 'quality' in question_lower or 'composition' in question_lower)):
                return self._handle_least_sold_query(question_lower, valid_data, date_filter_text)
            elif 'compare' in question_lower:
                return self._handle_comparison_query(question_lower, valid_data)
            else:
                return self._handle_general_math_query(question_lower, valid_data, analysis_data, date_filter_text)
            
        except Exception as e:
            return f"Analysis failed: {str(e)}"
    
    def _handle_most_sold_query(self, question_lower, valid_data, date_filter_text=""):
        """Handle queries about most sold items"""
        if 'weave' in question_lower:
            # Group by weave (case-insensitive) and sum quantities
            valid_data_case_normalized = valid_data.copy()
            valid_data_case_normalized['weave_normalized'] = valid_data_case_normalized['weave'].str.lower()
            weave_sales = valid_data_case_normalized.groupby('weave_normalized')['quantity_clean'].sum().sort_values(ascending=False)
            top_weave = weave_sales.index[0]
            top_quantity = weave_sales.iloc[0]
            
            # Brief ranking
            ranking = "\n".join([f"{i}. {weave.title()}: {qty:,.0f}" for i, (weave, qty) in enumerate(weave_sales.head(3).items(), 1)])
            
            date_text = f" {date_filter_text}" if date_filter_text else ""
            response = f"Most sold weave{date_text}: **{top_weave}** ({top_quantity:,.0f} units)\n\nRanking:\n{ranking}\n\n*Calculation excludes declined orders*"
            return strip_summary_sections(response)
            
        elif 'quality' in question_lower:
            # Group by quality (case-insensitive) and sum quantities
            valid_data_case_normalized = valid_data.copy()
            valid_data_case_normalized['quality_normalized'] = valid_data_case_normalized['quality'].str.lower()
            quality_sales = valid_data_case_normalized.groupby('quality_normalized')['quantity_clean'].sum().sort_values(ascending=False)
            top_quality = quality_sales.index[0]
            top_quantity = quality_sales.iloc[0]
            
            # Brief ranking
            ranking = "\n".join([f"{i}. {quality.title()}: {qty:,.0f}" for i, (quality, qty) in enumerate(quality_sales.head(3).items(), 1)])
            
            date_text = f" {date_filter_text}" if date_filter_text else ""
            response = f"Most sold quality{date_text}: **{top_quality}** ({top_quantity:,.0f} units)\n\nRanking:\n{ranking}\n\n*Calculation excludes declined orders*"
            return strip_summary_sections(response)
            
        elif 'composition' in question_lower:
            # Group by composition (case-insensitive) and sum quantities
            valid_data_case_normalized = valid_data.copy()
            valid_data_case_normalized['composition_normalized'] = valid_data_case_normalized['composition'].str.lower()
            comp_sales = valid_data_case_normalized.groupby('composition_normalized')['quantity_clean'].sum().sort_values(ascending=False)
            top_comp = comp_sales.index[0]
            top_quantity = comp_sales.iloc[0]
            
            # Brief ranking
            ranking = "\n".join([f"{i}. {comp.title()}: {qty:,.0f}" for i, (comp, qty) in enumerate(comp_sales.head(3).items(), 1)])
            
            date_text = f" {date_filter_text}" if date_filter_text else ""
            response = f"Most sold composition{date_text}: **{top_comp}** ({top_quantity:,.0f} units)\n\nRanking:\n{ranking}\n\n*Calculation excludes declined orders*"
            return strip_summary_sections(response)
        
        return "Please specify: weave, quality, or composition type"
    
    def _handle_least_sold_query(self, question_lower, valid_data, date_filter_text=""):
        """Handle queries about least sold items"""
        date_text = f" {date_filter_text}" if date_filter_text else ""
        response = f"📉 LEAST SOLD ANALYSIS{date_text} (Declined orders excluded):\n\n"
        
        if 'weave' in question_lower:
            # Group by weave (case-insensitive) and sum quantities
            valid_data_case_normalized = valid_data.copy()
            valid_data_case_normalized['weave_normalized'] = valid_data_case_normalized['weave'].str.lower()
            weave_sales = valid_data_case_normalized.groupby('weave_normalized')['quantity_clean'].sum().sort_values(ascending=True)
            response += "🧵 WEAVE TYPE SALES (Lowest first):\n"
            for i, (weave, qty) in enumerate(weave_sales.head(5).items(), 1):
                response += f"{i}. {weave.title()}: {qty:,.0f} units\n"
            response += f"\n📉 LEAST SOLD WEAVE: {weave_sales.index[0].title()} with {weave_sales.iloc[0]:,.0f} units"
            
        elif 'quality' in question_lower:
            # Group by quality (case-insensitive) and sum quantities
            valid_data_case_normalized = valid_data.copy()
            valid_data_case_normalized['quality_normalized'] = valid_data_case_normalized['quality'].str.lower()
            quality_sales = valid_data_case_normalized.groupby('quality_normalized')['quantity_clean'].sum().sort_values(ascending=True)
            response += "⭐ QUALITY TYPE SALES (Lowest first):\n"
            for i, (quality, qty) in enumerate(quality_sales.head(5).items(), 1):
                response += f"{i}. {quality.title()}: {qty:,.0f} units\n"
            response += f"\n📉 LEAST SOLD QUALITY: {quality_sales.index[0].title()} with {quality_sales.iloc[0]:,.0f} units"
            
        elif 'composition' in question_lower:
            # Group by composition (case-insensitive) and sum quantities
            valid_data_case_normalized = valid_data.copy()
            valid_data_case_normalized['composition_normalized'] = valid_data_case_normalized['composition'].str.lower()
            comp_sales = valid_data_case_normalized.groupby('composition_normalized')['quantity_clean'].sum().sort_values(ascending=True)
            response += "🧪 COMPOSITION TYPE SALES (Lowest first):\n"
            for i, (comp, qty) in enumerate(comp_sales.head(5).items(), 1):
                response += f"{i}. {comp.title()}: {qty:,.0f} units\n"
            response += f"\n📉 LEAST SOLD COMPOSITION: {comp_sales.index[0].title()} with {comp_sales.iloc[0]:,.0f} units"
        
        return response
    
    def _handle_comparison_query(self, question_lower, valid_data):
        """Handle comparison queries"""
        response = "📊 COMPARATIVE ANALYSIS (Declined orders excluded):\n\n"
        
        # Compare by agent performance
        if 'agent' in question_lower:
            agent_stats = valid_data.groupby('agentName').agg({
                'quantity_clean': 'sum',
                'rate_clean': 'mean',
                '_id': 'count'
            }).round(2)
            agent_stats['revenue'] = valid_data.groupby('agentName').apply(
                lambda x: (x['quantity_clean'] * x['rate_clean']).sum()
            ).round(2)
            
            response += "👤 AGENT PERFORMANCE COMPARISON:\n"
            for agent in agent_stats.index:
                response += f"• {agent}: {agent_stats.loc[agent, '_id']} orders, "
                response += f"{agent_stats.loc[agent, 'quantity_clean']:,.0f} units, "
                response += f"${agent_stats.loc[agent, 'revenue']:,.2f} revenue\n"
        
        # Compare categories
        else:
            for category in ['weave', 'quality', 'composition']:
                if category in question_lower:
                    valid_data_case_normalized = valid_data.copy()
                    normalized_col = f'{category}_normalized'
                    valid_data_case_normalized[normalized_col] = valid_data_case_normalized[category].str.lower()
                    cat_stats = valid_data_case_normalized.groupby(normalized_col).agg({
                        'quantity_clean': 'sum',
                        'rate_clean': 'mean',
                        '_id': 'count'
                    }).round(2)
                    
                    response += f"📈 {category.upper()} COMPARISON:\n"
                    for item in cat_stats.index:
                        response += f"• {item.title()}: {cat_stats.loc[item, '_id']} orders, "
                        response += f"{cat_stats.loc[item, 'quantity_clean']:,.0f} units\n"
                    break
        
        return response
    
    def _handle_general_math_query(self, question_lower, valid_data, all_data, date_filter_text=""):
        """Handle general mathematical queries"""
        # Calculate statistics (excluding declined orders for business metrics)
        stats = {
            'total_valid_records': len(valid_data),
            'total_all_records': len(all_data),
            'total_quantity': valid_data['quantity_clean'].sum(),
            'total_revenue': (valid_data['quantity_clean'] * valid_data['rate_clean']).sum(),
            'average_rate': valid_data['rate_clean'].mean(),
            'average_quantity': valid_data['quantity_clean'].mean(),
            'declined_orders': len(all_data[all_data['status'] == 'Declined'])
        }
        
        # Add date context to responses
        date_text = f" {date_filter_text}" if date_filter_text else ""
        
        # Handle specific sales count queries (most common for date-based questions)
        if ('how many sales' in question_lower or 'sales happened' in question_lower or 
            'sales happened' in question_lower or 'give me the sales' in question_lower or
            'number of sales' in question_lower or 'count' in question_lower):
            if stats['total_all_records'] == 0:
                return f"No sales found{date_text}"
            
            # For specific date queries, provide detailed breakdown
            if 'on ' in date_text and stats['total_all_records'] > 0:
                # Show detailed breakdown for specific dates
                sales_details = []
                for _, row in valid_data.iterrows():
                    agent = row['agentName']
                    customer = row['customerName'] 
                    weave = row['weave']
                    quantity = row['quantity_clean']
                    revenue = row['quantity_clean'] * row['rate_clean']
                    sales_details.append(f"• {agent} → {customer}: {weave} weave, {quantity:,.0f} units, ${revenue:,.2f}")
                
                details_text = "\n".join(sales_details[:5])  # Show up to 5 sales
                if len(valid_data) > 5:
                    details_text += f"\n• ... and {len(valid_data)-5} more sales"
                
                response = f"""Sales{date_text}: **{stats['total_all_records']} total** ({stats['total_valid_records']} valid + {stats['declined_orders']} declined)
   
   **Sales Details:**
   {details_text}
   
   {stats['total_quantity']:,.0f} units, ${stats['total_revenue']:,.2f} revenue"""
                return strip_summary_sections(response)
            
            # Regular sales count response
            if stats['declined_orders'] > 0:
                return f"Sales{date_text}: **{stats['total_all_records']} total** ({stats['total_valid_records']} valid + {stats['declined_orders']} declined)\n\n*Valid sales exclude declined orders*"
            else:
                return f"Sales{date_text}: **{stats['total_valid_records']} sales**"
        
        # Generate concise response based on specific question
        if 'total' in question_lower and 'revenue' in question_lower:
            return f"Total revenue{date_text}: **${stats['total_revenue']:,.2f}**\n\n*Based on {stats['total_valid_records']} valid orders (excluding {stats['declined_orders']} declined)*"
            
        elif 'total' in question_lower and 'quantity' in question_lower:
            return f"Total quantity{date_text}: **{stats['total_quantity']:,.0f} units**\n\n*From {stats['total_valid_records']} valid orders (excluding {stats['declined_orders']} declined)*"
            
        elif 'average' in question_lower and 'rate' in question_lower:
            return f"Average rate{date_text}: **${stats['average_rate']:.2f}**\n\n*Calculated from {stats['total_valid_records']} valid orders*"
            
        elif 'average' in question_lower and 'quantity' in question_lower:
            return f"Average quantity{date_text}: **{stats['average_quantity']:,.0f} units per order**\n\n*Based on {stats['total_valid_records']} valid orders*"
        
        # Handle performance queries (agent vs customer)
        elif (('best' in question_lower or 'top' in question_lower or 'highest' in question_lower or 
               'performing' in question_lower or 'leader' in question_lower or 'winner' in question_lower)):
            
            # Check if it's about customers
            if ('customer' in question_lower or 'client' in question_lower or 'buyer' in question_lower):
                return self._handle_customer_performance_query(valid_data, date_text)
            # Check if it's about agents or default case
            else:
                return self._handle_agent_performance_query(valid_data, date_text)
        
        # Default comprehensive summary for general queries
        else:
            if stats['total_all_records'] == 0:
                return f"No data found{date_text}"
                
            success_rate = (stats['total_valid_records'] / stats['total_all_records'] * 100)
            response = f"""{date_text}:
• Valid orders: {stats['total_valid_records']} ({success_rate:.1f}% success rate)
• Total quantity: {stats['total_quantity']:,.0f} units
• Total revenue: ${stats['total_revenue']:,.2f}
• Average per order: {stats['average_quantity']:,.0f} units, ${stats['total_revenue'] / max(stats['total_valid_records'], 1):,.2f}

Analysis excludes {stats['declined_orders']} declined orders"""
            return strip_summary_sections(response)
    
    def _handle_agent_performance_query(self, valid_data, date_filter_text=""):
        """Handle agent performance queries"""
        if len(valid_data) == 0:
            return f"No agent data found{' ' + date_filter_text if date_filter_text else ''}"
        
        # Calculate comprehensive agent statistics
        agent_stats = valid_data.groupby('agentName').agg({
            'quantity_clean': 'sum',
            'rate_clean': 'mean',
            '_id': 'count'
        }).round(2)
        
        # Calculate revenue for each agent
        agent_revenue = valid_data.groupby('agentName').apply(
            lambda x: (x['quantity_clean'] * x['rate_clean']).sum()
        ).round(2)
        
        agent_stats['revenue'] = agent_revenue
        
        # Sort by revenue (best performing = highest revenue)
        agent_stats = agent_stats.sort_values('revenue', ascending=False)
        
        if len(agent_stats) == 0:
            return f"No agent performance data available{' ' + date_filter_text if date_filter_text else ''}"
        
        # Get the best performing agent
        best_agent = agent_stats.index[0]
        best_revenue = agent_stats.loc[best_agent, 'revenue']
        best_orders = agent_stats.loc[best_agent, '_id']
        best_quantity = agent_stats.loc[best_agent, 'quantity_clean']
        
        date_text = f" {date_filter_text}" if date_filter_text else ""
        
        # Create ranking
        ranking = []
        for i, (agent, stats) in enumerate(agent_stats.head(3).iterrows(), 1):
            ranking.append(f"{i}. {agent}: ${stats['revenue']:,.0f} revenue ({stats['_id']} orders, {stats['quantity_clean']:,.0f} units)")
        
        ranking_text = "\n".join(ranking)
        
        response = f"""Best performing agent{date_text}: **{best_agent}**

Performance: ${best_revenue:,.0f} revenue from {best_orders} orders ({best_quantity:,.0f} units)

**Ranking:**
{ranking_text}

*Analysis based on total revenue from valid orders*"""
        return strip_summary_sections(response)
    
    def _handle_customer_performance_query(self, valid_data, date_filter_text=""):
        """Handle customer performance queries"""
        if len(valid_data) == 0:
            return f"No customer data found{' ' + date_filter_text if date_filter_text else ''}"
        
        # Calculate comprehensive customer statistics
        customer_stats = valid_data.groupby('customerName').agg({
            'quantity_clean': 'sum',
            'rate_clean': 'mean',
            '_id': 'count'
        }).round(2)
        
        # Calculate revenue for each customer
        customer_revenue = valid_data.groupby('customerName').apply(
            lambda x: (x['quantity_clean'] * x['rate_clean']).sum()
        ).round(2)
        
        customer_stats['revenue'] = customer_revenue
        
        # Sort by revenue (best performing = highest revenue)
        customer_stats = customer_stats.sort_values('revenue', ascending=False)
        
        if len(customer_stats) == 0:
            return f"No customer performance data available{' ' + date_filter_text if date_filter_text else ''}"
        
        # Get the best performing customer
        best_customer = customer_stats.index[0]
        best_revenue = customer_stats.loc[best_customer, 'revenue']
        best_orders = customer_stats.loc[best_customer, '_id']
        best_quantity = customer_stats.loc[best_customer, 'quantity_clean']
        
        date_text = f" {date_filter_text}" if date_filter_text else ""
        
        # Create ranking
        ranking = []
        for i, (customer, stats) in enumerate(customer_stats.head(3).iterrows(), 1):
            ranking.append(f"{i}. {customer}: ${stats['revenue']:,.0f} revenue ({stats['_id']} orders, {stats['quantity_clean']:,.0f} units)")
        
        ranking_text = "\n".join(ranking)
        
        response = f"""Best performing customer{date_text}: **{best_customer}**

Performance: ${best_revenue:,.0f} revenue from {best_orders} orders ({best_quantity:,.0f} units)

**Ranking:**
{ranking_text}

*Analysis based on total revenue from valid orders*"""
        return strip_summary_sections(response)
    
    def call_math_api_with_agent_context(self, question, agent_data, agent_name):
        """Perform accurate mathematical operations with agent context"""
        try:
            # Clean the data using robust cleaning function
            agent_data = self.clean_quantity_data(agent_data.copy())
            
            # Filter out declined orders for business calculations
            valid_agent_data = agent_data[agent_data['status'] != 'Declined'].copy()
            
            # Calculate verified statistics
            agent_stats = {
                'total_sales': len(agent_data),  # All records including declined
                'valid_sales': len(valid_agent_data),  # Excluding declined
                'total_quantity': valid_agent_data['quantity_clean'].sum(),
                'total_revenue': (valid_agent_data['quantity_clean'] * valid_agent_data['rate_clean']).sum(),
                'declined_orders': len(agent_data[agent_data['status'] == 'Declined']),
                'average_rate': valid_agent_data['rate_clean'].mean(),
                'average_quantity': valid_agent_data['quantity_clean'].mean()
            }
            
            question_lower = question.lower()
            
            # Handle specific queries about most/least sold by this agent
            if 'most sold' in question_lower or 'highest' in question_lower or 'best selling' in question_lower or ('most' in question_lower and ('weave' in question_lower or 'quality' in question_lower or 'composition' in question_lower)):
                return self._handle_agent_most_sold(question_lower, valid_agent_data, agent_name)
            elif 'least sold' in question_lower or 'lowest' in question_lower:
                return self._handle_agent_least_sold(question_lower, valid_agent_data, agent_name)
            
            # Handle specific weave/quality/composition type queries
            elif any(weave_type in question_lower for weave_type in ['twill', 'plain', 'satin', 'linen', 'spandex']):
                return self._handle_specific_type_query(question_lower, valid_agent_data, agent_name, 'weave')
            elif any(quality_type in question_lower for quality_type in ['premium', 'standard', 'primium', 'premier']):
                return self._handle_specific_type_query(question_lower, valid_agent_data, agent_name, 'quality')
            elif any(comp_type in question_lower for comp_type in ['cotton', 'polyester', 'silk', 'wool']):
                return self._handle_specific_type_query(question_lower, valid_agent_data, agent_name, 'composition')
            
            # Generate concise response based on specific question
            elif 'how many sales' in question_lower or 'how many orders' in question_lower:
                if 'valid' in question_lower or 'successful' in question_lower:
                    return f"{agent_name}: **{agent_stats['valid_sales']} valid orders**\n\n*Excludes {agent_stats['declined_orders']} declined orders*"
                else:
                    return f"{agent_name}: **{agent_stats['total_sales']} total records** ({agent_stats['valid_sales']} valid + {agent_stats['declined_orders']} declined)"
                    
            elif 'total revenue' in question_lower:
                return f"{agent_name} total revenue: **${agent_stats['total_revenue']:,.2f}**\n\n*From {agent_stats['valid_sales']} valid orders*"
                
            elif 'total quantity' in question_lower:
                return f"{agent_name} total quantity: **{agent_stats['total_quantity']:,.0f} units**\n\n*From {agent_stats['valid_sales']} valid orders*"
            
            # Default comprehensive summary
            success_rate = (agent_stats['valid_sales'] / agent_stats['total_sales'] * 100)
            response = f"""{agent_name}:
• Valid orders: {agent_stats['valid_sales']} ({success_rate:.1f}% success rate)
• Total quantity: {agent_stats['total_quantity']:,.0f} units
• Total revenue: ${agent_stats['total_revenue']:,.2f}
• Average per order: {agent_stats['average_quantity']:,.0f} units, ${agent_stats['total_revenue'] / max(agent_stats['valid_sales'], 1):,.2f}

Analysis excludes {agent_stats['declined_orders']} declined orders"""
            return strip_summary_sections(response)
            
        except Exception as e:
            return f"Analysis failed: {str(e)}"
    
    def _handle_agent_most_sold(self, question_lower, valid_agent_data, agent_name):
        """Handle agent-specific most sold queries"""
        if 'weave' in question_lower:
            # Group by weave (case-insensitive) and sum quantities
            valid_agent_data_case_normalized = valid_agent_data.copy()
            valid_agent_data_case_normalized['weave_normalized'] = valid_agent_data_case_normalized['weave'].str.lower()
            weave_sales = valid_agent_data_case_normalized.groupby('weave_normalized')['quantity_clean'].sum().sort_values(ascending=False)
            if len(weave_sales) > 0:
                top_weave = weave_sales.index[0]
                top_quantity = weave_sales.iloc[0]
                ranking = "\n".join([f"{i}. {weave.title()}: {qty:,.0f}" for i, (weave, qty) in enumerate(weave_sales.head(3).items(), 1)])
                return f"{agent_name}'s most sold weave: **{top_weave.title()}** ({top_quantity:,.0f} units)\n\nRanking:\n{ranking}"
            else:
                return f"{agent_name} has no valid weave sales data"
                
        elif 'quality' in question_lower:
            # Group by quality (case-insensitive) and sum quantities
            valid_agent_data_case_normalized = valid_agent_data.copy()
            valid_agent_data_case_normalized['quality_normalized'] = valid_agent_data_case_normalized['quality'].str.lower()
            quality_sales = valid_agent_data_case_normalized.groupby('quality_normalized')['quantity_clean'].sum().sort_values(ascending=False)
            if len(quality_sales) > 0:
                top_quality = quality_sales.index[0]
                top_quantity = quality_sales.iloc[0]
                ranking = "\n".join([f"{i}. {quality.title()}: {qty:,.0f}" for i, (quality, qty) in enumerate(quality_sales.head(3).items(), 1)])
                return f"{agent_name}'s most sold quality: **{top_quality.title()}** ({top_quantity:,.0f} units)\n\nRanking:\n{ranking}"
            else:
                return f"{agent_name} has no valid quality sales data"
                
        elif 'composition' in question_lower:
            # Group by composition (case-insensitive) and sum quantities
            valid_agent_data_case_normalized = valid_agent_data.copy()
            valid_agent_data_case_normalized['composition_normalized'] = valid_agent_data_case_normalized['composition'].str.lower()
            comp_sales = valid_agent_data_case_normalized.groupby('composition_normalized')['quantity_clean'].sum().sort_values(ascending=False)
            if len(comp_sales) > 0:
                top_comp = comp_sales.index[0]
                top_quantity = comp_sales.iloc[0]
                ranking = "\n".join([f"{i}. {comp.title()}: {qty:,.0f}" for i, (comp, qty) in enumerate(comp_sales.head(3).items(), 1)])
                return f"{agent_name}'s most sold composition: **{top_comp.title()}** ({top_quantity:,.0f} units)\n\nRanking:\n{ranking}"
            else:
                return f"{agent_name} has no valid composition sales data"
        
        return f"Please specify: weave, quality, or composition for {agent_name}"
    
    def _handle_agent_least_sold(self, question_lower, valid_agent_data, agent_name):
        """Handle agent-specific least sold queries"""
        response = f"📉 {agent_name.upper()} - LEAST SOLD ANALYSIS:\n\n"
        
        if 'weave' in question_lower:
            # Group by weave (case-insensitive) and sum quantities
            valid_agent_data_case_normalized = valid_agent_data.copy()
            valid_agent_data_case_normalized['weave_normalized'] = valid_agent_data_case_normalized['weave'].str.lower()
            weave_sales = valid_agent_data_case_normalized.groupby('weave_normalized')['quantity_clean'].sum().sort_values(ascending=True)
            response += "🧵 WEAVE TYPE SALES BY THIS AGENT (Lowest first):\n"
            for i, (weave, qty) in enumerate(weave_sales.items(), 1):
                response += f"{i}. {weave.title()}: {qty:,.0f} units\n"
            if len(weave_sales) > 0:
                response += f"\n📉 {agent_name}'s LEAST SOLD WEAVE: {weave_sales.index[0].title()} with {weave_sales.iloc[0]:,.0f} units"
                
        elif 'quality' in question_lower:
            # Group by quality (case-insensitive) and sum quantities
            valid_agent_data_case_normalized = valid_agent_data.copy()
            valid_agent_data_case_normalized['quality_normalized'] = valid_agent_data_case_normalized['quality'].str.lower()
            quality_sales = valid_agent_data_case_normalized.groupby('quality_normalized')['quantity_clean'].sum().sort_values(ascending=True)
            response += "⭐ QUALITY TYPE SALES BY THIS AGENT (Lowest first):\n"
            for i, (quality, qty) in enumerate(quality_sales.items(), 1):
                response += f"{i}. {quality.title()}: {qty:,.0f} units\n"
            if len(quality_sales) > 0:
                response += f"\n📉 {agent_name}'s LEAST SOLD QUALITY: {quality_sales.index[0].title()} with {quality_sales.iloc[0]:,.0f} units"
                
        elif 'composition' in question_lower:
            # Group by composition (case-insensitive) and sum quantities
            valid_agent_data_case_normalized = valid_agent_data.copy()
            valid_agent_data_case_normalized['composition_normalized'] = valid_agent_data_case_normalized['composition'].str.lower()
            comp_sales = valid_agent_data_case_normalized.groupby('composition_normalized')['quantity_clean'].sum().sort_values(ascending=True)
            response += "🧪 COMPOSITION TYPE SALES BY THIS AGENT (Lowest first):\n"
            for i, (comp, qty) in enumerate(comp_sales.items(), 1):
                response += f"{i}. {comp.title()}: {qty:,.0f} units\n"
            if len(comp_sales) > 0:
                response += f"\n📉 {agent_name}'s LEAST SOLD COMPOSITION: {comp_sales.index[0].title()} with {comp_sales.iloc[0]:,.0f} units"
        
        return response
    
    def _handle_specific_type_query(self, question_lower, valid_agent_data, agent_name, category):
        """Handle queries about specific weave/quality/composition types for an agent"""
        if len(valid_agent_data) == 0:
            return f"{agent_name} has no valid {category} data"
        
        # Extract the specific type mentioned in the question
        if category == 'weave':
            type_keywords = ['twill', 'plain', 'satin', 'linen', 'spandex']
        elif category == 'quality':
            type_keywords = ['premium', 'standard', 'primium', 'premier']
        elif category == 'composition':
            type_keywords = ['cotton', 'polyester', 'silk', 'wool']
        
        # Find which type is mentioned in the question
        mentioned_type = None
        for type_kw in type_keywords:
            if type_kw in question_lower:
                mentioned_type = type_kw
                break
        
        if not mentioned_type:
            return f"No specific {category} type found in query"
        
        # Filter data for the specific type (case-insensitive matching)
        type_data = valid_agent_data[valid_agent_data[category].str.lower().str.contains(mentioned_type, na=False)]
        
        if len(type_data) == 0:
            return f"{agent_name} has no {mentioned_type} {category} sales"
        
        # Calculate statistics for this specific type
        total_quantity = type_data['quantity_clean'].sum()
        total_orders = len(type_data)
        total_revenue = (type_data['quantity_clean'] * type_data['rate_clean']).sum()
        
        return f"""{agent_name}'s {mentioned_type} {category} sales: **{total_quantity:,.0f} units**

Details: {total_orders} orders, ${total_revenue:,.2f} revenue
Average per order: {total_quantity / total_orders:,.0f} units"""
    
    def process_query(self, question, previous_context=""):
        # Check for specific agent queries with status filtering
        question_lower = question.lower()
        
        # Check for specific agent queries with status filtering (for confirmed/declined/pending orders)
        agent_status_keywords = ['confirmed orders', 'declined orders', 'pending orders']
        for status_keyword in agent_status_keywords:
            if status_keyword in question_lower and any(agent_name.lower() in question_lower for agent_name in ['mukilan', 'devaraj', 'boopalan']):
                # Extract agent name from the question
                agent_name = None
                for agent in ['mukilan', 'devaraj', 'boopalan']:
                    if agent in question_lower:
                        agent_name = agent.title()
                        break
                
                if agent_name:
                    # Get status from the keyword
                    status = status_keyword.split()[0].title()  # 'Confirmed', 'Declined', or 'Pending'
                    # Filter data by agent (case-insensitive) and status
                    agent_data = self.data[self.data['agentName'].str.lower() == agent_name.lower()].copy()
                    filtered_orders = agent_data[agent_data['status'].str.lower() == status.lower()].copy()
                    
                    # Return specific count without grouping
                    count = len(filtered_orders)
                    return f"{agent_name} has {count} {status.lower()} orders."
        
        # Check for other agent-specific queries
        agent_context = self.detect_agent_context(question, previous_context)
        if agent_context:
            # Filter data by agent
            working_data = self.filter_data_by_agent(agent_context)
            
            # Check if it's asking for specific status orders
            if 'confirmed orders' in question_lower:
                working_data = working_data[working_data['status'] == 'Confirmed']
            elif 'declined orders' in question_lower:
                working_data = working_data[working_data['status'] == 'Declined']
            elif 'pending orders' in question_lower:
                working_data = working_data[working_data['status'] == 'Pending']
            
            # Process based on query type
            query_type = self.detect_query_type(question)
            if query_type == "math":
                return self.call_math_api_with_agent_context(question, working_data, agent_context)
            elif query_type == "weave":
                weave_data = working_data[['date', 'weave', 'quantity', 'status', '_id', 'rate', 'agentName', 'customerName']].copy()
                if any(word in question_lower for word in ['total', 'sum', 'average', 'count', 'how many', 'most sold', 'highest', 'best selling', 'least sold', 'lowest']):
                    return self.call_math_api_with_agent_context(question, weave_data, agent_context)
                else:
                    weave_summary = f"{agent_context}'s weave data: {len(weave_data)} records\nTypes: {', '.join(weave_data['weave'].unique())}"
                    return weave_summary
            elif query_type == "quality":
                quality_data = working_data[['date', 'quality', 'quantity', 'status', '_id', 'rate', 'agentName', 'customerName']].copy()
                if any(word in question_lower for word in ['total', 'sum', 'average', 'count', 'how many', 'most sold', 'highest', 'best selling', 'least sold', 'lowest']):
                    return self.call_math_api_with_agent_context(question, quality_data, agent_context)
                else:
                    quality_summary = f"{agent_context}'s quality data: {len(quality_data)} records\nTypes: {', '.join(quality_data['quality'].unique())}"
                    return quality_summary
            elif query_type == "composition":
                composition_data = working_data[['date', 'composition', 'quantity', 'status', '_id', 'rate', 'agentName', 'customerName']].copy()
                if any(word in question_lower for word in ['total', 'sum', 'average', 'count', 'how many', 'most sold', 'highest', 'best selling', 'least sold', 'lowest']):
                    return self.call_math_api_with_agent_context(question, composition_data, agent_context)
                else:
                    comp_summary = f"{agent_context}'s composition data: {len(composition_data)} records\nTypes: {', '.join(composition_data['composition'].unique())}"
                    return comp_summary
            else:
                return f"{agent_context} data: {len(working_data)} records found"
        
        # Dynamically extract keywords from the dataset
        dynamic_keywords = self.get_dynamic_keywords()
        # Tokenize question and check for keywords
        question_tokens = set(re.findall(r'\w+', question.lower()))
        matched_keywords = dynamic_keywords.intersection(question_tokens)
        # Route 'best performing' queries to correct handler
        if 'best' in question_tokens or 'top' in question_tokens or 'highest' in question_tokens or 'performing' in question_tokens:
            # If weave/quality/composition keyword present, route accordingly
            if 'weave' in question_tokens:
                return self._handle_most_sold_query('weave', self.clean_quantity_data(self.data[self.data['status'] != 'Declined']), "")
            elif 'quality' in question_tokens:
                return self._handle_most_sold_query('quality', self.clean_quantity_data(self.data[self.data['status'] != 'Declined']), "")
            elif 'composition' in question_tokens:
                return self._handle_most_sold_query('composition', self.clean_quantity_data(self.data[self.data['status'] != 'Declined']), "")
            elif any(k in question_tokens for k in dynamic_keywords if k in self.data['agentName'].str.lower().unique()):
                return self._handle_agent_performance_query(self.clean_quantity_data(self.data[self.data['status'] != 'Declined']), "")
            else:
                # If ambiguous, reply with clarification
                return "Please specify: agent, weave, quality, or composition for best performing query."
        # New: Check context first
        context = self.get_question_context(question)
        # You can use 'context' to route or enhance answers
        # Example: print or log context for debugging
        # print(f"[DEBUG] Question context: {context}")
        """Main method to process any query and route to appropriate API"""
        query_type = self.detect_query_type(question)
        
        # Filter data by agent if context is detected
        working_data = self.data  # Start with all data
        
        if query_type == "math":
            return self.call_math_api(question, working_data)
        
        elif query_type == "weave":
            weave_data = working_data[['date', 'weave', 'quantity', 'status', '_id', 'rate', 'agentName', 'customerName']].copy()
            
            # Check if it's also a mathematical query about weave
            if any(word in question_lower for word in ['total', 'sum', 'average', 'count', 'how many', 'most sold', 'highest', 'best selling', 'least sold', 'lowest']):
                return self.call_math_api(question, weave_data)
            else:
                weave_summary = f"Weave data: {len(weave_data)} records\nTypes: {', '.join(weave_data['weave'].unique())}"
                return weave_summary
        
        elif query_type == "quality":
            quality_data = working_data[['date', 'quality', 'quantity', 'status', '_id', 'rate', 'agentName', 'customerName']].copy()
            
            # Check if it's also a mathematical query about quality
            if any(word in question_lower for word in ['total', 'sum', 'average', 'count', 'how many', 'most sold', 'highest', 'best selling', 'least sold', 'lowest']):
                return self.call_math_api(question, quality_data)
            else:
                quality_summary = f"Quality data: {len(quality_data)} records\nTypes: {', '.join(quality_data['quality'].unique())}"
                return quality_summary
        
        elif query_type == "composition":
            composition_data = working_data[['date', 'composition', 'quantity', 'status', '_id', 'rate', 'agentName', 'customerName']].copy()
            
            # Check if it's also a mathematical query about composition
            if any(word in question_lower for word in ['total', 'sum', 'average', 'count', 'how many', 'most sold', 'highest', 'best selling', 'least sold', 'lowest']):
                return self.call_math_api(question, composition_data)
            else:
                comp_summary = f"Composition data: {len(composition_data)} records\nTypes: {', '.join(composition_data['composition'].unique())}"
                return comp_summary
        
        elif query_type == "customer":
            # Handle customer-specific queries with analysis
            return self._handle_customer_query(question, working_data)
        
        else:
            return f"General data: {len(working_data)} total records"

    def _handle_customer_query(self, question, data):
        """Handle customer-specific queries with proper analysis"""
        question_lower = question.lower()
        
        # Clean and prepare data
        cleaned_data = self._clean_data_for_analysis(data)
        
        # Check if this is a customer-agent relationship query
        # If data has been pre-filtered by agent, this means we're looking for customers of that agent
        agent_names = ['mukilan', 'devaraj', 'boopalan']
        mentioned_agent = None
        for agent in agent_names:
            if agent in question_lower:
                mentioned_agent = agent.title()
                break
        
        # If agent is mentioned and data size suggests filtering, this is a customer-agent relationship query
        if mentioned_agent and len(cleaned_data) < 18:  # Less than total records means pre-filtered
            # This is asking "which customers placed orders with agent X"
            if cleaned_data.empty:
                return f"No customers found who placed orders with agent {mentioned_agent}"
            
            # Get unique customers for this agent
            customers_list = cleaned_data['customerName'].dropna().unique()
            
            if len(customers_list) == 0:
                return f"No customers found who placed orders with agent {mentioned_agent}"
            
            # Build detailed customer-agent relationship analysis
            response = f"**Customers who placed orders with Agent {mentioned_agent}:**\n\n"
            
            total_customers = len(customers_list)
            total_orders = len(cleaned_data)
            total_revenue = (cleaned_data['quantity_clean'] * cleaned_data['rate']).sum()
            
            # Remove the summary line to avoid displaying it
            # response += f"📊 Summary: {total_customers} customers, {total_orders} orders, ₹{total_revenue:.2f} total revenue\n\n"
            
            # Analyze each customer's relationship with this agent
            for customer in customers_list:
                customer_orders = cleaned_data[cleaned_data['customerName'] == customer]
                customer_total_qty = customer_orders['quantity_clean'].sum()
                customer_revenue = (customer_orders['quantity_clean'] * customer_orders['rate']).sum()
                customer_order_count = len(customer_orders)
                
                response += f"👤 **{customer}**:\n"
                response += f"   • {customer_order_count} orders, {customer_total_qty} units, ₹{customer_revenue:.2f} revenue\n"
                
                # Show recent orders
                recent_orders = customer_orders.head(3)
                for _, order in recent_orders.iterrows():
                    order_revenue = order['quantity_clean'] * order['rate']
                    response += f"   • {order['date']}: {order['quantity_clean']} units of {order['weave']} {order['quality']} (₹{order_revenue:.2f})\n"
                
                if len(customer_orders) > 3:
                    response += f"   • ... and {len(customer_orders) - 3} more orders\n"
                response += "\n"
            
            return response
        
        # Extract customer name from question for individual customer analysis
        customer_name = self._extract_customer_name(question, cleaned_data)
        
        if customer_name:
            # Filter data for specific customer
            customer_data = cleaned_data[cleaned_data['customerName'].str.contains(customer_name, case=False, na=False)]
            
            if customer_data.empty:
                return f"No orders found for customer '{customer_name}'"
            
            # Analyze customer data
            total_orders = len(customer_data)
            total_quantity = customer_data['quantity_clean'].sum()
            total_revenue = (customer_data['quantity_clean'] * customer_data['rate']).sum()
            avg_order_size = customer_data['quantity_clean'].mean()
            
            # Get order details
            order_details = []
            for _, order in customer_data.iterrows():
                revenue = order['quantity_clean'] * order['rate']
                order_details.append(f"• {order['date']}: {order['quantity_clean']} units of {order['weave']} {order['quality']} at ₹{order['rate']}/unit (Total: ₹{revenue:.2f})")
            
            # Build response
            response = f"**Customer Analysis: {customer_name}**\n"
            # Remove the summary line to avoid displaying it
            # response += f"📊 Summary: {total_orders} orders, {total_quantity} total units, ₹{total_revenue:.2f} revenue\n"
            response += f"📈 Average Order: {avg_order_size:.1f} units per order\n\n"
            response += f"Order Details:\n" + "\n".join(order_details)
            
            return strip_summary_sections(response)
        else:
            # General customer analysis
            if 'details' in question_lower or 'list' in question_lower:
                # Show all customers with their order counts
                customer_summary = cleaned_data.groupby('customerName').agg({
                    'quantity_clean': ['count', 'sum'],
                    'rate': 'first'
                }).round(2)
                
                customer_summary.columns = ['Orders', 'Total_Quantity', 'Sample_Rate']
                customer_summary['Revenue'] = (cleaned_data.groupby('customerName').apply(
                    lambda x: (x['quantity_clean'] * x['rate']).sum()
                )).round(2)
                
                response = "**All Customers Analysis:**\n"
                for customer, row in customer_summary.iterrows():
                    response += f"• **{customer}**: {row['Orders']} orders, {row['Total_Quantity']} units, ₹{row['Revenue']} revenue\n"
                
                return response
            else:
                # Fallback to mathematical analysis
                return self.call_math_api(question, cleaned_data)
    
    def _clean_data_for_analysis(self, data):
        """Clean data for numerical analysis"""
        import re
        
        data_clean = data.copy()
        
        # Clean quantity column
        def clean_quantity(qty):
            if pd.isna(qty):
                return 0
            
            qty_str = str(qty).strip().lower()
            
            # Extract numbers from strings with units
            numbers = re.findall(r'\d+', qty_str)
            if numbers:
                return float(numbers[0])  # Take the first number found
            else:
                return 0  # For invalid entries like 'tyy', 'g', 'fhy'
        
        data_clean['quantity_clean'] = data_clean['quantity'].apply(clean_quantity)
        
        # Ensure rate is numeric
        data_clean['rate'] = pd.to_numeric(data_clean['rate'], errors='coerce').fillna(0)
        
        return data_clean
    
    def _extract_customer_name(self, question, data):
        """Extract customer name from the question"""
        # Get unique customer names from data
        customer_names = data['customerName'].dropna().unique()
        
        # Look for customer names in the question (case insensitive)
        question_lower = question.lower()
        
        # First try exact matches
        for customer in customer_names:
            if customer.lower() in question_lower:
                return customer
        
        # Then try partial matches (customer name contains part of question or vice versa)
        for customer in customer_names:
            customer_parts = customer.lower().split()
            for part in customer_parts:
                if len(part) > 2 and part in question_lower:  # Avoid short matches like 'T'
                    return customer
        
        # Look for quoted names
        import re
        quoted_names = re.findall(r"'([^']*)'|\"([^\"]*)\"", question)
        for quoted_name in quoted_names:
            name = quoted_name[0] or quoted_name[1]  # Handle both single and double quotes
            if name:
                # Check if this name exists in our data (partial match)
                for customer in customer_names:
                    if name.lower() in customer.lower() or customer.lower() in name.lower():
                        return customer
        
        # Try to find any customer name parts in the question
        words_in_question = re.findall(r'\b\w+\b', question_lower)
        for customer in customer_names:
            customer_words = re.findall(r'\b\w+\b', customer.lower())
            for customer_word in customer_words:
                if len(customer_word) > 3 and customer_word in words_in_question:
                    return customer
        
        return None

# Individual API Classes for specific purposes
class WeaveAPI:
    def __init__(self, csv_path="data/database_data.csv"):
        self.data = pd.read_csv(csv_path)
    
    def get_weave_data(self):
        """Returns weave-specific data"""
        columns = ['date', 'weave', 'quantity', 'status', '_id', 'rate', 'agentName', 'customerName']
        return self.data[columns].copy()
    
    def get_weave_summary(self):
        """Returns summary of weave data"""
        weave_data = self.get_weave_data()
        return {
            "total_records": len(weave_data),
            "unique_weaves": weave_data['weave'].nunique(),
            "weave_types": list(weave_data['weave'].unique()),
            "weave_counts": weave_data['weave'].value_counts().to_dict()
        }

class QualityAPI:
    def __init__(self, csv_path="data/database_data.csv"):
        self.data = pd.read_csv(csv_path)
    
    def get_quality_data(self):
        """Returns quality-specific data"""
        columns = ['date', 'quality', 'quantity', 'status', '_id', 'rate', 'agentName', 'customerName']
        return self.data[columns].copy()
    
    def get_quality_summary(self):
        """Returns summary of quality data"""
        quality_data = self.get_quality_data()
        return {
            "total_records": len(quality_data),
            "unique_qualities": quality_data['quality'].nunique(),
            "quality_types": list(quality_data['quality'].unique()),
            "quality_counts": quality_data['quality'].value_counts().to_dict()
        }

class CompositionAPI:
    def __init__(self, csv_path="data/database_data.csv"):
        self.data = pd.read_csv(csv_path)
    
    def get_composition_data(self):
        """Returns composition-specific data"""
        columns = ['date', 'composition', 'quantity', 'status', '_id', 'rate', 'agentName', 'customerName']
        return self.data[columns].copy()
    
    def get_composition_summary(self):
        """Returns summary of composition data"""
        composition_data = self.get_composition_data()
        return {
            "total_records": len(composition_data),
            "unique_compositions": composition_data['composition'].nunique(),
            "composition_types": list(composition_data['composition'].unique()),
            "composition_counts": composition_data['composition'].value_counts().to_dict()
        }

# Factory function to create the smart API handler
def create_smart_api_handler(csv_path="data/database_data.csv"):
    """Factory function to create a smart API handler"""
    return SmartAPIHandler(csv_path)
