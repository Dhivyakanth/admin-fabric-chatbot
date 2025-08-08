# 🛍️ Chic Chat Admin - Sales Analytics Dashboard

A full-stack AI-powered sales analytics chatbot for fashion retail businesses. This application combines a Python backend with advanced AI capabilities and a modern React frontend for comprehensive sales data analysis.

## ✨ Features

### 🤖 AI-Powered Analytics
- **Intelligent Sales Analysis**: Get insights on sales trends, customer behavior, and product performance
- **🎭 Festival-Aware Fabric Intelligence**: Advanced festival-specific fabric recommendations with profit-driven insights
- **Predictive Analytics**: Forecast future sales based on historical data
- **Natural Language Queries**: Ask questions in plain English about your sales data
- **Real-time Data Integration**: Live connection to sales APIs for up-to-date analysis

### 🎭 Festival Intelligence Features
- **Smart Festival Detection**: Automatically recognizes 20+ festivals and commercial events
- **Contextual Window Analysis**: Analyzes confirmed bookings [20 days before] to [5 days after] festivals
- **Profit-Driven Recommendations**: Focus on high-margin, high-volume fabric suggestions
- **Fallback Strategy**: Curated traditional recommendations when no booking data exists
- **Trend Predictions**: Future demand forecasting based on historical festival patterns

### 🎨 Modern Interface
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile devices
- **Dark/Light Theme**: Toggle between themes for comfortable viewing
- **Chat-based Interface**: Intuitive conversation flow for data exploration
- **Real-time Backend Status**: Visual indicators for backend connectivity

### 📊 Advanced Features
- **Multi-dimensional Analysis**: Analyze by weave type, quality, composition, agents, customers
- **Trend Analysis**: Month-over-month growth, seasonal patterns, performance metrics
- **Smart Context Handling**: Maintains conversation context for follow-up questions
- **Error Handling**: Robust error handling and user feedback

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+** with pip
- **Node.js 18+** with npm
- **Gemini API Key** (free from Google AI Studio)

### 1️⃣ Setup Environment

1. **Clone/Download** the project to your computer
2. **Get your Gemini API key**:
   - Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create a free account and generate an API key
3. **Configure environment**:
   - Copy `.env.example` to `.env`
   - Edit `.env` and add your API key:
     ```
     GEMINI_API_KEY=your_api_key_here
     ```

### 2️⃣ Start Backend Server

**Option A: Use the startup script (Recommended)**
```bash
# Double-click start-backend.bat or run in terminal:
start-backend.bat
```

**Option B: Manual setup**
```bash
# Install Python dependencies
pip install -r requirements.txt

# Start the Flask server
python flask_server.py
```

The backend will start on `http://127.0.0.1:8000`

### 3️⃣ Start Frontend

**Open a new terminal window** and run:

**Option A: Use the startup script (Recommended)**
```bash
# Double-click start-frontend.bat or run in terminal:
start-frontend.bat
```

**Option B: Manual setup**
```bash
# Install frontend dependencies
npm install

# Start the development server
npm run dev
```

The frontend will start on `http://localhost:5173`

### 4️⃣ Access the Application

1. Open your browser and go to `http://localhost:5173`
2. Login with demo credentials:
   - **Username**: `admin`
   - **Password**: `admin123`
3. Create a new chat and start asking questions about sales data!

## 💡 Example Questions

Try asking these questions to explore the sales analytics:

### 🎭 Festival Fabric Intelligence
- "What fabrics should we stock for Diwali?"
- "Suggest fabrics for Valentine's Day"
- "Recommend profitable fabrics for Holi"
- "Which fabrics performed best during last Christmas?"
- "Show me festival trends for Raksha Bandhan"

### 📈 Sales Analysis
- "What is the most sold weave type?"
- "Show me sales trends for the past 6 months"
- "Which customer bought the most items?"
- "What's the total revenue this year?"

### 🔮 Predictions
- "Predict sales for June 2026"
- "What will be the most sold item next year?"
- "Forecast revenue for 2027"

### 📊 Detailed Analytics
- "Show me premium quality dress sales"
- "Compare agent performance"
- "Analyze cotton dress sales trends"
- "Which month had the highest sales?"

## 🎭 Festival Intelligence System

### **Supported Festivals & Events**
The chatbot provides intelligent fabric recommendations for:

**Major Festivals:**
- Diwali, Holi, Christmas, Eid al-Fitr, Pongal
- Raksha Bandhan, Karva Chauth, Janmashtami, Ganesh Chaturthi, Dussehra

**Commercial Events:**
- Valentine's Day, Mother's Day, Father's Day

**National Holidays:**
- Independence Day, Republic Day, Good Friday

**Sale Periods:**
- Monsoon Sale, Festive Season Sale, Winter Collection Launch, Year-End Sale

### **How Festival Intelligence Works**

1. **Smart Detection**: Automatically identifies festival questions
2. **Window Analysis**: Analyzes confirmed bookings from 20 days before to 5 days after festival dates
3. **Trend Analysis**: Examines weave types, quality grades, and compositions
4. **Profit Focus**: Highlights high-margin and high-volume fabric combinations
5. **Fallback Recommendations**: Provides curated suggestions when no data exists
6. **Future Predictions**: Forecasts demand based on historical patterns

### **Example Festival Responses**

**With Data Available:**
```
🎭 Festival Fabric Intelligence: Diwali

📊 Data Analysis Summary:
Based on confirmed bookings from 15 orders during Diwali period:

🔥 Top Performing Fabrics:
• Premium Cotton: 8 orders (53.3%)
• Zari Silk: 4 orders (26.7%)
• Festive Brocade: 3 orders (20.0%)

💰 Profitability Insight:
• Highest revenue generator: Premium Cotton (₹45,230.00)

📈 Future Trend Prediction:
• Expected growth: 25% increase expected
• Recommended stock increase: 30%
```

**Fallback Strategy:**
```
🎭 Festival Fabric Intelligence: Karva Chauth

📋 Recommendation Status:
There are no recent confirmed orders around Karva Chauth, but based on 
traditional preferences and similar past events, we recommend:

🎯 Curated Fabric Recommendations:
1. Net Lace
2. Silk Crepe  
3. Light Embroidered Satin
```

## 🏗️ Project Structure

```
chic-chat-admin/
├── 📁 Backend (Python)
│   ├── flask_server.py          # Main Flask API server
│   ├── livedata_integration.py  # AI chatbot logic & sales analysis
│   ├── config.py               # Configuration management
│   └── requirements.txt        # Python dependencies
│
├── 📁 Frontend (React + TypeScript)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx   # Main chat interface
│   │   │   └── Login.tsx       # Authentication page
│   │   ├── lib/
│   │   │   └── chatbot-api.ts  # Backend API integration
│   │   └── components/         # Reusable UI components
│   │
│   ├── package.json           # Frontend dependencies
│   └── vite.config.ts        # Build configuration
│
├── 📁 Scripts
│   ├── start-backend.bat     # Backend startup script
│   └── start-frontend.bat    # Frontend startup script
│
└── 📁 Configuration
    ├── .env.example          # Environment template
    └── README.md            # This file
```

## 🔧 API Endpoints

The backend provides these API endpoints:

- `GET /api/health` - Check server status
- `POST /api/chat/new` - Create new chat session
- `POST /api/chat/{id}/message` - Send message to chat
- `GET /api/chats` - Get all chat sessions
- `DELETE /api/chat/{id}` - Delete chat session
- `GET /api/sales/data` - Get raw sales data

## 🎛️ Configuration Options

### Backend Configuration (config.py)
```python
# API Settings
GEMINI_API_KEY = "your_key_here"
SALES_API_URL = "http://54.234.201.60:5000/chat/getFormData"

# Server Settings
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 8000

# CORS Settings
CORS_ORIGINS = ["http://localhost:5173"]
```

### Frontend Configuration (chatbot-api.ts)
```typescript
const API_BASE_URL = 'http://127.0.0.1:8000/api';
```

## 🚨 Troubleshooting

### Backend Issues

**"GEMINI_API_KEY not set"**
- Make sure `.env` file exists with your API key
- Verify the API key is correct and active

**"Port 8000 already in use"**
- Change `FLASK_PORT` in `config.py`
- Or stop other applications using port 8000

**"Failed to fetch sales data"**
- Check internet connection
- Verify the sales API endpoint is accessible

### Frontend Issues

**"Backend Connection Failed"**
- Ensure the backend server is running
- Check if `http://127.0.0.1:8000/api/health` returns success

**"Cannot find module errors"**
- Run `npm install` to install dependencies
- Clear node_modules and reinstall if needed

### General Issues

**"Python/Node.js not found"**
- Install Python 3.8+ from [python.org](https://python.org)
- Install Node.js 18+ from [nodejs.org](https://nodejs.org)

## 📚 Technologies Used

### Backend
- **Flask** - Web framework
- **Google Generative AI** - AI/ML capabilities
- **Flask-CORS** - Cross-origin resource sharing
- **Requests** - HTTP client library

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **Shadcn/ui** - Component library
- **Lucide React** - Icons

## 🤝 Support

If you encounter any issues:

1. Check the troubleshooting section above
2. Verify all prerequisites are installed
3. Ensure your `.env` file is configured correctly
4. Check that both backend and frontend servers are running

## 📄 License

This project is for educational and business use. Please ensure you have proper licensing for any commercial deployment.

---

**Happy Analyzing! 🎉**

Built with ❤️ for modern fashion retail analytics.
