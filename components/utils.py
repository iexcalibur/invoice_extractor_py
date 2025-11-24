import streamlit as st
import pandas as pd
import tempfile
import os
import json
import shutil
from pathlib import Path
from core.invoice_extractor import EnhancedInvoiceExtractor
from core.database import InvoiceDatabase
from core.config import Config


def init_session_state():
    if 'db' not in st.session_state:
        st.session_state.db = None
    if 'invoices_df' not in st.session_state:
        st.session_state.invoices_df = None
    if 'extraction_result' not in st.session_state:
        st.session_state.extraction_result = None
    if 'show_all_results' not in st.session_state:
        st.session_state.show_all_results = False
    if 'uploaded_file_names' not in st.session_state:
        st.session_state.uploaded_file_names = set()
    if 'file_uploader_key' not in st.session_state:
        st.session_state.file_uploader_key = 0


def init_database():
    try:
        if st.session_state.db is None:
            st.session_state.db = InvoiceDatabase("invoices.db")
        return st.session_state.db
    except Exception as e:
        st.error(f"Database initialization failed: {e}")
        return None


def load_invoices_data():
    db = init_database()
    if not db:
        return pd.DataFrame()
    
    try:
        invoices = db.get_all_invoices()
        if not invoices:
            return pd.DataFrame()
        
        df = pd.DataFrame(invoices)
        
        if 'invoice_date' in df.columns:
            df['invoice_date'] = pd.to_datetime(df['invoice_date'])
        
        if 'created_at' in df.columns:
            df['created_at'] = pd.to_datetime(df['created_at'])
        
        return df
    except Exception as e:
        st.error(f"Error loading invoices: {e}")
        return pd.DataFrame()


def extract_invoice(uploaded_file):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        with st.spinner("🔄 Extracting invoice data..."):
            extractor = EnhancedInvoiceExtractor(
                api_key=Config.ANTHROPIC_API_KEY if Config.ANTHROPIC_API_KEY else None,
                use_regex=True,
                use_layoutlmv3=True,
                use_ocr=True
            )
            
            result = extractor.extract_robust(tmp_path)
        
        result['pdf'] = tmp_path
        result['original_filename'] = uploaded_file.name
        result['file_content'] = uploaded_file.getvalue()
        
        if result.get('status') == 'success':
            os.unlink(tmp_path)
        else:
            pass
        
        db = init_database()
        if db:
            valid_pages = [
                page for page in result.get('pages', [])
                if page.get('extraction_method') and page.get('extraction_method') != 'none'
            ]
            
            if valid_pages:
                save_result = {
                    'status': 'success',
                    'pages': valid_pages,
                    'pdf': result.get('pdf', uploaded_file.name)
                }
                db_result = db.save_extraction_result(save_result, uploaded_file.name)
                if db_result.get('saved'):
                    st.session_state.invoices_df = load_invoices_data()
                    st.success(f"💾 Saved {db_result.get('saved_pages', 0)} invoice(s) to database")
                elif db_result.get('errors'):
                    st.warning(f"⚠️ Saved with warnings: {', '.join(db_result['errors'])}")
                    st.session_state.invoices_df = load_invoices_data()
        
        return result
    
    except Exception as e:
        st.error(f"Extraction failed: {e}")
        return None


def display_extraction_result(result):
    if not result:
        return
    
    status = result.get('status')
    
    if status == 'success':
        st.markdown("""
        <div class="status-box success">
            <div style="display: flex; align-items: center;">
                <span class="status-icon">✅</span>
                <div>
                    <div class="status-title">Extraction Successful!</div>
                    <div class="status-text">Invoice data has been extracted and validated successfully.</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        for page in result.get('pages', []):
            if page.get('validated'):
                st.markdown(f'<div class="section-header">📄 Page {page.get("page_number", "?")}</div>', unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div class="metric-container">
                        <div class="metric-label">Invoice Number</div>
                        <div class="metric-value">{page.get('invoice_number', 'N/A')}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="metric-container">
                        <div class="metric-label">Date</div>
                        <div class="metric-value" style="font-size: 1.3rem;">{page.get('date', 'N/A')}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="metric-container">
                        <div class="metric-label">Total Amount</div>
                        <div class="metric-value">${page.get('total_amount', 0):.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="metric-container">
                        <div class="metric-label">Line Items</div>
                        <div class="metric-value">{len(page.get('line_items', []))}</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown('<div class="custom-card">', unsafe_allow_html=True)
                st.write(f"**Vendor:** {page.get('vendor_name', 'N/A')}")
                st.write(f"**Extraction Method:** `{page.get('extraction_method', 'unknown')}`")
                
                if page.get('line_items'):
                    st.write("**Line Items:**")
                    line_items_df = pd.DataFrame(page['line_items'])
                    st.dataframe(line_items_df, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
    
    elif status == 'manual_review_needed':
        st.markdown("""
        <div class="status-box warning">
            <div style="display: flex; align-items: center;">
                <span class="status-icon">⚠️</span>
                <div>
                    <div class="status-title">Manual Review Needed</div>
                    <div class="status-text">Extraction completed but validation failed. Please review the document manually.</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        pdf_path = result.get('pdf', '')
        original_filename = result.get('original_filename', '')
        file_content = result.get('file_content')
        
        if pdf_path or file_content:
            st.markdown('<div class="section-header">📋 Manual Review Actions</div>', unsafe_allow_html=True)
            
            if original_filename:
                file_name = original_filename
            elif pdf_path:
                file_name = Path(pdf_path).name
            else:
                file_name = "unknown_file"
            
            st.write(f"**File:** {file_name}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if file_content:
                    st.download_button(
                        label="📥 Download PDF",
                        data=file_content,
                        file_name=file_name,
                        mime="application/pdf",
                        use_container_width=True
                    )
                elif pdf_path and os.path.exists(pdf_path):
                    with open(pdf_path, 'rb') as f:
                        st.download_button(
                            label="📥 Download PDF",
                            data=f.read(),
                            file_name=file_name,
                            mime="application/pdf",
                            use_container_width=True
                        )
            
            with col2:
                if st.button("📁 Move to Manual Review", use_container_width=True):
                    manual_review_folder = Path("Manual review")
                    manual_review_folder.mkdir(exist_ok=True)
                    
                    try:
                        dest_path = manual_review_folder / file_name
                        counter = 1
                        while dest_path.exists():
                            stem = Path(file_name).stem
                            suffix = Path(file_name).suffix
                            dest_path = manual_review_folder / f"{stem}_{counter}{suffix}"
                            counter += 1
                        
                        if file_content:
                            with open(dest_path, 'wb') as f:
                                f.write(file_content)
                        elif pdf_path and os.path.exists(pdf_path):
                            shutil.copy2(pdf_path, dest_path)
                        
                        st.success(f"✅ File moved to: {dest_path}")
                        
                        json_path = dest_path.with_suffix('.json')
                        result_for_json = {k: v for k, v in result.items() if k != 'file_content'}
                        with open(json_path, 'w') as f:
                            json.dump(result_for_json, f, indent=2)
                    except Exception as e:
                        st.error(f"❌ Error moving file: {e}")
    
    else:
        st.markdown(f"""
        <div class="status-box error">
            <div style="display: flex; align-items: center;">
                <span class="status-icon">❌</span>
                <div>
                    <div class="status-title">Extraction Error</div>
                    <div class="status-text">{result.get("error", "Unknown error occurred")}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def extract_from_data_folder():
    data_folder = Path("data")
    
    if not data_folder.exists():
        st.error("❌ Data folder not found!")
        return []
    
    supported_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.gif']
    all_files = []
    
    for ext in supported_extensions:
        all_files.extend(list(data_folder.glob(f"*{ext}")))
        all_files.extend(list(data_folder.glob(f"*{ext.upper()}")))
    
    all_files = list(set(all_files))
    
    if not all_files:
        st.warning("⚠️ No PDF or image files found in the data folder!")
        return []
    
    return all_files

