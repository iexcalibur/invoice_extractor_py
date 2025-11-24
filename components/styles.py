"""
CSS styles for the Streamlit app
"""

STYLES = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
    
    /* Global Styles */
    * {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    code, pre {
        font-family: 'JetBrains Mono', monospace;
    }
    
    /* Main Container */
    .main {
        background: linear-gradient(135deg, #f0fdfa 0%, #e0f2fe 100%);
        padding: 2rem;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Custom Header */
    .dashboard-header {
        background: linear-gradient(135deg, #06b6d4 0%, #10b981 100%);
        padding: 2rem 2.5rem;
        border-radius: 24px;
        margin-bottom: 2rem;
        box-shadow: 0 20px 60px rgba(6, 182, 212, 0.3);
        color: white;
    }
    
    .dashboard-title {
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.02em;
    }
    
    .dashboard-subtitle {
        font-size: 1.1rem;
        font-weight: 400;
        margin-top: 0.5rem;
        opacity: 0.95;
    }
    
    /* Card Styles */
    .custom-card {
        background: white;
        border-radius: 20px;
        padding: 1.8rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        margin-bottom: 1.5rem;
        transition: all 0.3s ease;
        border: 1px solid rgba(0, 0, 0, 0.05);
    }
    
    .custom-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
    }
    
    /* Folder Cards */
    .folder-card {
        background: linear-gradient(135deg, #06b6d4 0%, #10b981 100%);
        border-radius: 20px;
        padding: 2rem;
        color: white;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 8px 25px rgba(6, 182, 212, 0.3);
        min-height: 180px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    
    .folder-card:hover {
        transform: translateY(-6px) scale(1.02);
        box-shadow: 0 12px 35px rgba(6, 182, 212, 0.4);
    }
    
    .folder-card.green {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    }
    
    .folder-card.purple {
        background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);
    }
    
    .folder-card.orange {
        background: linear-gradient(135deg, #f59e0b 0%, #f97316 100%);
    }
    
    .folder-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    
    .folder-name {
        font-size: 1.3rem;
        font-weight: 700;
        margin: 0;
    }
    
    .folder-size {
        font-size: 0.9rem;
        opacity: 0.9;
        margin-top: 0.5rem;
    }
    
    /* Metrics */
    .metric-container {
        background: white;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .metric-container:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
    }
    
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: #06b6d4;
        margin: 0.5rem 0;
    }
    
    .metric-label {
        font-size: 0.95rem;
        color: #64748b;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* File List */
    .file-item {
        background: white;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        transition: all 0.2s ease;
        border: 1px solid rgba(0, 0, 0, 0.05);
    }
    
    .file-item:hover {
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
        transform: translateX(4px);
    }
    
    .file-icon {
        width: 44px;
        height: 44px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        margin-right: 1rem;
    }
    
    .file-icon.pdf {
        background: linear-gradient(135deg, #f59e0b 0%, #f97316 100%);
    }
    
    .file-icon.image {
        background: linear-gradient(135deg, #06b6d4 0%, #0ea5e9 100%);
    }
    
    .file-icon.zip {
        background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);
    }
    
    .file-name {
        font-weight: 600;
        color: #1e293b;
        font-size: 1rem;
    }
    
    .file-meta {
        color: #64748b;
        font-size: 0.85rem;
        margin-top: 0.2rem;
    }
    
    /* Status Boxes */
    .status-box {
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        border-left: 5px solid;
        background: white;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    }
    
    .status-box.success {
        border-left-color: #10b981;
        background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
    }
    
    .status-box.warning {
        border-left-color: #f59e0b;
        background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
    }
    
    .status-box.error {
        border-left-color: #ef4444;
        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
    }
    
    .status-icon {
        font-size: 1.8rem;
        margin-right: 1rem;
    }
    
    .status-title {
        font-size: 1.2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .status-text {
        font-size: 1rem;
        line-height: 1.6;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #06b6d4 0%, #10b981 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(6, 182, 212, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(6, 182, 212, 0.4);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        padding: 2rem 1rem;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: white;
    }
    
    .sidebar-section {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
        backdrop-filter: blur(10px);
    }
    
    .sidebar-title {
        color: white;
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
    }
    
    .sidebar-item {
        color: rgba(255, 255, 255, 0.8);
        padding: 0.6rem 0.8rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        transition: all 0.2s ease;
        cursor: pointer;
    }
    
    .sidebar-item:hover {
        background: rgba(255, 255, 255, 0.15);
        color: white;
    }
    
    .sidebar-item.active {
        background: linear-gradient(135deg, #06b6d4 0%, #10b981 100%);
        color: white;
    }
    
    /* Section Headers */
    .section-header {
        font-size: 1.5rem;
        font-weight: 700;
        color: white;
        margin: 2rem 0 1.5rem 0;
        display: flex;
        align-items: center;
    }
    
    .section-header::before {
        content: '';
        width: 4px;
        height: 28px;
        background: linear-gradient(135deg, #06b6d4 0%, #10b981 100%);
        border-radius: 2px;
        margin-right: 1rem;
    }
    
    /* Dataframe Styling */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    }
    
    /* Progress Bar */
    .stProgress > div > div {
        background: linear-gradient(90deg, #06b6d4 0%, #10b981 100%);
        border-radius: 10px;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: white;
        border-radius: 16px;
        padding: 0.5rem;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 12px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        color: #64748b;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #06b6d4 0%, #10b981 100%);
        color: white;
    }
    
    /* HIDE DEFAULT FILE UPLOADER */
    [data-testid="stFileUploader"] {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border-width: 0;
        opacity: 0;
        pointer-events: none;
    }
    
    /* Custom Upload Area Styling */
    .upload-area-wrapper {
        margin-bottom: 1rem;
        position: relative;
        z-index: 1;
    }
    
    .upload-area {
        background: white;
        border: 3px dashed #06b6d4;
        border-radius: 24px;
        padding: 3rem 2rem;
        text-align: center;
        transition: all 0.3s ease;
        cursor: pointer;
        position: relative;
        overflow: hidden;
        min-height: 350px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    
    .upload-area::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(45deg, transparent, rgba(6, 182, 212, 0.05), transparent);
        transform: rotate(45deg);
        transition: all 0.5s ease;
        pointer-events: none;
    }
    
    .upload-area:hover {
        border-color: #10b981;
        background: linear-gradient(135deg, #fefeff 0%, #f0fdfa 100%);
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(6, 182, 212, 0.15);
    }
    
    .upload-area:hover::before {
        left: 100%;
    }
    
    .upload-area:active {
        transform: translateY(0);
        box-shadow: 0 4px 15px rgba(6, 182, 212, 0.2);
    }
    
    .upload-cloud-icon {
        width: 100px;
        height: 100px;
        color: #06b6d4;
        margin-bottom: 1.5rem;
        transition: all 0.3s ease;
    }
    
    .upload-area:hover .upload-cloud-icon {
        color: #10b981;
        transform: translateY(-8px);
    }
    
    .upload-text {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.5rem;
    }
    
    .upload-subtext {
        font-size: 1.2rem;
        color: #475569;
        margin-bottom: 1rem;
    }
    
    .upload-hint {
        font-size: 0.95rem;
        color: #64748b;
        margin-top: 1rem;
    }
    
    /* Animations */
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .custom-card, .metric-container, .file-item {
        animation: fadeIn 0.4s ease-out;
    }
    
    /* File List Container */
    .file-list-container {
        background: white;
        border-radius: 20px;
        padding: 1.5rem;
        min-height: 400px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
    }
    
    .empty-file-list {
        background: white;
        border-radius: 20px;
        padding: 1.5rem;
        min-height: 400px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    /* Upload File Item */
    .upload-file-item {
        background: #f8fafc;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: all 0.2s ease;
        border: 1px solid #e2e8f0;
    }
    
    .upload-file-item:hover {
        background: #f1f5f9;
        border-color: #cbd5e1;
        transform: translateX(2px);
    }
    
    .upload-file-icon {
        width: 48px;
        height: 48px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        margin-right: 1rem;
        flex-shrink: 0;
    }
    
    .upload-file-name {
        font-weight: 600;
        color: #1e293b;
        font-size: 0.95rem;
        margin-bottom: 0.3rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 250px;
    }
    
    .upload-file-size {
        font-size: 0.8rem;
        color: #94a3b8;
        margin-bottom: 0.4rem;
    }
    
    .upload-progress-bar {
        width: 100%;
        height: 4px;
        background: #e2e8f0;
        border-radius: 2px;
        overflow: hidden;
    }
    
    .upload-progress-fill {
        height: 100%;
        border-radius: 2px;
        transition: width 0.3s ease;
    }
    
    .upload-status-icon {
        font-size: 1.3rem;
        margin-left: 1rem;
        flex-shrink: 0;
    }
    
    /* Files Header with Count Badge */
    .files-header {
        margin-top: 2rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        justify-content: flex-start;
    }
    
    .files-count-badge {
        display: inline-flex;
        align-items: center;
        background: linear-gradient(135deg, #06b6d4 0%, #10b981 100%);
        padding: 0.75rem 1.5rem;
        border-radius: 16px;
        box-shadow: 0 4px 15px rgba(6, 182, 212, 0.3);
        animation: fadeIn 0.4s ease-out;
    }
    
    .clipboard-icon {
        font-size: 1.5rem;
        margin-right: 0.75rem;
    }
    
    .files-count-text {
        font-size: 1.1rem;
        font-weight: 700;
        color: white;
    }
    
    /* Dark Files Container */
    .files-container {
        background: #2d3748;
        border-radius: 20px;
        padding: 1.5rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        margin-bottom: 1.5rem;
    }
    
    /* Dark File Item */
    .dark-file-item {
        background: #1a202c;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: all 0.2s ease;
        border: 1px solid #4a5568;
    }
    
    .dark-file-item:hover {
        background: #2d3748;
        border-color: #718096;
        transform: translateX(2px);
    }
    
    .dark-file-item:last-child {
        margin-bottom: 0;
    }
    
    .dark-file-icon {
        width: 52px;
        height: 52px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.8rem;
        margin-right: 1rem;
        flex-shrink: 0;
    }
    
    .dark-file-name {
        font-weight: 600;
        color: #f7fafc;
        font-size: 1rem;
        margin-bottom: 0.4rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 600px;
    }
    
    .dark-file-size {
        font-size: 0.85rem;
        color: #a0aec0;
        margin-bottom: 0.5rem;
    }
    
    .dark-progress-bar {
        width: 100%;
        height: 5px;
        background: #4a5568;
        border-radius: 3px;
        overflow: hidden;
    }
    
    .dark-progress-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.3s ease;
    }
    
    .dark-status-icon {
        font-size: 1.5rem;
        margin-left: 1rem;
        flex-shrink: 0;
    }
    
    /* Extraction Progress Header */
    .extraction-progress-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
        border-radius: 16px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(30, 58, 138, 0.3);
        width: 100%;
    }
    
    .progress-info {
        display: flex;
        align-items: center;
        width: 100%;
    }
    
    .progress-icon {
        font-size: 2rem;
        margin-right: 1rem;
        flex-shrink: 0;
    }
    
    .progress-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: white;
        flex: 1;
    }
    
    /* Full width progress bar */
    .stProgress {
        width: 100%;
    }
    
    .stProgress > div {
        width: 100%;
    }
    
    /* Status Messages */
    .status-message {
        padding: 1rem 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        font-size: 1.1rem;
        font-weight: 600;
        display: flex;
        align-items: center;
        animation: fadeIn 0.3s ease-out;
        width: 100%;
        box-sizing: border-box;
    }
    
    .status-message.processing {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border-left: 4px solid #1d4ed8;
    }
    
    .status-message.success {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        border-left: 4px solid #047857;
    }
    
    .status-message.warning {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
        border-left: 4px solid #b45309;
    }
    
    .status-message.error {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
        border-left: 4px solid #b91c1c;
    }
    
    .status-spinner {
        margin-right: 0.75rem;
        font-size: 1.3rem;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        from {
            transform: rotate(0deg);
        }
        to {
            transform: rotate(360deg);
        }
    }

</style>
"""