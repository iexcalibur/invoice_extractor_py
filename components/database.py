import streamlit as st
import pandas as pd
from datetime import datetime
from components.utils import load_invoices_data, init_database


def show_database_tab():
    col_header, col_button = st.columns([4, 1])
    with col_header:
        st.markdown('<div class="section-header">🗄️ Database Browser</div>', unsafe_allow_html=True)
    with col_button:
        st.write("")
        if st.button("🗑️ Empty Database", type="secondary", use_container_width=True):
            db = init_database()
            if db:
                try:
                    cursor = db.conn.cursor()
                    cursor.execute("DELETE FROM line_items")
                    cursor.execute("DELETE FROM invoices")
                    db.conn.commit()
                    st.success("✅ Database emptied successfully!")
                    st.session_state.invoices_df = load_invoices_data()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error emptying database: {e}")
    
    df = load_invoices_data()
    
    if df.empty:
        st.info("📊 No invoices in database yet. Upload some invoices to get started!")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Total Invoices</div>
            <div class="metric-value">{len(df)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Total Amount</div>
            <div class="metric-value">${df['total_amount'].sum():,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Unique Vendors</div>
            <div class="metric-value">{df['vendor_name'].nunique()}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        if 'invoice_date' in df.columns:
            min_date = df['invoice_date'].min()
            max_date = df['invoice_date'].max()
            date_range = f"{min_date.strftime('%b %Y')} - {max_date.strftime('%b %Y')}"
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Date Range</div>
                <div class="metric-value" style="font-size: 0.9rem;">{date_range}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('<div class="section-header">🔍 Filters</div>', unsafe_allow_html=True)
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        vendors = ['All'] + sorted(df['vendor_name'].unique().tolist())
        selected_vendor = st.selectbox("Vendor", vendors)
    
    with col2:
        if 'invoice_date' in df.columns:
            min_date = df['invoice_date'].min().date()
            max_date = df['invoice_date'].max().date()
            date_range = st.date_input(
                "Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
    
    with col3:
        methods = ['All'] + sorted(df['extraction_method'].unique().tolist())
        selected_method = st.selectbox("Extraction Method", methods)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    filtered_df = df.copy()
    
    if selected_vendor != 'All':
        filtered_df = filtered_df[filtered_df['vendor_name'] == selected_vendor]
    
    if 'invoice_date' in df.columns and len(date_range) == 2:
        filtered_df = filtered_df[
            (filtered_df['invoice_date'].dt.date >= date_range[0]) &
            (filtered_df['invoice_date'].dt.date <= date_range[1])
        ]
    
    if selected_method != 'All':
        filtered_df = filtered_df[filtered_df['extraction_method'] == selected_method]
    
    st.markdown(f'<div class="section-header">📋 Invoices ({len(filtered_df)} results)</div>', unsafe_allow_html=True)
    
    display_df = filtered_df[[
        'invoice_number', 'vendor_name', 'invoice_date', 
        'total_amount', 'extraction_method', 'source_pdf_name'
    ]].copy()
    
    display_df['total_amount'] = display_df['total_amount'].apply(lambda x: f"${x:,.2f}")
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown('<div class="section-header">📦 Line Items Details</div>', unsafe_allow_html=True)
    
    if len(filtered_df) > 0:
        invoice_options = []
        for idx, row in filtered_df.iterrows():
            invoice_num = row.get('invoice_number', 'N/A')
            vendor = row.get('vendor_name', 'N/A')
            date = row.get('invoice_date', 'N/A')
            if isinstance(date, pd.Timestamp):
                date_str = date.strftime('%Y-%m-%d')
            else:
                date_str = str(date)
            invoice_options.append(f"{invoice_num} - {vendor} ({date_str})")
        
        selected_invoice_idx = st.selectbox(
            "Select invoice to view line items:",
            range(len(invoice_options)),
            format_func=lambda x: invoice_options[x] if x < len(invoice_options) else ""
        )
        
        if selected_invoice_idx is not None:
            selected_invoice = filtered_df.iloc[selected_invoice_idx]
            
            db = init_database()
            if db:
                invoice_number = selected_invoice.get('invoice_number')
                all_invoices = db.get_all_invoices()
                
                for invoice in all_invoices:
                    if invoice.get('invoice_number') == invoice_number:
                        line_items = invoice.get('line_items', [])
                        
                        if line_items:
                            st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                            st.write(f"**Invoice #{invoice_number}** - {len(line_items)} line item(s)")
                            
                            line_items_df = pd.DataFrame(line_items)
                            
                            if 'quantity' in line_items_df.columns:
                                line_items_df['quantity'] = line_items_df['quantity'].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "N/A")
                            if 'unit_price' in line_items_df.columns:
                                line_items_df['unit_price'] = line_items_df['unit_price'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "N/A")
                            if 'line_total' in line_items_df.columns:
                                line_items_df['line_total'] = line_items_df['line_total'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "N/A")
                            
                            st.dataframe(line_items_df, use_container_width=True, hide_index=True)
                            st.markdown('</div>', unsafe_allow_html=True)
                        break
    
    st.markdown('<div class="section-header">📥 Export Data</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"invoices_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        json_str = filtered_df.to_json(orient='records', indent=2)
        st.download_button(
            label="📥 Download JSON",
            data=json_str,
            file_name=f"invoices_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )

