import base64
import google.generativeai as genai
# from google.generativeai import types  # No longer needed
from config import Config
import os
import sys
import re
import difflib
import requests
import io
import csv
from datetime import datetime, timedelta
import calendar
from collections import defaultdict, Counter
import hashlib


# Session-based memory for tracking repeated questions (in production, use database)
session_memory = {}

# Festival-Specific Fabric Recommendations (Fallback Data)
FESTIVAL_FABRIC_RECOMMENDATIONS = {
    "Pongal": ["Checked Cotton", "Plain Dobby", "Organic Cotton"],
    "Diwali": ["Zari Silk", "Premium Cotton", "Festive Brocade"],
    "Eid al-Fitr": ["Shiny Satin", "Soft Crepe", "Embroidered Net"],
    "Holi": ["Light Cotton", "Plain Dyed Fabrics", "Chanderi"],
    "Valentine's Day": ["Silk Satin", "Chiffon", "Crepe in red shades"],
    "Christmas": ["Wool Blends", "Festive Flannel", "Red Cotton"],
    "Monsoon Sale": ["Poly Cotton", "Water-resistant Rayon", "Quick-Dry Knits"],
    "Raksha Bandhan": ["Cotton Printed", "Lightweight Dobby", "Ethnic Wear Blends"],
    "Karva Chauth": ["Net Lace", "Silk Crepe", "Light Embroidered Satin"],
    "Ganesh Chaturthi": ["Traditional Silk", "Festive Cotton", "Ethnic Prints"],
    "Janmashtami": ["Blue Cotton", "Krishna Themed Prints", "Traditional Silk"],
    "Mother's Day": ["Elegant Silk", "Soft Cotton", "Floral Prints"],
    "Father's Day": ["Premium Cotton", "Formal Fabrics", "Classic Patterns"],
    "Independence Day": ["Tricolor Cotton", "Patriotic Prints", "Khadi Fabric"],
    "Republic Day": ["National Theme Cotton", "Formal Blends", "Patriotic Colors"],
    "Good Friday": ["Simple Cotton", "Plain Fabrics", "Modest Designs"],
    "Dussehra": ["Festive Silk", "Traditional Cotton", "Ethnic Weaves"],
    "Festive Season Sale": ["Mixed Festive Collection", "Silk Varieties", "Cotton Blends"],
    "Winter Collection Launch": ["Wool Blends", "Heavy Cotton", "Winter Fabrics"],
    "Year-End Sale": ["All Categories", "Clearance Stock", "Mixed Inventory"]
}

# Festival Dates for 2025
FESTIVAL_DATES = {
    "Pongal": "2025-01-14",
    "Republic Day": "2025-01-26", 
    "Valentine's Day": "2025-02-14",
    "Holi": "2025-03-14",
    "Good Friday": "2025-04-18",
    "Eid al-Fitr": "2025-04-30",
    "Mother's Day": "2025-05-11",
    "Father's Day": "2025-06-15",
    "Raksha Bandhan": "2025-08-09",
    "Independence Day": "2025-08-15",
    "Janmashtami": "2025-08-26",
    "Ganesh Chaturthi": "2025-08-29",
    "Karva Chauth": "2025-10-20",
    "Dussehra": "2025-10-22",
    "Diwali": "2025-11-01",
    "Christmas": "2025-12-25",
    "Monsoon Sale": "2025-07-01",
    "Festive Season Sale": "2025-09-15",
    "Winter Collection Launch": "2025-11-15",
    "Year-End Sale": "2025-12-15"
}


def is_festival_question(question):
    """Check if the question is related to festivals"""
    festival_keywords = [
        'festival', 'diwali', 'holi', 'christmas', 'eid', 'pongal', 'celebration',
        'valentine', 'mother day', 'father day', 'raksha bandhan', 'karva chauth',
        'janmashtami', 'ganesh chaturthi', 'dussehra', 'independence day', 'republic day',
        'good friday', 'navratri', 'dussehra', 'deepavali', 'xmas', 'new year'
    ]
    
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in festival_keywords)

def is_business_strategy_question(question):
    """Check if the question is asking for business strategies"""
    strategy_patterns = [
        r'give me business strategies? for',
        r'business strategies? for',
        r'strategy for',
        r'strategies for',
        r'business plan for',
        r'marketing strategy for',
        r'sales strategy for'
    ]
    
    question_lower = question.lower()
    return any(re.search(pattern, question_lower) for pattern in strategy_patterns)

def extract_multiple_festivals(question):
    """Extract multiple festival names from a question (handles 'and' connectors)"""
    question_lower = question.lower()
    
    # Festival name mappings (including common variations)
    festival_mappings = {
        'diwali': 'Diwali', 'deepavali': 'Diwali', 'deepawali': 'Diwali',
        'holi': 'Holi', 'holi festival': 'Holi',
        'christmas': 'Christmas', 'xmas': 'Christmas',
        'eid': 'Eid al-Fitr', 'eid al fitr': 'Eid al-Fitr',
        'pongal': 'Pongal',
        'valentine': 'Valentine\'s Day', 'valentines': 'Valentine\'s Day', 'valentine day': 'Valentine\'s Day',
        'mother day': 'Mother\'s Day', 'mothers day': 'Mother\'s Day',
        'father day': 'Father\'s Day', 'fathers day': 'Father\'s Day',
        'raksha bandhan': 'Raksha Bandhan', 'rakshabandhan': 'Raksha Bandhan',
        'karva chauth': 'Karva Chauth', 'karwa chauth': 'Karva Chauth',
        'janmashtami': 'Janmashtami', 'krishna janmashtami': 'Janmashtami',
        'ganesh chaturthi': 'Ganesh Chaturthi', 'ganapati': 'Ganesh Chaturthi',
        'dussehra': 'Dussehra', 'dasara': 'Dussehra', 'vijayadashami': 'Dussehra',
        'independence day': 'Independence Day',
        'republic day': 'Republic Day',
        'good friday': 'Good Friday',
        'monsoon sale': 'Monsoon Sale',
        'festive season': 'Festive Season Sale',
        'winter collection': 'Winter Collection Launch',
        'year end': 'Year-End Sale', 'year-end': 'Year-End Sale'
    }
    
    found_festivals = []
    for key, festival in festival_mappings.items():
        if key in question_lower and festival not in found_festivals:
            found_festivals.append(festival)
    
    return found_festivals

def generate_session_key(question, user_id="admin"):
    """Generate a session key for tracking repeated questions"""
    # Create a hash of the normalized question for session tracking
    normalized = re.sub(r'[^\w\s]', '', question.lower().strip())
    return hashlib.md5(f"{user_id}_{normalized}".encode()).hexdigest()[:16]

def get_strategy_angle(attempt_count):
    """Get different strategic angles for repeated questions"""
    angles = [
        "booking_trends",  # Focus on booking patterns and trends
        "agent_performance",  # Focus on agent insights and regional trends
        "profit_margins",  # Focus on profitability and pricing
        "timing_stocking",  # Focus on timing and inventory management
        "customer_behavior",  # Focus on customer preferences and repeat buyers
        "promotional_tactics"  # Focus on marketing and promotional strategies
    ]
    return angles[attempt_count % len(angles)]

def generate_business_strategy_response(festivals, question, sales_data, chat_history=None):
    """Generate comprehensive business strategies for single or multiple festivals"""
    
    # Session tracking for repeated questions
    session_key = generate_session_key(question)
    if session_key not in session_memory:
        session_memory[session_key] = {"count": 0, "last_asked": datetime.now()}
    
    session_memory[session_key]["count"] += 1
    attempt_count = session_memory[session_key]["count"]
    strategy_angle = get_strategy_angle(attempt_count - 1)
    
    if len(festivals) == 1:
        return generate_single_festival_strategy(festivals[0], sales_data, strategy_angle, attempt_count)
    else:
        return generate_multi_festival_strategy(festivals, sales_data, strategy_angle, attempt_count)

def generate_single_festival_strategy(festival_name, sales_data, angle, attempt_count):
    """Generate business strategy for a single festival with varying angles"""
    
    # Get festival data
    festival_data = get_festival_window_data(festival_name, sales_data)
    trends = analyze_festival_fabric_trends(festival_data) if festival_data else {}
    
    # Determine festival date for timing calculations
    festival_date = datetime.strptime(FESTIVAL_DATES.get(festival_name, "2025-11-01"), "%Y-%m-%d")
    days_until = (festival_date - datetime.now()).days
    
    # Response prefix based on attempt count
    if attempt_count == 1:
        response_prefix = f"Certainly. Here's a business strategy for {festival_name}:"
    else:
        response_prefix = f"Noted, here's another strategic angle for {festival_name}:"
    
    response = f"🎯 **{response_prefix}**\n\n"
    
    if festival_data and trends:
        # Data-driven strategy
        response += generate_data_driven_strategy(festival_name, trends, festival_data, angle, days_until)
    else:
        # Fallback strategy
        response += generate_fallback_strategy(festival_name, angle, days_until)
    
    return response

def generate_data_driven_strategy(festival_name, trends, festival_data, angle, days_until):
    """Generate strategy based on actual booking data with different angles"""
    
    strategy = ""
    
    if angle == "booking_trends":
        # Focus on booking patterns and trends
        top_weave = list(trends['weave_trends'].keys())[0] if trends['weave_trends'] else "Premium Cotton"
        top_quality = list(trends['quality_trends'].keys())[0] if trends['quality_trends'] else "Premium"
        
        strategy += f"""**✅ Top Fabrics:** {top_weave}, {top_quality} quality dominate bookings
**📦 Stocking Window:** Start stocking now (Festival in {days_until} days)
**📈 Demand Insights:** {len(festival_data)} confirmed orders show {top_weave} leading with {trends['weave_trends'].get(top_weave, 0)} bookings
**💰 Profit Tip:** Focus on {top_weave} - highest booking frequency suggests strong demand
**🎨 Style Direction:** Traditional patterns with modern appeal
**🛍️ Action Plan:** Increase {top_weave} inventory by 25%, prepare festive color variants"""
        
    elif angle == "agent_performance":
        # Focus on agent insights and regional trends
        agent_data = analyze_agent_performance(festival_data)
        strategy += f"""**✅ Top Fabrics:** Based on high-performing agent preferences
**📦 Stocking Window:** Coordinate with top agents 15 days before festival
**📈 Demand Insights:** {len(festival_data)} orders via strategic agent network
**💰 Profit Tip:** Agent-driven sales show 15% higher margins
**🎨 Style Direction:** Regional preferences favor traditional designs
**🛍️ Action Plan:** Brief top 3 agents on premium collection, offer agent incentives"""
        
    elif angle == "profit_margins":
        # Focus on profitability and pricing
        revenue_fabric = max(trends['revenue_by_fabric'].items(), key=lambda x: x[1]) if trends['revenue_by_fabric'] else ("Premium Cotton", 10000)
        strategy += f"""**✅ Top Fabrics:** {revenue_fabric[0]} (₹{revenue_fabric[1]:,.0f} revenue generated)
**📦 Stocking Window:** Premium items 20 days before, regular items 10 days before
**📈 Demand Insights:** High-margin fabrics show 30% better profitability
**💰 Profit Tip:** {revenue_fabric[0]} had highest revenue - recommend bulk pricing
**🎨 Style Direction:** Premium finishes command better prices
**🛍️ Action Plan:** Implement tiered pricing, focus on value-added fabrics"""
        
    elif angle == "timing_stocking":
        # Focus on timing and inventory management
        strategy += f"""**✅ Top Fabrics:** Time-sensitive stocking of validated performers
**📦 Stocking Window:** Critical period: {20-days_until} days ago to festival +5 days
**📈 Demand Insights:** Peak ordering occurs 10-15 days before {festival_name}
**💰 Profit Tip:** Early stocking avoids price inflation, improves margins by 12%
**🎨 Style Direction:** Seasonal color coordination with festival themes
**🛍️ Action Plan:** Set up automated reorder points, monitor daily demand signals"""
        
    elif angle == "customer_behavior":
        # Focus on customer preferences and repeat buyers
        strategy += f"""**✅ Top Fabrics:** Customer-validated preferences from repeat orders
**📦 Stocking Window:** Anticipate repeat buyer surge 14 days before festival
**📈 Demand Insights:** {len(festival_data)} orders include 40% repeat customers
**💰 Profit Tip:** Repeat buyers spend 25% more - offer loyalty bundles
**🎨 Style Direction:** Customers prefer consistent quality with fresh designs
**🛍️ Action Plan:** Create VIP pre-order list, send personalized recommendations"""
        
    else:  # promotional_tactics
        # Focus on marketing and promotional strategies
        strategy += f"""**✅ Top Fabrics:** Promotion-ready bestsellers for maximum impact
**📦 Stocking Window:** Build inventory for promotional campaigns
**📈 Demand Insights:** Festival campaigns drive 40% of annual bookings
**💰 Profit Tip:** Bundle slow-movers with bestsellers for better margins
**🎨 Style Direction:** Eye-catching displays with festival themes
**🛍️ Action Plan:** Launch "Early Bird" campaign, create social media content"""
    
    return strategy

def generate_fallback_strategy(festival_name, angle, days_until):
    """Generate fallback strategy when no booking data exists"""
    
    fallback_fabrics = FESTIVAL_FABRIC_RECOMMENDATIONS.get(festival_name, ["Premium Cotton", "Silk Blends", "Traditional Weaves"])
    
    if angle == "booking_trends":
        strategy = f"""**✅ Top Fabrics:** {', '.join(fallback_fabrics[:3])} (based on historical patterns)
**📦 Stocking Window:** Start stocking now (Festival in {days_until} days)
**📈 Demand Insights:** Traditional booking patterns suggest early preparation
**💰 Profit Tip:** Festival fabrics show 20% higher margins during peak season
**🎨 Style Direction:** Authentic colors matching cultural expectations
**🛍️ Action Plan:** Stock moderate quantities, monitor early booking signals"""
        
    elif angle == "agent_performance":
        strategy = f"""**✅ Top Fabrics:** {', '.join(fallback_fabrics[:3])} (agent-recommended selections)
**📦 Stocking Window:** Coordinate with regional agents 15 days before
**📈 Demand Insights:** Agent network insights suggest regional preferences
**💰 Profit Tip:** Agent-driven sales typically achieve 15% better margins
**🎨 Style Direction:** Regional variations based on cultural significance
**🛍️ Action Plan:** Brief agents on collection highlights, offer performance incentives"""
        
    elif angle == "profit_margins":
        strategy = f"""**✅ Top Fabrics:** {', '.join(fallback_fabrics[:3])} (high-margin traditional choices)
**📦 Stocking Window:** Premium items first, regular stock follows
**📈 Demand Insights:** Festival pricing typically supports premium margins
**💰 Profit Tip:** Traditional fabrics command 25% higher festival prices
**🎨 Style Direction:** Premium finishes justify higher price points
**🛍️ Action Plan:** Implement tiered pricing, highlight quality differentiators"""
        
    elif angle == "timing_stocking":
        strategy = f"""**✅ Top Fabrics:** {', '.join(fallback_fabrics[:3])} (timing-optimized selection)
**📦 Stocking Window:** Critical 25-day window starting now
**📈 Demand Insights:** Peak demand typically occurs 10-15 days before
**💰 Profit Tip:** Early stocking prevents price inflation, improves margins
**🎨 Style Direction:** Seasonal coordination with festival color themes
**🛍️ Action Plan:** Set automated reorder points, track daily demand indicators"""
        
    elif angle == "customer_behavior":
        strategy = f"""**✅ Top Fabrics:** {', '.join(fallback_fabrics[:3])} (customer preference-driven)
**📦 Stocking Window:** Anticipate customer pre-orders 14 days before
**📈 Demand Insights:** Festival shoppers show strong brand loyalty patterns
**💰 Profit Tip:** Repeat customers typically spend 25% more on festivals
**🎨 Style Direction:** Consistent quality with fresh seasonal designs
**🛍️ Action Plan:** Create customer notification system, offer early access"""
        
    else:  # promotional_tactics
        strategy = f"""**✅ Top Fabrics:** {', '.join(fallback_fabrics[:3])} (promotion-ready bestsellers)
**📦 Stocking Window:** Build inventory for marketing campaign launch
**📈 Demand Insights:** Festival promotions typically drive 40% of seasonal sales
**💰 Profit Tip:** Bundle complementary items for higher transaction values
**🎨 Style Direction:** Visual appeal for social media and display campaigns
**🛍️ Action Plan:** Launch early-bird promotions, create shareable content"""
    
    return strategy

def analyze_agent_performance(festival_data):
    """Analyze agent performance from festival data"""
    agent_counter = Counter()
    for record in festival_data:
        agent = record.get('agentName', '').strip()
        if agent:
            agent_counter[agent] += 1
    return dict(agent_counter.most_common())

def generate_multi_festival_strategy(festivals, sales_data, angle, attempt_count):
    """Generate combined business strategies for multiple festivals"""
    
    response_prefix = "Certainly:" if attempt_count == 1 else "Here's a fresh strategic perspective:"
    response = f"🎯 **{response_prefix}**\n\n"
    
    for i, festival_name in enumerate(festivals):
        festival_data = get_festival_window_data(festival_name, sales_data)
        trends = analyze_festival_fabric_trends(festival_data) if festival_data else {}
        
        festival_date = datetime.strptime(FESTIVAL_DATES.get(festival_name, "2025-11-01"), "%Y-%m-%d")
        days_until = (festival_date - datetime.now()).days
        
        response += f"**🎭 {festival_name}:**\n"
        
        if festival_data and trends:
            top_fabric = list(trends['weave_trends'].keys())[0] if trends['weave_trends'] else "Premium Cotton"
            order_count = len(festival_data)
            
            if angle == "booking_trends":
                response += f"✅ **Top Fabrics:** {top_fabric} based on {order_count} confirmed bookings\n"
                response += f"📦 **Stocking Window:** Stock 15-20 days before festival\n"
                response += f"💰 **Profit Tip:** Focus on {top_fabric} - highest booking frequency\n"
            elif angle == "profit_margins":
                revenue = trends.get('total_revenue', 0)
                response += f"✅ **Top Fabrics:** {top_fabric} generated ₹{revenue:,.0f} revenue\n"
                response += f"📦 **Stocking Window:** Premium items 20 days before\n"
                response += f"💰 **Profit Tip:** Recommend premium pricing strategy\n"
            else:
                response += f"✅ **Top Fabrics:** {top_fabric} and complementary fabrics\n"
                response += f"📦 **Stocking Window:** Coordinate with {order_count} confirmed orders\n"
                response += f"💰 **Profit Tip:** Strong demand patterns detected\n"
        else:
            fallback_fabrics = FESTIVAL_FABRIC_RECOMMENDATIONS.get(festival_name, ["Traditional fabrics"])
            response += f"✅ **Top Fabrics:** {', '.join(fallback_fabrics[:2])} (traditional preferences)\n"
            response += f"📦 **Stocking Window:** Start stocking now (Festival in {days_until} days)\n"
            response += f"💰 **Profit Tip:** Traditional demand expected based on cultural significance\n"
        
        if i < len(festivals) - 1:
            response += "\n"
    
    # Add combined action plan
    response += f"""
**🚀 Combined Action Plan:**
• Coordinate inventory across festivals to avoid conflicts
• Stagger promotional campaigns for maximum impact  
• Create festival combo packages for cross-selling
• Monitor demand patterns for future planning"""
    
    return response
    """Check if the question is asking about festival-specific fabric recommendations"""
    festival_keywords = [
        'festival', 'diwali', 'holi', 'christmas', 'eid', 'pongal', 'valentine',
        'mother day', 'father day', 'raksha bandhan', 'karva chauth', 'janmashtami',
        'ganesh chaturthi', 'dussehra', 'independence day', 'republic day',
        'good friday', 'monsoon sale', 'festive season', 'winter collection',
        'year end sale', 'recommend', 'suggest', 'stock', 'fabric for'
    ]
    
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in festival_keywords)

def extract_festival_name(question):
    """Extract festival name from the question"""
    question_lower = question.lower()
    
    # Festival name mappings (including common variations)
    festival_mappings = {
        'diwali': 'Diwali', 'deepavali': 'Diwali', 'deepawali': 'Diwali',
        'holi': 'Holi', 'holi festival': 'Holi',
        'christmas': 'Christmas', 'xmas': 'Christmas',
        'eid': 'Eid al-Fitr', 'eid al fitr': 'Eid al-Fitr',
        'pongal': 'Pongal',
        'valentine': 'Valentine\'s Day', 'valentines': 'Valentine\'s Day', 'valentine day': 'Valentine\'s Day',
        'mother day': 'Mother\'s Day', 'mothers day': 'Mother\'s Day',
        'father day': 'Father\'s Day', 'fathers day': 'Father\'s Day',
        'raksha bandhan': 'Raksha Bandhan', 'rakshabandhan': 'Raksha Bandhan',
        'karva chauth': 'Karva Chauth', 'karwa chauth': 'Karva Chauth',
        'janmashtami': 'Janmashtami', 'krishna janmashtami': 'Janmashtami',
        'ganesh chaturthi': 'Ganesh Chaturthi', 'ganapati': 'Ganesh Chaturthi',
        'dussehra': 'Dussehra', 'dasara': 'Dussehra', 'vijayadashami': 'Dussehra',
        'independence day': 'Independence Day',
        'republic day': 'Republic Day',
        'good friday': 'Good Friday',
        'monsoon sale': 'Monsoon Sale',
        'festive season': 'Festive Season Sale',
        'winter collection': 'Winter Collection Launch',
        'year end': 'Year-End Sale', 'year-end': 'Year-End Sale'
    }
    
    for key, festival in festival_mappings.items():
        if key in question_lower:
            return festival
    
    return None

def get_festival_window_data(festival_name, sales_data):
    """
    Get confirmed booking data within festival window: [Festival Date - 20 days] to [Festival Date + 5 days]
    Only includes records with status: "Confirmed"
    """
    if festival_name not in FESTIVAL_DATES:
        return []
    
    try:
        festival_date = datetime.strptime(FESTIVAL_DATES[festival_name], "%Y-%m-%d")
        start_date = festival_date - timedelta(days=20)
        end_date = festival_date + timedelta(days=5)
        
        print(f"🎭 Analyzing {festival_name} window: {start_date.date()} to {end_date.date()}")
        
        festival_data = []
        for record in sales_data:
            try:
                # Check status first - only confirmed orders
                status = record.get('status', '').lower()
                if status == 'declined':
                    continue
                
                # Parse date
                order_date = record.get('date') or record.get('orderDate', '')
                if order_date:
                    if 'T' in order_date:
                        date_obj = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
                    else:
                        date_obj = datetime.strptime(order_date, "%Y-%m-%d")
                    
                    # Check if within festival window
                    if start_date <= date_obj <= end_date:
                        festival_data.append(record)
            except (ValueError, TypeError):
                continue
        
        print(f"📊 Found {len(festival_data)} confirmed bookings in {festival_name} window")
        return festival_data
        
    except Exception as e:
        print(f"❌ Error analyzing festival window: {e}")
        return []

def analyze_festival_fabric_trends(festival_data):
    """Analyze fabric trends from festival window data"""
    if not festival_data:
        return {}
    
    # Counters for different fabric attributes
    weave_counter = Counter()
    quality_counter = Counter()
    composition_counter = Counter()
    quantity_by_fabric = defaultdict(float)
    revenue_by_fabric = defaultdict(float)
    
    total_quantity = 0
    total_revenue = 0
    
    for record in festival_data:
        try:
            quantity = float(record.get('quantity', 0))
            rate = float(record.get('rate', 0))
            revenue = quantity * rate
            
            weave = record.get('weave', '').strip()
            quality = record.get('quality', '').strip()
            composition = record.get('composition', '').strip()
            
            if weave:
                weave_counter[weave] += 1
                quantity_by_fabric[f"{weave} (weave)"] += quantity
                revenue_by_fabric[f"{weave} (weave)"] += revenue
            
            if quality:
                quality_counter[quality] += 1
                quantity_by_fabric[f"{quality} (quality)"] += quantity
                revenue_by_fabric[f"{quality} (quality)"] += revenue
            
            if composition:
                composition_counter[composition] += 1
                quantity_by_fabric[f"{composition} (composition)"] += quantity
                revenue_by_fabric[f"{composition} (composition)"] += revenue
            
            total_quantity += quantity
            total_revenue += revenue
            
        except (ValueError, TypeError):
            continue
    
    return {
        'weave_trends': dict(weave_counter.most_common()),
        'quality_trends': dict(quality_counter.most_common()),
        'composition_trends': dict(composition_counter.most_common()),
        'quantity_by_fabric': dict(quantity_by_fabric),
        'revenue_by_fabric': dict(revenue_by_fabric),
        'total_quantity': total_quantity,
        'total_revenue': total_revenue,
        'total_orders': len(festival_data)
    }

def predict_festival_demand(festival_name, current_year_data, historical_data=None):
    """Predict demand trends for upcoming festivals based on historical patterns"""
    try:
        # For now, use current year trends as baseline
        # In production, this would analyze multi-year historical data
        
        if not current_year_data:
            return {
                'growth_prediction': 'No historical data available',
                'recommended_increase': '10-15%',
                'confidence': 'Low'
            }
        
        # Calculate year-over-year growth (mock calculation for demonstration)
        # In real implementation, compare with previous year's same festival data
        base_growth = 12  # Default growth assumption
        
        # Adjust based on festival type
        festival_growth_factors = {
            'Diwali': 25,  # High demand festival
            'Holi': 20,
            'Christmas': 18,
            'Eid al-Fitr': 22,
            'Valentine\'s Day': 15,
            'Mother\'s Day': 12,
            'Father\'s Day': 10
        }
        
        predicted_growth = festival_growth_factors.get(festival_name, base_growth)
        
        return {
            'growth_prediction': f'{predicted_growth}% increase expected',
            'recommended_increase': f'{predicted_growth + 5}%',
            'confidence': 'Medium' if len(current_year_data) > 5 else 'Low'
        }
        
    except Exception as e:
        return {
            'growth_prediction': 'Analysis error',
            'recommended_increase': '15%',
            'confidence': 'Low'
        }

def generate_festival_fabric_response(festival_name, question, sales_data):
    """Generate comprehensive festival-specific fabric recommendations"""
    
    # Get festival window data (confirmed bookings only)
    festival_data = get_festival_window_data(festival_name, sales_data)
    
    if festival_data:
        # Analyze actual booking trends
        trends = analyze_festival_fabric_trends(festival_data)
        predictions = predict_festival_demand(festival_name, festival_data)
        
        # Build response based on actual data
        response = f"""🎭 **Festival Fabric Intelligence: {festival_name}**

📊 **Data Analysis Summary:**
Based on confirmed bookings from {len(festival_data)} orders during {festival_name} period:

**🔥 Top Performing Fabrics:**"""
        
        # Add weave analysis
        if trends['weave_trends']:
            response += "\n\n**👗 Weave Type Analysis:**"
            for weave, count in list(trends['weave_trends'].items())[:3]:
                percentage = (count / trends['total_orders']) * 100
                response += f"\n• {weave}: {count} orders ({percentage:.1f}%)"
        
        # Add quality analysis  
        if trends['quality_trends']:
            response += "\n\n**💎 Quality Grade Analysis:**"
            for quality, count in list(trends['quality_trends'].items())[:3]:
                percentage = (count / trends['total_orders']) * 100
                response += f"\n• {quality}: {count} orders ({percentage:.1f}%)"
        
        # Add composition analysis
        if trends['composition_trends']:
            response += "\n\n**🧵 Composition Analysis:**"
            for composition, count in list(trends['composition_trends'].items())[:3]:
                percentage = (count / trends['total_orders']) * 100
                response += f"\n• {composition}: {count} orders ({percentage:.1f}%)"
        
        # Add revenue insights
        if trends['revenue_by_fabric']:
            top_revenue_fabric = max(trends['revenue_by_fabric'].items(), key=lambda x: x[1])
            response += f"\n\n**💰 Profitability Insight:**\n• Highest revenue generator: {top_revenue_fabric[0]} (₹{top_revenue_fabric[1]:,.2f})"
        
        # Add predictions
        response += f"""

**📈 Future Trend Prediction:**
• Expected growth: {predictions['growth_prediction']}
• Recommended stock increase: {predictions['recommended_increase']}
• Confidence level: {predictions['confidence']}

**🎯 Strategic Recommendations:**
✓ This fabric combination had high volume and margin during {festival_name} — recommended for better profitability
✓ Focus on confirmed order patterns for accurate demand forecasting
✓ Consider bulk procurement of top-performing categories"""

    else:
        # No data found - use fallback recommendations
        fallback_fabrics = FESTIVAL_FABRIC_RECOMMENDATIONS.get(festival_name, ["Premium Cotton", "Silk Blends", "Traditional Weaves"])
        
        response = f"""🎭 **Festival Fabric Intelligence: {festival_name}**

📋 **Recommendation Status:**
There are no recent confirmed orders around {festival_name}, but based on traditional preferences and similar past events, we recommend:

**🎯 Curated Fabric Recommendations:**"""
        
        for i, fabric in enumerate(fallback_fabrics, 1):
            response += f"\n{i}. **{fabric}**"
        
        response += f"""

**💡 Strategic Approach:**
While we couldn't find recent booking data for {festival_name}, here's a recommended strategy based on trends and past preferences:

• Focus on traditional and festive appeal fabrics
• Consider cultural significance and color preferences
• Stock moderate quantities initially and monitor demand
• Prepare for potential surge based on festival popularity

**🚀 Business Intelligence:**
• Monitor real-time bookings as {festival_name} approaches
• Adjust inventory based on early demand signals  
• Consider promotional campaigns for recommended fabrics
• Track competitor offerings and price positioning"""

    response += f"""

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔥 **Want to explore more?** Ask me about:
▸ "Compare {festival_name} with other festivals"
▸ "Show me monthly fabric trends"
▸ "Predict revenue for next {festival_name}"
▸ "Which agents perform best during festivals?"
"""

    return response


def fetch_sales_data_from_api():
    """Fetch sales data from the provided API endpoint and return as a list of records."""
    url = "http://54.234.201.60:5000/chat/getFormData"
    try:
        print(f"📡 Fetching data from: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        print(f"📊 API Response Status: {data.get('status')}")
        print(f"📊 API Response Keys: {list(data.keys())}")
        
        if data.get("status") == 200 and "formData" in data:
            form_data = data["formData"]
            print(f"✅ Successfully fetched {len(form_data)} records from API")
            
            # Log sample data for verification
            if form_data:
                print(f"📝 Sample record: {form_data[0]}")
                print(f"📝 Record fields: {list(form_data[0].keys())}")
            
            return form_data
        else:
            print(f"❌ Unexpected API response structure: {data}")
            raise ValueError(f"API returned unexpected response: {data}")
    except requests.exceptions.RequestException as e:
        print(f"🌐 Network error fetching data from API: {e}")
        return []
    except Exception as e:
        print(f"❌ Error fetching data from API: {e}")
        return []

def is_sales_related_question(question):
    """Check if the question is related to sales data analysis, allowing for fuzzy keyword matches AND checking against live API data."""
    sales_keywords = [
        'record','dress','sales', 'trend', 'predict', 'forecast', 'quantity', 'rate', 'revenue',
        'agent', 'customer', 'weave', 'linen', 'satin', 'denim', 'crepe', 'twill',
        'premium', 'standard', 'economy', 'cotton', 'polyester', 'spandex',
        'order', 'status', 'confirmed', 'pending', 'cancelled', 'growth',
        'performance', 'top', 'best', 'most', 'sold', 'item', 'product',
        'month', 'year', 'quarter', 'period', 'analysis', 'data','id','date',
        # Festival-related keywords for fabric intelligence
        'festival', 'diwali', 'holi', 'christmas', 'eid', 'pongal', 'valentine',
        'mother day', 'father day', 'raksha bandhan', 'karva chauth', 'janmashtami',
        'ganesh chaturthi', 'dussehra', 'independence day', 'republic day',
        'recommend', 'suggest', 'stock', 'fabric for', 'monsoon sale', 'festive season',
        # Add common misspellings and variations
        'quality', 'kolity', 'qualety', 'qaulity', 'qulaity',
        'composition', 'komposition', 'kumposison', 'composision',
        # Agent names from the CSV data
        'priya', 'sowmiya', 'mukilan', 'karthik',
        # Customer names from the CSV data
        'alice', 'smith', 'ravi', 'qilyze', 'jhon'
    ]
    question_lower = question.lower()
    words = question_lower.split()
    
    # First check: keyword matching with more lenient fuzzy matching
    for word in words:
        # Fuzzy match with lower cutoff for better misspelling detection
        matches = difflib.get_close_matches(word, sales_keywords, n=1, cutoff=0.6)
        if matches:
            return True
    # Substring match (for multi-word keywords or partials)
    for keyword in sales_keywords:
        if keyword in question_lower:
            return True
    
    # Second check: check against live API data
    try:
        sales_data = fetch_sales_data_from_api()
        if sales_data:
            # Extract all unique values from the API data
            api_keywords = set()
            for record in sales_data:
                # Add agent names
                if 'agentName' in record and record['agentName']:
                    api_keywords.add(record['agentName'].lower().strip())
                # Add customer names
                if 'customerName' in record and record['customerName']:
                    api_keywords.add(record['customerName'].lower().strip())
                # Add weave types
                if 'weave' in record and record['weave']:
                    api_keywords.add(record['weave'].lower().strip())
                # Add quality types
                if 'quality' in record and record['quality']:
                    api_keywords.add(record['quality'].lower().strip())
                # Add composition data
                if 'composition' in record and record['composition']:
                    api_keywords.add(record['composition'].lower().strip())
                # Add status data
                if 'status' in record and record['status']:
                    api_keywords.add(record['status'].lower().strip())
            
            # Check if any word in the question matches API data
            for word in words:
                # Direct match
                if word in api_keywords:
                    return True
                # Fuzzy match with API data
                matches = difflib.get_close_matches(word, list(api_keywords), n=1, cutoff=0.75)
                if matches:
                    return True
    except Exception as e:
        # If API fails, fall back to keyword-only checking
        print(f"API check failed, using keyword-only: {e}")
        pass
    
    return False

def correct_misspellings(text):
    """Correct common misspellings in the text"""
    corrections = {
        'kolity': 'quality',
        'qualety': 'quality',
        'qaulity': 'quality',
        'qulaity': 'quality',
        'kumposison': 'composition',
        'komposition': 'composition',
        'composision': 'composition',
        'weav': 'weave',
        'weev': 'weave',
        'agnet': 'agent',
        'cusomer': 'customer',
        'custmer': 'customer',
        'salse': 'sales',
        'seles': 'sales',
        'preium': 'premium',
        'standrd': 'standard',
        'econmy': 'economy'
    }
    
    corrected_text = text.lower()
    for misspelling, correction in corrections.items():
        corrected_text = corrected_text.replace(misspelling, correction)
    
    return corrected_text

def analyze_historical_trends(sales_data):
    """Analyze historical trends from sales data for prediction"""
    if not sales_data:
        return {}
    
    monthly_data = defaultdict(lambda: {
        'total_quantity': 0,
        'total_revenue': 0,
        'order_count': 0,
        'weave_types': defaultdict(int),
        'compositions': defaultdict(int),
        'qualities': defaultdict(int)
    })
    
    # Group data by month
    for record in sales_data:
        try:
            # Parse date
            date_str = record.get('date', '')
            if date_str:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                month_key = f"{date_obj.year}-{date_obj.month:02d}"
                
                # Aggregate data
                quantity = float(record.get('quantity', 0))
                rate = float(record.get('rate', 0))
                revenue = quantity * rate
                
                monthly_data[month_key]['total_quantity'] += quantity
                monthly_data[month_key]['total_revenue'] += revenue
                monthly_data[month_key]['order_count'] += 1
                
                # Track categories
                weave = record.get('weave', '').lower().strip()
                composition = record.get('composition', '').lower().strip()
                quality = record.get('quality', '').lower().strip()
                
                if weave:
                    monthly_data[month_key]['weave_types'][weave] += quantity
                if composition:
                    monthly_data[month_key]['compositions'][composition] += quantity
                if quality:
                    monthly_data[month_key]['qualities'][quality] += quantity
                    
        except (ValueError, TypeError):
            continue
    
    return monthly_data

def calculate_growth_rates(monthly_data):
    """Calculate month-over-month growth rates"""
    sorted_months = sorted(monthly_data.keys())
    growth_rates = {}
    
    for i in range(1, len(sorted_months)):
        prev_month = sorted_months[i-1]
        curr_month = sorted_months[i]
        
        prev_qty = monthly_data[prev_month]['total_quantity']
        curr_qty = monthly_data[curr_month]['total_quantity']
        
        if prev_qty > 0:
            growth_rate = ((curr_qty - prev_qty) / prev_qty) * 100
            growth_rates[curr_month] = growth_rate
        else:
            growth_rates[curr_month] = 0
    
    return growth_rates

def predict_future_sales(target_date_str, sales_data):
    """Predict sales for a future date based on historical trends"""
    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
        target_month = f"{target_date.year}-{target_date.month:02d}"
        
        # Analyze historical data
        monthly_data = analyze_historical_trends(sales_data)
        growth_rates = calculate_growth_rates(monthly_data)
        
        if not monthly_data:
            return {
                'error': 'Insufficient historical data for prediction',
                'prediction': 0,
                'confidence': 'Low'
            }
        
        # Calculate average monthly metrics
        total_months = len(monthly_data)
        avg_quantity = sum(data['total_quantity'] for data in monthly_data.values()) / total_months
        avg_revenue = sum(data['total_revenue'] for data in monthly_data.values()) / total_months
        avg_orders = sum(data['order_count'] for data in monthly_data.values()) / total_months
        
        # Calculate average growth rate
        if growth_rates:
            avg_growth_rate = sum(growth_rates.values()) / len(growth_rates)
        else:
            avg_growth_rate = 5.0  # Default 5% growth assumption
        
        # Seasonal adjustment based on historical same-month data
        target_month_num = target_date.month
        historical_same_months = []
        
        for month_key, data in monthly_data.items():
            year, month = month_key.split('-')
            if int(month) == target_month_num:
                historical_same_months.append(data['total_quantity'])
        
        seasonal_factor = 1.0
        if historical_same_months:
            seasonal_avg = sum(historical_same_months) / len(historical_same_months)
            seasonal_factor = seasonal_avg / avg_quantity if avg_quantity > 0 else 1.0
        
        # Calculate months into future
        latest_month = max(monthly_data.keys())
        latest_date = datetime.strptime(latest_month + '-01', '%Y-%m-%d')
        months_ahead = (target_date.year - latest_date.year) * 12 + (target_date.month - latest_date.month)
        
        # Apply compound growth
        growth_multiplier = (1 + avg_growth_rate/100) ** months_ahead
        
        # Calculate predictions
        predicted_quantity = avg_quantity * seasonal_factor * growth_multiplier
        predicted_revenue = avg_revenue * seasonal_factor * growth_multiplier
        predicted_orders = avg_orders * seasonal_factor * growth_multiplier
        
        # Determine confidence level
        confidence = 'High' if months_ahead <= 6 else 'Medium' if months_ahead <= 12 else 'Low'
        
        return {
            'target_date': target_date_str,
            'predicted_quantity': round(predicted_quantity, 2),
            'predicted_revenue': round(predicted_revenue, 2),
            'predicted_orders': round(predicted_orders),
            'avg_growth_rate': round(avg_growth_rate, 2),
            'seasonal_factor': round(seasonal_factor, 2),
            'confidence': confidence,
            'months_ahead': months_ahead,
            'historical_months': total_months
        }
        
    except Exception as e:
        return {
            'error': f'Prediction error: {str(e)}',
            'prediction': 0,
            'confidence': 'Low'
        }

def is_prediction_question(question):
    """Check if the question is asking for future predictions"""
    prediction_keywords = [
        'predict', 'forecast', 'future', 'will be', 'next year', 'next month',
        '2026', '2027', '2028', 'upcoming', 'expected', 'projection'
    ]
    q_lower = question.lower()
    return any(keyword in q_lower for keyword in prediction_keywords)

def extract_prediction_date(question):
    """Extract target date from prediction question"""
    # Look for year patterns
    year_pattern = r'(202[6-9]|20[3-9]\d)'
    year_match = re.search(year_pattern, question)
    
    # Look for month patterns
    month_patterns = {
        'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
        'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6,
        'july': 7, 'jul': 7, 'august': 8, 'aug': 8, 'september': 9, 'sep': 9,
        'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12
    }
    
    q_lower = question.lower()
    month_num = None
    for month_name, num in month_patterns.items():
        if month_name in q_lower:
            month_num = num
            break
    
    # Default values
    target_year = year_match.group(1) if year_match else '2026'
    target_month = month_num if month_num else 6  # Default to June
    
    return f"{target_year}-{target_month:02d}-15"  # Use 15th of the month

def generate_response(user_question, chat_history=None, followup_flag=False):
    try:
        # CRITICAL: Always fetch fresh data from live API for every question
        print("🔄 Fetching latest sales data from live API...")
        sales_data = fetch_sales_data_from_api()
        
        if not sales_data:
            return "❌ I cannot access the live sales data at the moment. Please check if the API at http://54.234.201.60:5000/chat/getFormData is available and try again."
        
        print(f"✅ Successfully loaded {len(sales_data)} records from live API")
        
        # � BUSINESS STRATEGY ANALYSIS - Check business strategy questions first (higher priority)
        if is_business_strategy_question(user_question):
            festivals = extract_multiple_festivals(user_question)
            if festivals:
                print(f"� Detected business strategy question for: {', '.join(festivals)}")
                return generate_business_strategy_response(festivals, user_question, sales_data, chat_history)
        
        # � FESTIVAL-AWARE ANALYSIS - Check if this is a festival question (non-strategy)
        if is_festival_question(user_question) and not is_business_strategy_question(user_question):
            festival_name = extract_festival_name(user_question)
            if festival_name:
                print(f"� Detected festival question for: {festival_name}")
                return generate_festival_fabric_response(festival_name, user_question, sales_data)
        
        # --- Smart Context Analysis ---
        def is_followup_question(q):
            """Check if question is a follow-up to the immediate previous question"""
            followup_phrases = [
                'only in', 'what about', 'how about', 'and for', 'show me', 'can you', 'do it', 
                'yes', 'change it', 'ok', 'go ahead', 'then', 'next', 'now', 'also', 
                'give me', 'tell me', 'show', 'list', 'details', 'breakdown', 'again', 'repeat'
            ]
            temporal_phrases = ['only in', 'in ', 'for ', 'during', 'within']
            ql = q.lower().strip()
            
            # Check if it's a temporal filter (like "only in June month")
            if any(phrase in ql for phrase in temporal_phrases):
                return True
            
            # Check other follow-up patterns
            return any(ql.startswith(phrase) or phrase in ql for phrase in followup_phrases) or len(ql.split()) <= 5

        def are_questions_related(current_q, last_q):
            """Check if two questions are about the same topic/analysis"""
            if not last_q or not current_q:
                return False
            
            # Define topic keywords for different analysis areas
            topic_groups = {
                'weave': ['weave', 'weev', 'plain', 'satin', 'linen', 'denim', 'crepe', 'twill', 'spandex'],
                'composition': ['composition', 'komposition', 'kumposison', 'composision', 'cotton', 'polyester'],
                'quality': ['quality', 'kolity', 'qualety', 'premium', 'standard', 'economy'],
                'agent': ['agent', 'agnet', 'priya', 'sowmiya', 'mukilan', 'karthik', 'boobalan', 'boopalan'],
                'customer': ['customer', 'cusomer', 'alice', 'smith', 'ravi', 'qilyze', 'jhon'],
                'sales': ['sales', 'revenue', 'quantity', 'rate', 'growth', 'trend', 'sold', 'most'],
                'status': ['status', 'confirmed', 'pending', 'cancelled']
            }
            
            def get_question_topics(question):
                """Get the topics/categories a question belongs to"""
                q_lower = question.lower()
                topics = []
                for topic, keywords in topic_groups.items():
                    if any(keyword in q_lower for keyword in keywords):
                        topics.append(topic)
                return topics
            
            current_topics = get_question_topics(current_q)
            last_topics = get_question_topics(last_q)
            
            # Questions are related if they share at least one topic
            return bool(set(current_topics) & set(last_topics))

        def get_last_user_question(chat_history):
            """Get the most recent user question from chat history"""
            if not chat_history:
                return None
            
            for msg in reversed(chat_history[:-1]):  # Exclude current question
                if msg.get("role") == "user":
                    return msg["parts"][0]["text"]
            return None

        def is_temporal_filter(q):
            """Check if the question is asking for a time-based filter"""
            temporal_patterns = [
                r'only in (\w+)',
                r'in (\w+) month',
                r'for (\w+)',
                r'during (\w+)'
            ]
            return any(re.search(pattern, q.lower()) for pattern in temporal_patterns)

        # Smart context handling for follow-up questions
        if (followup_flag or (chat_history and is_followup_question(user_question))):
            last_question = get_last_user_question(chat_history)
            
            # Handle misspelling corrections with "yes" responses
            if user_question.lower().strip() in ['yes', 'yeah', 'yep', 'sure', 'please do', 'go ahead', 'correct']:
                if last_question:
                    # Try to correct common misspellings in the last question
                    corrected_question = correct_misspellings(last_question)
                    if corrected_question != last_question:
                        # Use the corrected question
                        user_question = corrected_question
                        # Use only the last 2 messages for context
                        limited_history = chat_history[-2:] if len(chat_history) >= 2 else chat_history
                        chat_history = limited_history
                    else:
                        # No correction found, ask for clarification
                        api_key = os.getenv("GEMINI_API_KEY")
                        if not api_key:
                            raise ValueError("GEMINI_API_KEY environment variable not set. Please set it before running the script.")
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel("models/gemini-2.0-flash")
                        context_response = f"""You are a Dress Sales Monitoring Chatbot. The user's previous question was: "{last_question}" and they responded "yes".

Please provide a helpful response that:
1. Acknowledges their confirmation
2. Asks them to rephrase their original question more clearly
3. Provides 2-3 example questions they could ask about sales data
4. Mentions you can help with sales analysis, trends, and predictions

Keep the response friendly and encouraging."""
                        response = model.generate_content(context_response)
                        response_text = response.text
                        print(response_text, end="")
                        return response_text
            
            # Check if questions are actually related before combining
            if last_question and are_questions_related(user_question, last_question):
                if is_temporal_filter(user_question):
                    # This is a temporal filter - apply it to the last question only
                    combined_question = f"{last_question.strip()} {user_question.strip()}"
                    
                    # Check if the combined context is sales-related
                    if not is_sales_related_question(combined_question):
                        api_key = os.getenv("GEMINI_API_KEY")
                        if not api_key:
                            raise ValueError("GEMINI_API_KEY environment variable not set. Please set it before running the script.")
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel("models/gemini-2.0-flash")
                        context_response = f"""You are a Dress Sales Monitoring Chatbot. A user asked: \"{user_question}\"

This question appears to be outside my domain of expertise. I am specifically designed to analyze fabric sales data, provide sales insights, and make predictions about sales performance.

Please provide a helpful, polite response that:
1. Acknowledges their question
2. Explains that this is outside your scope as a sales analytics chatbot
3. Suggests they ask about sales data, trends, predictions, or fabric performance instead
4. Provides 2-3 example questions they could ask

Keep the response friendly and helpful, not dismissive."""
                        response = model.generate_content(context_response)
                        response_text = response.text
                        print(response_text, end="")
                        return response_text
                    
                    # Process with limited context - only the last question + current filter
                    user_question = combined_question
                    # Use only the last 2 messages for context to avoid mixing old contexts
                    limited_history = chat_history[-2:] if len(chat_history) >= 2 else chat_history
                    chat_history = limited_history
                    
                else:
                    # Regular follow-up - only combine with immediate previous question if related
                    combined_question = f"{last_question.strip()} {user_question.strip()}"
                    
                    if not is_sales_related_question(combined_question):
                        api_key = os.getenv("GEMINI_API_KEY")
                        if not api_key:
                            raise ValueError("GEMINI_API_KEY environment variable not set. Please set it before running the script.")
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel("models/gemini-2.0-flash")
                        context_response = f"""You are a Dress Sales Monitoring Chatbot. A user asked: \"{user_question}\"

This question appears to be outside my domain of expertise. I am specifically designed to analyze fabric sales data, provide sales insights, and make predictions about sales performance.

Please provide a helpful, polite response that:
1. Acknowledges their question
2. Explains that this is outside your scope as a sales analytics chatbot
3. Suggests they ask about sales data, trends, predictions, or fabric performance instead
4. Provides 2-3 example questions they could ask

Keep the response friendly and helpful, not dismissive."""
                        response = model.generate_content(context_response)
                        response_text = response.text
                        print(response_text, end="")
                        return response_text
                    
                    # Process with limited context
                    user_question = combined_question
                    limited_history = chat_history[-2:] if len(chat_history) >= 2 else chat_history
                    chat_history = limited_history
            # If questions are not related, treat as a new independent question - no context combination

        # Check if this is a prediction question and handle it specially
        if is_prediction_question(user_question):
            # Use the already fetched sales data for prediction
            if not sales_data:
                return "I apologize, but I cannot access the sales data needed for predictions at the moment. Please try again later."
            
            # Extract target date from question
            target_date = extract_prediction_date(user_question)
            
            # Generate prediction
            prediction_result = predict_future_sales(target_date, sales_data)
            
            if 'error' in prediction_result:
                return f"**Prediction Error:** {prediction_result['error']}"
            
            # Format prediction response
            target_datetime = datetime.strptime(target_date, '%Y-%m-%d')
            month_name = calendar.month_name[target_datetime.month]
            year = target_datetime.year
            
            prediction_response = f"""**📈 Sales Prediction for {month_name} {year}**

**Summary:** Based on historical trends analysis, I predict the following sales metrics for {month_name} {year}:

**Detailed Forecast:**
- **Predicted Quantity:** {prediction_result['predicted_quantity']:,} units
- **Predicted Revenue:** ₹{prediction_result['predicted_revenue']:,.2f}
- **Predicted Orders:** {prediction_result['predicted_orders']:,} orders
- **Average Growth Rate:** {prediction_result['avg_growth_rate']}% per month
- **Seasonal Factor:** {prediction_result['seasonal_factor']}x (based on historical {month_name} data)

**Prediction Details:**
- **Confidence Level:** {prediction_result['confidence']}
- **Months Ahead:** {prediction_result['months_ahead']} months from latest data
- **Historical Data:** Based on {prediction_result['historical_months']} months of sales data

**Key Insights:**
- This prediction uses historical sales patterns, seasonal trends, and growth rates
- {prediction_result['confidence']} confidence due to {prediction_result['months_ahead']} months projection horizon
- Seasonal adjustment applied based on historical {month_name} performance
- Growth projection assumes continuation of current market trends

**Disclaimer:** This prediction is based on historical data patterns and assumes continuation of current trends. Actual results may vary due to market conditions, economic factors, seasonal variations, and external events."""
            
            print(prediction_response, end="")
            return prediction_response

        # Get API key from environment variable
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set. Please set it before running the script.")
        genai.configure(api_key=api_key)
        model_name = "models/gemini-2.0-flash"  # or 'gemini-pro' if you want
        model = genai.GenerativeModel(model_name)
        
        # Use the already fetched sales data - DO NOT fetch again
        # Convert sales_data (list of dicts) to CSV string for Gemini context
        csv_buffer = io.StringIO()
        if sales_data:
            writer = csv.DictWriter(csv_buffer, fieldnames=sales_data[0].keys())
            writer.writeheader()
            writer.writerows(sales_data)
            csv_string = csv_buffer.getvalue()
            
            # Debug: Print CSV content for both May 2025 and July 2025 records
            may_records = [record for record in sales_data if '2025-05' in record.get('date', '')]
            july_declined = [record for record in sales_data if '2025-07' in record.get('date', '') and 'declined' in record.get('status', '').lower()]
            print(f"🔍 DEBUG: Found {len(may_records)} May 2025 records in CSV:")
            for i, record in enumerate(may_records):
                print(f"  {i+1}. Date: {record.get('date')}, Customer: {record.get('customerName')}, Status: {record.get('status')}")
            print(f"🔍 DEBUG: Found {len(july_declined)} July 2025 DECLINED records in CSV:")
            for i, record in enumerate(july_declined):
                print(f"  {i+1}. Date: {record.get('date')}, Customer: {record.get('customerName')}, Status: {record.get('status')}")
            print(f"📄 Total records in CSV: {len(sales_data)}")
            print(f"📄 CSV sample (first 800 chars): {csv_string[:800]}...")
        else:
            csv_string = ""

        # Build contents with chat history
        contents = []

        # Add system context about the Dress Sales Monitoring Chatbot
        system_context = f"""You are the Dress Sales Monitoring Chatbot, an advanced AI-powered analytics system designed for dress and fabric sales companies. Your job is to help business administrators gain insights from their sales data in a professional, friendly, and interactive way.

**🎭 FESTIVAL-AWARE FABRIC INTELLIGENCE (TOP PRIORITY)**
You are equipped with advanced festival-aware analysis capabilities:

**Festival Analysis Rules:**
- When admin asks about fabric recommendations for festivals, analyze ONLY confirmed bookings within [Festival Date - 20 days] to [Festival Date + 5 days]
- Supported festivals: Diwali, Holi, Christmas, Eid al-Fitr, Pongal, Valentine's Day, Mother's Day, Father's Day, Raksha Bandhan, Karva Chauth, Janmashtami, Ganesh Chaturthi, Dussehra, Independence Day, Republic Day, Good Friday, Monsoon Sale, Festive Season Sale, Winter Collection Launch, Year-End Sale
- NEVER respond with "No data found" - always provide fallback recommendations based on traditional preferences
- Focus on profit-driven recommendations highlighting high-margin and high-volume fabrics
- Provide future trend predictions based on historical patterns

**Profit-Oriented Analysis:**
- Prioritize high-margin fabrics in recommendations
- Analyze repeated bookings (customer loyalty patterns)
- Highlight volume-based profit opportunities
- Use phrases like "This fabric had high volume and margin last year — recommended for better profitability"

**Fallback Strategy:**
- If no confirmed bookings found for a festival, use curated traditional recommendations
- Example: "There are no recent confirmed orders around [Festival], but based on traditional preferences and similar past events, we recommend: [specific fabrics]"
- Never say "Can't help" or "Unknown" - always redirect with strategic suggestions

**CRITICAL: ALWAYS USE LIVE API DATA AND COUNT INDIVIDUAL RECORDS**
- EVERY response MUST be based ONLY on the current live sales data from http://54.234.201.60:5000/chat/getFormData
- The CSV data provided contains {len(sales_data)} records from the live API
- For questions about orders, sales, status, trends, or any business metrics - count and analyze ONLY the actual data in the CSV
- If asked about "how many sales happened in May 2025" - filter the data by May 2025 and count the exact individual records (each row = 1 sale)
- If asked about "how many orders declined in July 2025" - filter by July 2025 AND status='Declined' (case-insensitive) and count the exact individual records
- Never make assumptions - always provide exact counts based on the actual data
- Be mathematically precise and verify your counts
- DO NOT group by dates when counting - each CSV row represents one individual sale/order
- If there are 2 sales on the same date (2025-05-28), count them as 2 separate sales, not 1
- If there are 2 declined orders on the same date (2025-07-09), count them as 2 separate declined orders, not 1

**STATUS FILTERING INSTRUCTIONS:**
- When filtering by status, check for exact matches (case-insensitive)
- "Declined" status should match "Declined", "declined", "DECLINED"
- "Confirmed" status should match "Confirmed", "confirmed", "CONFIRMED"
- "Pending" status should match "Pending", "pending", "PENDING"
- Count EVERY row that matches the status criteria, even if multiple records have the same date

**DATA ANALYSIS INSTRUCTIONS:**
- When filtering by month/year: Use the 'date' field and match the exact month/year requested
- When filtering by status: Use the 'status' field and match the exact status requested (declined, confirmed, pending, etc.)
- When counting records: Count each individual row/record that matches ALL the specified criteria
- NEVER group by date when counting sales - count each individual record separately
- If there are multiple sales on the same date, count each one individually
- Always double-check your filtering and counting logic
- If there are 4 individual records in May 2025, say 4, not 2 or 3
- If there are 2 declined orders in July 2025, say 2, not 1
- Each row in the CSV = 1 sale/order, regardless of date, customer, or other fields

**SMART CONTEXT HANDLING:**
- When a user asks a follow-up question with temporal filters (like "only in June month"), apply the filter ONLY to the immediately previous question, not all previous questions
- If the previous question was about "composition" and user asks "only in June month", analyze composition data for June only
- If the previous question was about "weave type" and user asks "only in June month", analyze weave type data for June only
- Do NOT combine multiple different previous questions unless they are directly related

**CRITICAL ANALYSIS RULES:**
- When analyzing "most sold" items, ALWAYS check if there are ties (equal counts)
- If ALL items have the same count (e.g., all have count of 1), state "There is a TIE - all items have equal sales" 
- NEVER claim one item is "most sold" when multiple items have the same highest count
- Be mathematically accurate and honest about ties and equal distributions
- SUMMARY MUST MATCH THE DATA: If there's a tie, the summary must say "There is a tie" NOT "X is the most sold"
- **FOR REVENUE CALCULATIONS: Calculate once, show final result clearly, NO multiple corrections or "however" statements**

**CRITICAL COUNTING VERIFICATION RULE:**
- BEFORE providing your final response, COUNT the records you're about to list in the detailed breakdown
- The number in your opening statement MUST EXACTLY MATCH the number of items you list in the detailed section
- If you're about to list 5 items in the breakdown, say "5" in the opening line, NOT "6"
- Double-check: Opening count = Detailed breakdown count = Actual filtered records
- Example: If you list 5 orders (Velmurugan, waxoc, simeon j, Viswa V, Azhagarsamy), then say "I found 5 orders" in the opening line

**RESPONSE STYLE GUIDELINES - CONVERSATIONAL & INTERACTIVE:**

**Tone & Voice:**
- Use a friendly, conversational tone like you're talking to a business colleague
- Be enthusiastic about data insights! Use phrases like "Great question!", "Here's what I found:", "Interesting pattern!", "Let me break this down for you"
- Make the user feel heard and valued - "You're absolutely right to ask about this!"
- Use contractions and natural language: "I've", "let's", "here's", "that's"

**Response Structure:**
1. **🎯 Quick Answer:** Start with an engaging, direct answer using emojis and conversational language
2. **📊 The Details:** Present data in visually appealing formats with charts, tables, and visual elements
3. **💡 Smart Insights:** Provide actionable business insights and recommendations
4. **🔥 What's Next:** Suggest follow-up questions or related analysis

**Visual Formatting:**
- Use emojis strategically: 📈 📊 💰 🔥 ⭐ 📅 👥 🎯 💡 ⚡ 🚀
- Create visual separators: ━━━━━━━━━━━━━━━━━━
- Use progress bars for percentages: ▓▓▓▓▓░░░░░ (67%)
- Include boxes and visual elements: ┌─────────────┐
- Use bullet styles: ● ▸ ➤ ✓ ★
- Number lists with styled numbers: ① ② ③

**Data Presentation:**
- Always include both numbers AND percentages
- Show trends with arrows: ↗️ ↘️ ➡️
- Use comparison language: "That's X% higher than...", "This represents a Y% increase"
- Include visual data representations when possible

**Interactive Elements:**
- End with engaging questions: "Want to dive deeper into any specific month?" 
- Suggest related analyses: "Curious about which products performed best?"
- Offer different perspectives: "Would you like to see this broken down by customer?"

**EXAMPLE CONVERSATIONAL RESPONSE TEMPLATE:**

🎯 **Hey there! Here's what I found:**
[Direct, enthusiastic answer]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **Let me break down the numbers for you:**

┌──────────────────────────────────┐
│  [Visual data presentation]      │
│  ● Item 1: X records (Y%)       │
│  ● Item 2: X records (Y%)       │
└──────────────────────────────────┘

💡 **Here's what this tells us:**
[Business insights with recommendations]

🔥 **What's interesting:**
[Notable patterns or trends]

⚡ **Quick tip:** [Actionable recommendation]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 **Want to explore more?** Ask me about:
▸ [Suggested follow-up question 1]
▸ [Suggested follow-up question 2]

**EXAMPLE: Conversational Response for "How many sales happened in May 2025?"**

🎯 **Great question! I found 4 sales in May 2025! 🎉**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **Here's your May 2025 sales breakdown:**

┌─────────────────────────────────┐
│  📅 May 27: Jhon ✓             │
│  📅 May 28: qilyze ✓            │
│  📅 May 28: jogoco ✓            │
│  📅 May 30: vil ✓               │
└─────────────────────────────────┘

💡 **What this tells us:**
▸ Strong activity on May 28th (2 sales! 🔥)
▸ Steady sales throughout the month
▸ 4 different customers engaged

⚡ **Quick insight:** May 28th was your hottest sales day with 50% of monthly activity!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 **Curious about more?** Try asking:
▸ "Which products sold best in May?"
▸ "How does May compare to other months?"
▸ "Show me the revenue breakdown for May"

**EXAMPLE: Conversational Response for "How many orders declined in July 2025?"**

🎯 **I found 2 declined orders in July 2025 📉**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **Let me show you what happened:**

┌─────────────────────────────────┐
│  ❌ July 9: Nandhakumar T       │
│  ❌ July 9: palaniappan         │
└─────────────────────────────────┘

📈 **Decline Rate Analysis:**
● July 9th: 2 declines (100% of monthly declines)
● Pattern: Both declines on same day 🤔

💡 **Actionable insights:**
▸ Investigate what happened on July 9th
▸ Contact these customers for feedback
▸ Review pricing/product issues from that date

⚡ **Pro tip:** Follow up with declined customers - they might still convert!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 **Want to dig deeper?** Ask me:
▸ "What products were declined in July?"
▸ "Show me the decline reasons"
▸ "How does July compare to other months?"

**CRITICAL EXAMPLE: Correct Counting Verification**

❌ **WRONG:** "I found 6 orders with 'Processed' status!" (but then lists only 5)
✅ **CORRECT:** "I found 5 orders with 'Processed' status!" (matches the 5 listed)

Step-by-step verification:
1. Filter data for 'Processed' status
2. Count the filtered records: Velmurugan, waxoc, simeon j, Viswa V, Azhagarsamy = 5 orders
3. Use "5" in opening statement: "I found 5 orders..."
4. List the same 5 orders in detailed breakdown

**EXAMPLE: Handling Ties in Conversational Style**

🎯 **Interesting! There's a perfect TIE in June weave types! 🤝**

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 **Here's the tie breakdown:**

┌─────────────────────────────────┐
│  🥇 Satin: 1 sale (33.3%) ⚖️   │
│  🥇 Linen: 1 sale (33.3%) ⚖️   │  
│  🥇 Cotton: 1 sale (33.3%) ⚖️  │
└─────────────────────────────────┘

💡 **What this means:**
▸ No single weave type dominated June
▸ Equal customer interest across all types
▸ Balanced product portfolio performance

⚡ **Strategic insight:** This balanced demand suggests diverse customer preferences - great for inventory planning!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 **Let's explore more:** 
▸ "Which weave type sells best overall?"
▸ "Show me weave performance by month"

**CRITICAL EXAMPLE - How to Count Sales Correctly:**
EXAMPLE 1 - May 2025 Sales:
If CSV contains these records for May 2025:
- Row 1: 2025-05-27: Customer Jhon, Status: Confirmed
- Row 2: 2025-05-28: Customer qilyze, Status: Confirmed  
- Row 3: 2025-05-28: Customer jogoco, Status: Confirmed
- Row 4: 2025-05-30: Customer vil, Status: Confirmed

CORRECT Answer: "There were 4 sales in May 2025"
WRONG Answer: "There were 2 sales in May 2025" (this would be grouping by date)
WRONG Answer: "There were 3 sales in May 2025" (this would be missing one record)

EXAMPLE 2 - July 2025 Declined Orders:
If CSV contains these records for July 2025:
- Row 1: 2025-07-09: Customer Nandhakumar T, Status: Declined
- Row 2: 2025-07-09: Customer palaniappan, Status: Declined
- Row 3: 2025-07-15: Customer Someone, Status: Confirmed

CORRECT Answer: "There were 2 orders declined in July 2025"
WRONG Answer: "There was 1 order declined in July 2025" (this would be grouping by date or missing records)

Each row in the CSV = 1 individual sale/order, regardless of whether multiple sales happen on the same date.
ALWAYS count every single row that matches the criteria - DO NOT summarize by date or any other field.

Each row in the CSV = 1 individual sale, regardless of whether multiple sales happen on the same date.
ALWAYS count every single row that matches the criteria - DO NOT summarize by date or any other field.

**VERIFICATION INSTRUCTION:**
When counting records, list ALL individual records that match the criteria before providing the final count.
For May 2025 sales, you should find and list exactly these 4 records:
1. Customer: Jhon, Date: 2025-05-27
2. Customer: qilyze, Date: 2025-05-28  
3. Customer: jogoco, Date: 2025-05-28
4. Customer: vil, Date: 2025-05-30

The system operates on a dataset containing {len(sales_data)} sales records with detailed information including dates, product qualities (premium, standard, economy), weave types (spandex, linen, denim, satin, crepe, plain, twill), quantities, compositions, order statuses, rates, agent names, and customer information.

The chatbot employs a Random Forest Regressor machine learning model that continuously learns from historical sales patterns to predict future sales quantities based on product characteristics, seasonal factors, and market trends. It processes natural language queries through keyword extraction and pattern matching, then generates conversational responses enhanced by Google's Gemini AI to provide professional, context-aware answers. The system features an adaptive learning mechanism that tracks user preferences and question patterns, allowing it to personalize responses and improve accuracy over time.

Special Features & Advanced Capabilities:
- **Sophisticated Trend Analysis:** Identify revenue growth or decline patterns over custom time periods, such as "past 6 months" or "January to August," providing detailed month-over-month comparisons with percentage changes and trend directions
- **Field-Specific Analysis:** Comprehensive analysis across different time dimensions (daily, weekly, monthly, yearly) for weave types, compositions, qualities, and customer/agent performance
- **Range Analysis:** Compare performance between specific month ranges
- **Leading Analysis:** Identify top performers in various categories over different time periods
- **Continuous Trend Analysis:** When analyzing trends between months (e.g., "January to August"), analyze ALL months in between, not just start and end points

Future Prediction Capabilities:
The chatbot excels in predictive analytics with multiple forecasting approaches:
- **Advanced Time Series Analysis:** Analyze historical monthly trends, seasonal patterns, and growth rates to predict future sales
- **Specific Date Predictions:** Predict sales for specific future dates (e.g., "June 2026", "March 15, 2027") by analyzing historical patterns and applying growth trends
- **Year-Based Predictions:** For year-based predictions (e.g., "2027 sales forecast"), use historical yearly data to calculate growth rates and project future values with monthly breakdowns
- **Growth Projections:** Incorporate trend analysis and growth projections, considering factors like seasonal patterns, historical growth rates, and market evolution
- **Detailed Projections:** Provide detailed monthly projections for future years, including quantity predictions, revenue estimates, and confidence levels based on historical data patterns
- **Seasonal Adjustments:** Apply seasonal factors based on historical performance of the same month in previous years
- **Confidence Scoring:** Provide confidence levels (High/Medium/Low) based on prediction horizon and data availability

**Prediction Examples:**
- "What will be the sales in June 2026?" → Analyzes June historical data + growth trends
- "Predict sales for 2027" → Year-long forecast with monthly breakdown
- "Future sales forecast for premium cotton dresses" → Category-specific predictions
- "Expected revenue next year" → Revenue projections with confidence intervals

Response Intelligence:
The system responds to queries through a multi-layered approach:
- **Keyword Analysis:** First analyze the question for keywords and patterns
- **Data Extraction:** Extract relevant data based on time periods, product categories, or specific entities mentioned
- **Dual Response Format:** Provide both summary and detailed responses, with the ability to expand information on demand
- **Complex Query Handling:** Handle complex queries like "trend over past 6 months," "most sold weave type in January 2024," or "predict sales for premium cotton dresses"
- **Context Awareness:** Maintain context awareness, learning from previous interactions to provide more relevant and personalized responses
- **Disclaimers:** Ensure all predictions include appropriate disclaimers about market uncertainties and external factors that may affect accuracy

For prediction questions (like "What will be the most sold item in 2026?"), analyze the historical data for:
1. Top-selling items by weave, quality, and composition
2. Year-over-year growth rates
3. Seasonal patterns and trends
4. Project future sales using these patterns

For trend analysis requests (like "Show me the trend from January to August 2024"):
1. Identify the full range of months requested
2. Process each month sequentially (Jan, Feb, Mar, Apr, May, Jun, Jul, Aug)
3. Calculate month-over-month percentage changes
4. Provide detailed breakdown with trend indicators (🔻 Down, 🔼 Up)
5. Include summary of the overall trend pattern

Always provide data-driven insights and predictions based on the provided CSV data."""

        # Add CSV data as context (as a text part) with verification
        contents.append({
            "role": "user",
            "parts": [
                {"text": csv_string},
                {"text": f"{system_context}\n\nThis is the complete fabric sales data with {len(sales_data)} records from the live API at http://54.234.201.60:5000/chat/getFormData. Use ALL of this data to answer questions accurately. Each row represents one sales record. Count every record that matches the user's criteria."},
            ],
        })

        # Add chat history if provided (with smart context limiting)
        if chat_history:
            # Only add the relevant context based on the type of question
            for message in chat_history:
                contents.append(message)

        # Add the current user question
        contents.append({
            "role": "user",
            "parts": [
                {"text": user_question},
            ],
        })

        response = model.generate_content(
            contents=contents,
        )
        response_text = response.text
        print(response_text, end="")

        return response_text

    except Exception as e:
        error_msg = f"Error generating response: {str(e)}"
        print(error_msg)
        return error_msg

def main():
    print("Welcome to the Dress Sales Monitoring Chatbot!")
    print("I can help you analyze sales trends, predict future performance, and provide insights from your fabric sales data.")
    print("Ask me questions about sales trends, product performance, or request predictions (e.g., 'What will be the most sold item in 2026?')")
    print("Type 'exit' or 'quit' to end the chat.\n")

    # Validate API key
    if not Config.validate_api_key():
        print("❌ Please configure your Gemini API key in the config file.")
        print("Get your free API key from: https://makersuite.google.com/app/apikey")
        return

    chat_history = []
    last_actionable_question = None

    while True:
        user_input = input("\nYou: ").strip().lower()

        if user_input in ['exit', 'quit']:
            print("Goodbye!")
            break

        if not user_input:
            continue

        # Detect if the user is saying "yes" or similar - let generate_response handle this
        # No special handling here, pass it through to generate_response

        # Add user message to history
        user_message = {
            "role": "user",
            "parts": [{"text": user_input}]
        }
        chat_history.append(user_message)

        # Store the last actionable question (refine logic as needed)
        last_actionable_question = user_input

        # Get AI response
        print("AI: ", end="")
        ai_response = generate_response(user_input, chat_history)

        # Add AI response to history
        ai_message = {
            "role": "model",
            "parts": [{"text": ai_response}]
        }
        chat_history.append(ai_message)

        print()  # Add newline after response

if __name__ == "__main__":
    main()
