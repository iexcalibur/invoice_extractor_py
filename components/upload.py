import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
from components.utils import (
    extract_invoice,
    extract_from_data_folder,
    display_extraction_result,
    init_database,
    load_invoices_data
)
from core.invoice_extractor import EnhancedInvoiceExtractor
from core.config import Config


def show_upload_tab():
    st.markdown('<div class="section-header">📤 Upload & Extract Invoices</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="custom-card">', unsafe_allow_html=True)
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📁 Extract from Data Folder")
        st.write("Batch process all PDFs and images from the `data/` folder")
    
    with col2:
        st.write("")
        st.write("")
        extract_clicked = st.button("🚀 Extract All", type="primary", use_container_width=True, key="extract_all_data")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if extract_clicked:
        files = extract_from_data_folder()
        
        if files:
            if 'stop_extraction' not in st.session_state:
                st.session_state.stop_extraction = False
            
            st.session_state.stop_extraction = False
            
            st.markdown(f"""
            <div class="extraction-progress-header">
                <div class="progress-info">
                    <span class="progress-icon">📄</span>
                    <span class="progress-title">Found {len(files)} file(s) in data folder</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            if st.button("⏹️ Stop Extraction", type="secondary", use_container_width=True, key="stop_extraction_btn"):
                st.session_state.stop_extraction = True
            
            results = []
            success_count = 0
            error_count = 0
            stopped = False
            
            for i, file_path in enumerate(files):
                if st.session_state.get('stop_extraction', False):
                    stopped = True
                    status_text.markdown(f"""
                    <div class="status-message warning">
                        ⚠️ Extraction stopped by user at {i}/{len(files)} files
                    </div>
                    """, unsafe_allow_html=True)
                    break
                
                current_progress = (i / len(files))
                progress_bar.progress(current_progress)
                
                status_text.markdown(f"""
                <div class="status-message processing">
                    <span class="status-spinner">🔄</span>
                    Processing {i+1}/{len(files)}: {file_path.name}
                </div>
                """, unsafe_allow_html=True)
                
                try:
                    extractor = EnhancedInvoiceExtractor(
                        api_key=Config.ANTHROPIC_API_KEY if Config.ANTHROPIC_API_KEY else None,
                        use_regex=True,
                        use_layoutlmv3=True,
                        use_ocr=True
                    )
                    
                    result = extractor.extract_robust(str(file_path))
                    
                    if result:
                        results.append(result)
                        
                        valid_pages = [
                            page for page in result.get('pages', [])
                            if page.get('extraction_method') and page.get('extraction_method') != 'none'
                        ]
                        
                        if valid_pages:
                            db = init_database()
                            if db:
                                save_result = {
                                    'status': 'success',
                                    'pages': valid_pages,
                                    'pdf': str(file_path)
                                }
                                db_result = db.save_extraction_result(save_result, file_path.name)
                                if db_result.get('saved'):
                                    success_count += db_result.get('saved_pages', 0)
                                else:
                                    error_count += 1
                
                except Exception as e:
                    error_count += 1
                    st.warning(f"Error processing {file_path.name}: {e}")
            
            if not stopped:
                progress_bar.progress(1.0)
                status_text.markdown(f"""
                <div class="status-message success">
                    ✅ Processing complete! {success_count} invoice(s) saved, {error_count} error(s)
                </div>
                """, unsafe_allow_html=True)
            
            st.session_state.invoices_df = load_invoices_data()
            
            if results:
                st.session_state.extraction_result = results[-1]
                if not stopped:
                    st.success(f"📊 Processed {len(results)} file(s). {success_count} invoice(s) saved to database.")
    
    st.markdown('<div class="section-header" style="margin-top: 2rem;">📤 Upload Files</div>', unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "hidden_uploader",
        type=['pdf', 'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'tif'],
        accept_multiple_files=True,
        key=f"file_uploader_{st.session_state.file_uploader_key}",
        label_visibility="collapsed"
    )
    
    st.markdown("""
    <div class="upload-area-wrapper">
        <div class="upload-area" id="custom-upload-area">
            <svg class="upload-cloud-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M12 12v9m0 0l3-3m-3 3l-3-3" />
            </svg>
            <div class="upload-text">Drop your files here</div>
            <div class="upload-subtext">or click to browse</div>
            <div class="upload-hint">Supported: PDF, PNG, JPG, JPEG, TIFF, BMP</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # JavaScript to make upload area clickable and handle file selection
    components.html("""
    <script>
    (function() {
        // Function to find and click the file input
        function triggerFileInput() {
            // Find the Streamlit file uploader in parent document
            const fileUploader = window.parent.document.querySelector('input[type="file"]');
            if (fileUploader) {
                fileUploader.click();
            }
        }
        
        // Wait a bit for the page to load
        setTimeout(function() {
            const uploadArea = window.parent.document.getElementById('custom-upload-area');
            
            if (uploadArea) {
                // Set cursor style
                uploadArea.style.cursor = 'pointer';
                
                // Add click event listener
                uploadArea.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    triggerFileInput();
                });
                
                // Add drag and drop visual feedback
                uploadArea.addEventListener('dragenter', function(e) {
                    e.preventDefault();
                    uploadArea.style.borderColor = '#10b981';
                    uploadArea.style.background = 'linear-gradient(135deg, #f0fdfa 0%, #d1fae5 100%)';
                });
                
                uploadArea.addEventListener('dragleave', function(e) {
                    e.preventDefault();
                    uploadArea.style.borderColor = '#06b6d4';
                    uploadArea.style.background = 'white';
                });
                
                uploadArea.addEventListener('dragover', function(e) {
                    e.preventDefault();
                });
                
                uploadArea.addEventListener('drop', function(e) {
                    uploadArea.style.borderColor = '#06b6d4';
                    uploadArea.style.background = 'white';
                });
            }
        }, 500);
    })();
    </script>
    """, height=0)
    
    if uploaded_files:
        unique_files = []
        seen_names = set()
        
        for file in uploaded_files:
            if file.name not in seen_names:
                unique_files.append(file)
                seen_names.add(file.name)
        
        uploaded_files = unique_files
        
        st.markdown(f"""
        <div class="files-header">
            <div class="files-count-badge">
                <span class="clipboard-icon">📋</span>
                <span class="files-count-text">{len(uploaded_files)} file(s) selected</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="files-container">', unsafe_allow_html=True)
        
        for idx, file in enumerate(uploaded_files):
            file_size_kb = len(file.getvalue()) / 1024
            file_ext = Path(file.name).suffix.lower()
            
            if file_ext == '.pdf':
                icon_emoji = '📄'
                icon_color = '#f59e0b'  # Orange
            elif file_ext in ['.zip']:
                icon_emoji = '🗜️'
                icon_color = '#8b5cf6'  # Purple
            else:
                icon_emoji = '🖼️'
                icon_color = '#06b6d4'
            
            if 'processing_files' in st.session_state and file.name in st.session_state.processing_files:
                status_icon = '🔄'
                status_color = '#06b6d4'
                progress = st.session_state.processing_files[file.name]
            elif 'completed_files' in st.session_state and file.name in st.session_state.completed_files:
                status_icon = '✅'
                status_color = '#10b981'
                progress = 100
            else:
                status_icon = '⭕'
                status_color = '#94a3b8'
                progress = 0
            
            st.markdown(f"""
            <div class="dark-file-item">
                <div style="display: flex; align-items: center; flex: 1;">
                    <div class="dark-file-icon" style="background: linear-gradient(135deg, {icon_color} 0%, {icon_color}cc 100%);">
                        {icon_emoji}
                    </div>
                    <div style="flex: 1;">
                        <div class="dark-file-name" title="{file.name}">{file.name}</div>
                        <div class="dark-file-size">{file_size_kb:.1f} KB</div>
                        <div class="dark-progress-bar">
                            <div class="dark-progress-fill" style="width: {progress}%; background: {status_color};"></div>
                        </div>
                    </div>
                </div>
                <div class="dark-status-icon" style="color: {status_color};">
                    {status_icon}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div style="margin-top: 1.5rem;">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            extract_files_clicked = st.button("🚀 Extract All Files", type="primary", use_container_width=True, key="extract_uploaded_files")
        
        with col2:
            if st.button("🗑️ Clear All", use_container_width=True):
                st.session_state.file_uploader_key += 1
                if 'processing_files' in st.session_state:
                    del st.session_state.processing_files
                if 'completed_files' in st.session_state:
                    del st.session_state.completed_files
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if extract_files_clicked:
            if 'stop_upload_extraction' not in st.session_state:
                st.session_state.stop_upload_extraction = False
            
            st.session_state.stop_upload_extraction = False
            
            st.markdown(f"""
            <div class="extraction-progress-header">
                <div class="progress-info">
                    <span class="progress-icon">🚀</span>
                    <span class="progress-title">Extracting {len(uploaded_files)} file(s)</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            progress_bar = st.progress(0)
            
            status_text = st.empty()
            
            if st.button("⏹️ Stop Extraction", type="secondary", use_container_width=True, key="stop_upload_extraction_btn"):
                st.session_state.stop_upload_extraction = True
            
            results = []
            st.session_state.processing_files = {}
            st.session_state.completed_files = set()
            stopped = False
            
            for i, uploaded_file in enumerate(uploaded_files):
                if st.session_state.get('stop_upload_extraction', False):
                    stopped = True
                    status_text.markdown(f"""
                    <div class="status-message warning">
                        ⚠️ Extraction stopped by user at {i}/{len(uploaded_files)} files
                    </div>
                    """, unsafe_allow_html=True)
                    break
                
                st.session_state.processing_files[uploaded_file.name] = 50
                
                current_progress = (i / len(uploaded_files))
                progress_bar.progress(current_progress)
                
                status_text.markdown(f"""
                <div class="status-message processing">
                    <span class="status-spinner">🔄</span>
                    Processing {i+1}/{len(uploaded_files)}: {uploaded_file.name}
                </div>
                """, unsafe_allow_html=True)
                
                result = extract_invoice(uploaded_file)
                if result:
                    results.append(result)
                st.session_state.processing_files[uploaded_file.name] = 100
                st.session_state.completed_files.add(uploaded_file.name)
            
            if not stopped:
                progress_bar.progress(1.0)
                status_text.markdown(f"""
                <div class="status-message success">
                    ✅ Processed {len(results)} file(s) successfully!
                </div>
                """, unsafe_allow_html=True)
            
            if results and not stopped:
                st.session_state.extraction_result = results[-1]
                st.rerun()
    
    if st.session_state.extraction_result:
        st.markdown('<div style="margin-top: 2rem;">', unsafe_allow_html=True)
        display_extraction_result(st.session_state.extraction_result)
        st.markdown('</div>', unsafe_allow_html=True)