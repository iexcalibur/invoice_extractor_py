import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from components.styles import STYLES
from components.utils import init_session_state, load_invoices_data
from components.overview import show_overview_tab
from components.upload import show_upload_tab
from components.database import show_database_tab
from components.analytics import show_analytics_tab
from components.evaluation import show_evaluation_tab
from components.about import show_about_tab

st.set_page_config(
    page_title="Invoice Extraction Dashboard",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(STYLES, unsafe_allow_html=True)

init_session_state()


def main():
    with st.sidebar:
        st.markdown('<div class="sidebar-title">📄 Invoice Extraction</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown("### Navigation")
        
        page = st.radio(
            "Go to",
            ["Overview", "Upload", "Database", "Analytics", "Evaluation", "About"],
            label_visibility="collapsed"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown("### Quick Stats")
        df = load_invoices_data()
        if not df.empty:
            st.metric("Total Invoices", len(df))
            st.metric("Total Amount", f"${df['total_amount'].sum():,.0f}")
        else:
            st.info("No data yet")
        st.markdown('</div>', unsafe_allow_html=True)
    
    if page == "Overview":
        show_overview_tab()
    elif page == "Upload":
        show_upload_tab()
    elif page == "Database":
        show_database_tab()
    elif page == "Analytics":
        show_analytics_tab()
    elif page == "Evaluation":
        show_evaluation_tab()
    elif page == "About":
        show_about_tab()


if __name__ == "__main__":
    main()
