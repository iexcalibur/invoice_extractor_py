"""
Overview tab component
"""
import streamlit as st
import pandas as pd
from components.utils import load_invoices_data


def show_overview_tab():
    """Display the overview tab"""
    st.markdown("""
    <div class="dashboard-header">
        <h1 class="dashboard-title">📄 Invoice Extraction Dashboard</h1>
        <p class="dashboard-subtitle">Hybrid AI system for automated invoice data extraction</p>
    </div>
    """, unsafe_allow_html=True)
    
    df = load_invoices_data()
    
    # Metrics Section
    st.markdown('<div class="section-header">📊 Overview</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_invoices = len(df) if not df.empty else 0
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Total Invoices</div>
            <div class="metric-value">{total_invoices}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_amount = df['total_amount'].sum() if not df.empty else 0
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Total Amount</div>
            <div class="metric-value">${total_amount:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        unique_vendors = df['vendor_name'].nunique() if not df.empty else 0
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Unique Vendors</div>
            <div class="metric-value">{unique_vendors}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        avg_amount = df['total_amount'].mean() if not df.empty else 0
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Avg Invoice</div>
            <div class="metric-value">${avg_amount:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Folder Cards Section
    st.markdown('<div class="section-header" style="margin-top: 3rem;">📁 Quick Actions</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="folder-card">
            <div class="folder-icon">📤</div>
            <div class="folder-name">Upload</div>
            <div class="folder-size">Extract Invoices</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="folder-card green">
            <div class="folder-icon">🗄️</div>
            <div class="folder-name">Database</div>
            <div class="folder-size">Browse Records</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="folder-card purple">
            <div class="folder-icon">📊</div>
            <div class="folder-name">Analytics</div>
            <div class="folder-size">View Insights</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="folder-card orange">
            <div class="folder-icon">✅</div>
            <div class="folder-name">Evaluation</div>
            <div class="folder-size">Performance Metrics</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Recent Files Section
    if not df.empty:
        st.markdown('<div class="section-header" style="margin-top: 3rem;">📋 Recent Invoices</div>', unsafe_allow_html=True)
        
        recent_df = df.sort_values('created_at', ascending=False).head(5) if 'created_at' in df.columns else df.head(5)
        
        for idx, row in recent_df.iterrows():
            invoice_num = row.get('invoice_number', 'N/A')
            vendor = row.get('vendor_name', 'N/A')
            date = row.get('invoice_date', 'N/A')
            amount = row.get('total_amount', 0)
            
            if isinstance(date, pd.Timestamp):
                date_str = date.strftime('%b %d, %Y')
            else:
                date_str = str(date)
            
            st.markdown(f"""
            <div class="file-item">
                <div style="display: flex; align-items: center; flex: 1;">
                    <div class="file-icon pdf">📄</div>
                    <div>
                        <div class="file-name">{invoice_num} - {vendor}</div>
                        <div class="file-meta">{date_str} · ${amount:,.2f}</div>
                    </div>
                </div>
                <div style="color: #64748b; font-size: 0.9rem;">{date_str}</div>
            </div>
            """, unsafe_allow_html=True)

