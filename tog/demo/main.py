"""
Main Streamlit Application
Entry point for the Knowledge Graph Explorer web application
"""

import streamlit as st
import time
from datetime import datetime

from tog.config import create_sidebar_config
from ui_components import render_header, setup_page, display_exploration_results, display_logs_section, display_history_section
from session_manager import initialize_session_state, setup_logging
from explorer_engine import initialize_explorer, run_exploration_with_progress


def main():
    """Main Streamlit application entry point"""
    # Initialize the application
    setup_page()
    initialize_session_state()
    setup_logging()
    
    # Render main header
    render_header()
    
    # Sidebar configuration
    config = create_sidebar_config()
    
    # Main query section
    st.subheader("🤔 Ask Your Question")
    
    query = st.text_area(
        "Enter your question:",
        placeholder="e.g., What are the effects of CBD on anxiety?",
        height=120,
        help="Enter a natural language question about your knowledge graph"
    )
    
    # Button columns for actions
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        explore_button = st.button(
            "🚀 Start Exploration", 
            type="primary", 
            disabled=st.session_state.exploration_running
        )
    
    with col2:
        if st.button("🗑️ Clear Results"):
            st.session_state.exploration_results = None
            st.session_state.log_handler.logs = []
            st.rerun()
    
    with col3:
        if st.button("🔄 Reset"):
            st.session_state.explorer = None
            st.session_state.exploration_results = None
            st.session_state.log_handler.logs = []
            st.session_state.exploration_history = []
            st.rerun()
    
    # Handle exploration button click
    if explore_button and query.strip():
        result = run_exploration_with_progress(query, config)
    elif explore_button and not query.strip():
        st.warning("⚠️ Please enter a query to explore")
    
    # Display results in tabs if any data exists
    if (st.session_state.exploration_results or 
        st.session_state.log_handler.logs or 
        st.session_state.exploration_history):
        
        st.divider()
        
        tab1, tab2, tab3 = st.tabs(["📊 Results", "📋 Logs", "📚 History"])
        
        with tab1:
            if st.session_state.exploration_results:
                display_exploration_results(st.session_state.exploration_results)
            else:
                st.info("No exploration results available. Enter a query and click 'Start Exploration' to begin.")
        
        with tab2:
            display_logs_section()
        
        with tab3:
            display_history_section()


if __name__ == "__main__":
    main()