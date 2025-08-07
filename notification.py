"""
Notification System Module
Handles all notification and festival-related functionality for the Dress Sales Monitoring Chatbot.
"""

from datetime import datetime, timedelta
from collections import Counter
import calendar


# Festival Data
FESTIVALS = [
    {"name": "New Year", "date": "2025-01-01", "category": "Public Holiday"},
    {"name": "Republic Day", "date": "2025-01-26", "category": "National Holiday"},
    {"name": "Holi", "date": "2025-03-14", "category": "Festival"},
    {"name": "Good Friday", "date": "2025-04-18", "category": "Religious"},
    {"name": "Eid al-Fitr", "date": "2025-04-30", "category": "Religious"},
    {"name": "Independence Day", "date": "2025-08-15", "category": "National Holiday"},
    {"name": "Janmashtami", "date": "2025-08-26", "category": "Festival"},
    {"name": "Ganesh Chaturthi", "date": "2025-08-29", "category": "Festival"},
    {"name": "Gandhi Jayanti", "date": "2025-10-02", "category": "National Holiday"},
    {"name": "Dussehra", "date": "2025-10-22", "category": "Festival"},
    {"name": "Diwali", "date": "2025-11-01", "category": "Festival"},
    {"name": "Christmas", "date": "2025-12-25", "category": "Religious"},
    
    # Valentine's Day and other commercial festivals
    {"name": "Valentine's Day", "date": "2025-02-14", "category": "Commercial"},
    {"name": "Mother's Day", "date": "2025-05-11", "category": "Commercial"},
    {"name": "Father's Day", "date": "2025-06-15", "category": "Commercial"},
    {"name": "Raksha Bandhan", "date": "2025-08-09", "category": "Festival"},
    {"name": "Karva Chauth", "date": "2025-10-20", "category": "Festival"},
    {"name": "Bhai Dooj default", "date": "2025-07-31", "category": "Festival"},
    
    # Seasonal sales periods
    {"name": "Summer Sale Season", "date": "2025-04-01", "category": "Sale Period"},
    {"name": "Monsoon Sale", "date": "2025-07-01", "category": "Sale Period"},
    {"name": "Festive Season Sale", "date": "2025-09-15", "category": "Sale Period"},
    {"name": "Winter Collection Launch", "date": "2025-11-15", "category": "Sale Period"},
    {"name": "Year End Sale", "date": "2025-12-15", "category": "Sale Period"}
]


def get_upcoming_festivals_data(days_ahead=10):
    """
    Get upcoming festivals within the specified number of days.
    
    Args:
        days_ahead (int): Number of days to look ahead for festivals (default: 10)
    
    Returns:
        list: List of upcoming festival dictionaries with additional information
    """
    current_date = datetime.now().date()
    upcoming_festivals = []
    
    for festival in FESTIVALS:
        festival_date = datetime.strptime(festival["date"], "%Y-%m-%d").date()
        days_until = (festival_date - current_date).days

        # Check if festival is within specified days
        if 0 <= days_until <= days_ahead:
            upcoming_festivals.append({
                **festival,
                "days_until": days_until,
                "is_today": days_until == 0
            })
    
    return upcoming_festivals


def get_festival_recommendations(festival_name, category, sales_data=None):
    """
    Get specific recommendations for each festival based on actual sales data.
    
    Args:
        festival_name (str): Name of the festival
        category (str): Category of the festival
        sales_data (list): Sales data for analysis (optional)
    
    Returns:
        dict: Recommendations dictionary with stock updates, discounts, and marketing tips
    """
    recommendations = {
        "stock_updates": [],
        "discount_suggestions": [],
        "marketing_tips": []
    }
    
    # Get current month's sales data for analysis if provided
    if sales_data:
        try:
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            print(f"🔍 Analyzing recommendations for {festival_name} ({category})")
            print(f"📅 Current month: {current_month}, Current year: {current_year}")
            print(f"📊 Total sales records: {len(sales_data)}")
            
            # Filter data for current month
            current_month_sales = []
            for record in sales_data:
                try:
                    # Check both 'date' and 'orderDate' fields
                    order_date = record.get('date') or record.get('orderDate', '')
                    if order_date:
                        # Parse ISO date format (2025-07-09T13:03:42.202Z) or simple date
                        if 'T' in order_date:
                            date_obj = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
                        else:
                            date_obj = datetime.strptime(order_date, "%Y-%m-%d")
                        
                        if date_obj.month == current_month and date_obj.year == current_year:
                            current_month_sales.append(record)
                except (ValueError, TypeError) as e:
                    print(f"Date parsing error for record {record.get('_id', 'unknown')}: {e}")
                    continue
            
            print(f"📈 Current month sales: {len(current_month_sales)}")
            
            # Analyze most sold items
            weave_counter = Counter()
            quality_counter = Counter()
            composition_counter = Counter()
            
            for record in current_month_sales:
                if record.get('weave'):
                    weave_counter[record['weave']] += 1
                if record.get('quality'):
                    quality_counter[record['quality']] += 1
                if record.get('composition'):
                    composition_counter[record['composition']] += 1
            
            print(f"👗 Weave analysis: {dict(weave_counter)}")
            print(f"💎 Quality analysis: {dict(quality_counter)}")
            print(f"🧵 Composition analysis: {dict(composition_counter)}")
            
            # Get top items
            top_weave = weave_counter.most_common(1)
            top_quality = quality_counter.most_common(1)
            top_composition = composition_counter.most_common(1)
            
            # Build stock update recommendations based on actual data
            stock_recommendations = []
            if top_weave:
                stock_recommendations.append(f"Increase {top_weave[0][0]} weave inventory (top seller this month)")
            if top_quality:
                stock_recommendations.append(f"Stock more {top_quality[0][0]} quality items (high demand)")
            if top_composition:
                stock_recommendations.append(f"Focus on {top_composition[0][0]} composition (best performing)")
            
            print(f"💡 Generated recommendations: {stock_recommendations}")
            
            if stock_recommendations:
                recommendations["stock_updates"] = stock_recommendations
            
        except Exception as e:
            print(f"Error analyzing sales data for recommendations: {e}")
    
    # If no data-based recommendations or no sales data provided, use generic recommendations
    if not recommendations["stock_updates"]:
        if category == "Festival" or festival_name in ["Diwali", "Holi", "Ganesh Chaturthi"]:
            recommendations["stock_updates"] = [
                "Increase ethnic wear inventory",
                "Stock traditional jewelry",
                "Prepare festive color collections"
            ]
        else:
            recommendations["stock_updates"] = [
                "Monitor current sales trends",
                "Update inventory based on demand",
                "Prepare seasonal collections"
            ]
        print(f"📋 Using fallback recommendations: {recommendations['stock_updates']}")
    
    # Set discount suggestions and marketing tips based on category
    if category == "Festival" or festival_name in ["Diwali", "Holi", "Ganesh Chaturthi"]:
        recommendations["discount_suggestions"] = [
            "20-30% off on ethnic wear",
            "Buy 2 Get 1 on accessories",
            "Festive combo deals"
        ]
        recommendations["marketing_tips"] = [
            "Highlight traditional designs",
            "Create festive lookbooks",
            "Partner with local influencers"
        ]
    elif category == "Commercial" or festival_name in ["Valentine's Day", "Mother's Day"]:
        recommendations["discount_suggestions"] = [
            "15-25% off on premium items",
            "Free gift wrapping",
            "Couple's discount packages"
        ]
        recommendations["marketing_tips"] = [
            "Create romantic campaigns",
            "Offer personalization",
            "Target gift buyers"
        ]
    elif category == "Sale Period":
        recommendations["discount_suggestions"] = [
            "Up to 50% off clearance",
            "Season launch offers",
            "Bulk purchase discounts"
        ]
        recommendations["marketing_tips"] = [
            "Heavy social media promotion",
            "Email marketing campaigns",
            "Flash sale announcements"
        ]
    else:  # National holidays, Religious festivals
        recommendations["discount_suggestions"] = [
            "10-20% seasonal discounts",
            "Free shipping offers",
            "Loyalty rewards"
        ]
        recommendations["marketing_tips"] = [
            "Respectful themed content",
            "Community engagement",
            "Cultural celebration posts"
        ]
    
    return recommendations


def get_all_festivals():
    """
    Get all festivals data.
    
    Returns:
        list: List of all festival dictionaries
    """
    return FESTIVALS.copy()


def is_festival_today():
    """
    Check if today is a festival.
    
    Returns:
        dict or None: Festival dictionary if today is a festival, None otherwise
    """
    today = datetime.now().date()
    
    for festival in FESTIVALS:
        fest_date = datetime.strptime(festival["date"], "%Y-%m-%d").date()
        if fest_date == today:
            return festival
    
    return None


def get_next_festival():
    """
    Get the next upcoming festival.
    
    Returns:
        dict or None: Next festival dictionary with days_left, None if no upcoming festivals
    """
    today = datetime.now().date()
    next_festival = None
    min_days = float('inf')
    
    for festival in FESTIVALS:
        fest_date = datetime.strptime(festival["date"], "%Y-%m-%d").date()
        days_left = (fest_date - today).days
        
        if days_left >= 0 and days_left < min_days:
            min_days = days_left
            next_festival = festival.copy()
            next_festival["days_left"] = days_left
    
    return next_festival


def get_festivals_in_month(month, year=None):
    """
    Get all festivals occurring in a specific month.
    
    Args:
        month (int): Month number (1-12)
        year (int): Year (optional, defaults to current year)
    
    Returns:
        list: List of festival dictionaries for the specified month
    """
    if year is None:
        year = datetime.now().year
    
    festivals_in_month = []
    
    for festival in FESTIVALS:
        fest_date = datetime.strptime(festival["date"], "%Y-%m-%d")
        if fest_date.month == month and fest_date.year == year:
            festivals_in_month.append(festival)
    
    return festivals_in_month


def generate_festival_notification_message(festival):
    """
    Generate a notification message for a specific festival.
    
    Args:
        festival (dict): Festival dictionary with name and days_until
    
    Returns:
        str: Notification message
    """
    days_until = festival.get("days_until", 0)
    name = festival.get("name", "Festival")
    
    if days_until == 0:
        return f"🎉 Happy {name}! Great day for sales!"
    elif days_until == 1:
        return f"🎊 {name} is tomorrow! Consider special promotions."
    else:
        return f"🎊 {name} is in {days_until} days! Consider special promotions."


def get_seasonal_recommendations():
    """
    Get seasonal business recommendations based on current date.
    
    Returns:
        dict: Seasonal recommendations
    """
    current_month = datetime.now().month
    
    # Seasonal recommendations based on month
    seasonal_data = {
        1: {  # January
            "season": "Winter",
            "recommendations": [
                "Focus on warm fabrics and winter collections",
                "New Year promotion campaigns",
                "Clearance of previous year stock"
            ]
        },
        2: {  # February
            "season": "Late Winter",
            "recommendations": [
                "Valentine's Day special collections",
                "Romantic color themes",
                "Couple's discount packages"
            ]
        },
        3: {  # March
            "season": "Spring",
            "recommendations": [
                "Spring collection launch",
                "Holi festival preparations",
                "Bright and vibrant colors"
            ]
        },
        4: {  # April
            "season": "Spring",
            "recommendations": [
                "Summer collection preparation",
                "Light fabrics and breathable materials",
                "Easter and spring festivities"
            ]
        },
        5: {  # May
            "season": "Late Spring",
            "recommendations": [
                "Mother's Day promotions",
                "Summer collection highlights",
                "Light cotton and linen focus"
            ]
        },
        6: {  # June
            "season": "Early Summer",
            "recommendations": [
                "Father's Day campaigns",
                "Summer sale preparations",
                "Monsoon collection preview"
            ]
        },
        7: {  # July
            "season": "Monsoon",
            "recommendations": [
                "Monsoon-appropriate fabrics",
                "Quick-dry and water-resistant materials",
                "Raksha Bandhan preparations"
            ]
        },
        8: {  # August
            "season": "Monsoon",
            "recommendations": [
                "Independence Day patriotic themes",
                "Festival season preparations",
                "Traditional and ethnic wear"
            ]
        },
        9: {  # September
            "season": "Post-Monsoon",
            "recommendations": [
                "Festival season launch",
                "Navaratri special collections",
                "Traditional and designer wear"
            ]
        },
        10: {  # October
            "season": "Festival Season",
            "recommendations": [
                "Diwali collection highlights",
                "Premium and luxury segments",
                "Gift packaging options"
            ]
        },
        11: {  # November
            "season": "Post-Festival",
            "recommendations": [
                "Wedding season preparations",
                "Winter collection launch",
                "Clearance of festival stock"
            ]
        },
        12: {  # December
            "season": "Winter/Holiday",
            "recommendations": [
                "Christmas and year-end promotions",
                "Holiday party wear",
                "New Year collection teasers"
            ]
        }
    }
    
    return seasonal_data.get(current_month, {
        "season": "General",
        "recommendations": ["Monitor sales trends", "Update inventory", "Plan seasonal campaigns"]
    })
