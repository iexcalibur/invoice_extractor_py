import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from components.utils import load_invoices_data


def show_analytics_tab():
    st.markdown('<div class="section-header">📊 Analytics & Insights</div>', unsafe_allow_html=True)
    
    df = load_invoices_data()
    
    if df.empty:
        st.info("📊 No data to visualize yet. Upload some invoices first!")
        return
    
    if 'invoice_date' in df.columns:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.subheader("📈 Invoices Over Time")
        
        time_series = df.groupby(df['invoice_date'].dt.date)['total_amount'].agg(['count', 'sum']).reset_index()
        time_series.columns = ['Date', 'Count', 'Total Amount']
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=time_series['Date'],
            y=time_series['Count'],
            name='Invoice Count',
            marker_color='#667eea'
        ))
        
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Number of Invoices",
            hovermode='x',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.subheader("🏢 Spend by Vendor")
        
        vendor_spend = df.groupby('vendor_name')['total_amount'].sum().sort_values(ascending=False)
        
        fig = px.bar(
            x=vendor_spend.index,
            y=vendor_spend.values,
            labels={'x': 'Vendor', 'y': 'Total Amount ($)'},
            color_discrete_sequence=['#667eea']
        )
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        st.subheader("🔧 Extraction Methods")
        
        method_counts = df['extraction_method'].value_counts()
        
        fig = px.pie(
            values=method_counts.values,
            names=method_counts.index,
            hole=0.5,
            color_discrete_sequence=['#667eea', '#764ba2', '#56CCF2', '#2F80ED']
        )
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-header">📊 Summary Statistics</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="metric-container" style="margin-bottom: 10px;">
            <div class="metric-label">Average Invoice</div>
            <div class="metric-value">${df['total_amount'].mean():,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class="metric-container" style="margin-bottom: 10px;">
            <div class="metric-label">Median Invoice</div>
            <div class="metric-value">${df['total_amount'].median():,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-container" style="margin-bottom: 10px;">
            <div class="metric-label">Largest Invoice</div>
            <div class="metric-value">${df['total_amount'].max():,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class="metric-container" style="margin-bottom: 10px;">
            <div class="metric-label">Smallest Invoice</div>
            <div class="metric-value">${df['total_amount'].min():,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-container" style="margin-bottom: 10px;">
            <div class="metric-label">Std Deviation</div>
            <div class="metric-value">${df['total_amount'].std():,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div class="metric-container" style="margin-bottom: 10px;">
            <div class="metric-label">Total Revenue</div>
            <div class="metric-value">${df['total_amount'].sum():,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

