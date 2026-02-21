"""
Custom CSS styles for the application with enhanced McKinsey-style aesthetics.
"""

def get_custom_css():
    return """
    <style>
        /* Import Professional Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* General App Styling - Dark Theme */
        .stApp {
            background-color: #0a0a0a;
            color: #E0E0E0;
            font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }

        /* Typography */
        h1, h2, h3, h4 {
            color: #FFFFFF;
            font-weight: 600;
            font-family: 'Inter', sans-serif;
        }
        
        h1 {
            font-size: 2.5rem !important;
            letter-spacing: -0.5px;
        }
        
        h2 {
            font-size: 1.8rem !important;
            color: #64B5F6;
        }
        
        p, div, label, span {
            color: #E0E0E0;
        }

        /* Metric Styling */
        [data-testid="stMetricValue"] {
            color: #FFFFFF !important;
            font-size: 1.8rem !important;
        }
        [data-testid="stMetricLabel"] {
            color: #B0B0B0 !important;
        }

        /* ===== Enhanced Meeting Selection Styling ===== */
        .meeting-selector-container {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            padding: 30px;
            border-radius: 16px;
            border: 1px solid rgba(100, 181, 246, 0.3);
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        }
        
        .meeting-selector-label {
            font-size: 1.4rem;
            color: #64B5F6;
            margin-bottom: 15px;
            display: block;
            font-weight: 600;
            letter-spacing: 0.5px;
        }

        /* Customize Selectbox - Make it Premium */
        div[data-baseweb="select"] > div {
            background: linear-gradient(135deg, #1E3A5F 0%, #0D2137 100%) !important;
            border: 2px solid #1976D2 !important;
            border-radius: 12px !important;
            padding: 8px 12px !important;
            font-size: 1.3rem !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
        }
        
        div[data-baseweb="select"] > div:hover {
            border-color: #42A5F5 !important;
            box-shadow: 0 0 20px rgba(66, 165, 245, 0.3) !important;
        }
        
        div[data-baseweb="select"] span {
            color: #FFFFFF !important;
            font-size: 1.2rem !important;
            font-weight: 500 !important;
        }
        
        /* Dropdown Menu Styling */
        [data-baseweb="popover"] {
            background-color: #1E3A5F !important;
        }
        
        [data-baseweb="menu"] {
            background-color: #1E3A5F !important;
        }
        
        li[role="option"] {
            color: white !important;
            font-size: 1.1rem !important;
            padding: 12px 16px !important;
        }
        
        li[role="option"]:hover {
            background-color: #2196F3 !important;
        }

        /* ===== Premium Analysis Button ===== */
        .stButton > button {
            background: linear-gradient(135deg, #1565C0 0%, #0D47A1 50%, #1976D2 100%) !important;
            color: white !important;
            border: none !important;
            padding: 18px 40px !important;
            font-size: 1.2rem !important;
            font-weight: 700 !important;
            letter-spacing: 1px !important;
            text-transform: uppercase !important;
            border-radius: 12px !important;
            cursor: pointer !important;
            width: 100% !important;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
            box-shadow: 0 6px 20px rgba(21, 101, 192, 0.4) !important;
            position: relative !important;
            overflow: hidden !important;
        }
        
        .stButton > button:hover {
            background: linear-gradient(135deg, #1976D2 0%, #1565C0 50%, #2196F3 100%) !important;
            transform: translateY(-3px) !important;
            box-shadow: 0 10px 30px rgba(33, 150, 243, 0.5) !important;
        }
        
        .stButton > button:active {
            transform: translateY(0) !important;
        }

        /* Back Button Specific Style */
        .stButton > button[kind="secondary"] {
            background: linear-gradient(135deg, #424242 0%, #212121 100%) !important;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
        }
        
        .stButton > button[kind="secondary"]:hover {
            background: linear-gradient(135deg, #616161 0%, #424242 100%) !important;
        }

        /* ===== Report Container ===== */
        .report-container {
            background-color: #121212;
            padding: 40px;
            border-radius: 2px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            margin-top: 20px;
            border-top: 5px solid #1976D2;
        }

        /* ===== Sidebar Styling ===== */
        section[data-testid="stSidebar"] {
            background-color: #0d1117 !important;
            border-right: 1px solid #21262d;
        }
        
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: #58a6ff !important;
        }

        /* ===== DataFrame/Table Styling ===== */
        .stDataFrame {
            border-radius: 10px;
            overflow: hidden;
        }

        /* ===== Horizontal Rule ===== */
        hr {
            border: none;
            height: 1px;
            background: linear-gradient(90deg, transparent, #444, transparent);
            margin: 30px 0;
        }

        /* ===== Plotly Chart Background ===== */
        .js-plotly-plot .plotly .main-svg {
            background-color: transparent !important;
        }

        /* ===== Mobile Sidebar Toggle Styles ===== */
        /* Mobile menu toggle button */
        .mobile-menu-toggle {
            display: none;
            position: fixed;
            top: 10px;
            left: 10px;
            z-index: 999999;
            background: linear-gradient(135deg, #1565C0 0%, #0D47A1 100%) !important;
            color: white !important;
            border: none !important;
            padding: 12px 20px !important;
            font-size: 0.95rem !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            cursor: pointer !important;
            box-shadow: 0 4px 15px rgba(21, 101, 192, 0.5) !important;
            transition: all 0.3s ease !important;
            font-family: 'Inter', sans-serif !important;
        }
        
        .mobile-menu-toggle:hover {
            background: linear-gradient(135deg, #1976D2 0%, #1565C0 100%) !important;
            box-shadow: 0 6px 20px rgba(33, 150, 243, 0.6) !important;
            transform: translateY(-2px) !important;
        }

        /* Desktop sidebar always visible */
        @media screen and (min-width: 769px) {
            section[data-testid="stSidebar"] {
                transform: translateX(0) !important;
                position: relative !important;
                width: auto !important;
            }
            
            /* Hide mobile toggle on desktop */
            .mobile-menu-toggle {
                display: none !important;
            }
            
            /* Hide overlay on desktop */
            .sidebar-overlay {
                display: none !important;
            }
        }

        /* Mobile responsive styles */
        @media screen and (max-width: 768px) {
            /* Show mobile toggle button */
            .mobile-menu-toggle {
                display: flex !important;
                align-items: center;
                gap: 8px;
            }
            
            /* Hide sidebar by default on mobile */
            section[data-testid="stSidebar"] {
                transform: translateX(-100%) !important;
                transition: transform 0.3s ease-in-out !important;
                position: fixed !important;
                left: 0 !important;
                top: 0 !important;
                height: 100vh !important;
                z-index: 999998 !important;
                width: 300px !important;
                box-shadow: 2px 0 20px rgba(0,0,0,0.8) !important;
            }
            
            /* Show sidebar when open */
            section[data-testid="stSidebar"].mobile-open {
                transform: translateX(0) !important;
            }
            
            /* Overlay when sidebar is open */
            .sidebar-overlay {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: rgba(0, 0, 0, 0.6);
                z-index: 999997;
                backdrop-filter: blur(3px);
            }
            
            .sidebar-overlay.active {
                display: block !important;
            }
            
            /* Adjust main content for mobile */
            section.main > div {
                padding-top: 60px !important;
            }
            
            /* Hide default sidebar collapse button on mobile */
            button[kind="header"] {
                display: none !important;
            }
        }

    </style>
    """
