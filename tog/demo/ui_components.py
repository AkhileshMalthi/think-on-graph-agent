"""
UI Components and Styling
All UI rendering functions and CSS styling for the Streamlit application
"""

import streamlit as st
import pandas as pd
from data_processing import display_exploration_metrics


def setup_page():
    """Setup Streamlit page configuration with modern styling"""
    st.set_page_config(
        page_title="Knowledge Graph Explorer",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Dark theme styling for info display boxes
    st.markdown("""
        <style>
            .main .block-container {
                padding-top: 1rem;
                max-width: 1200px;
            }
            
            .main-header {
                text-align: center;
                padding: 2rem 0;
                margin-bottom: 2rem;
            }
            
            .main-title {
                font-size: 2.5rem;
                font-weight: bold;
                color: #1f77b4;
                margin-bottom: 0.5rem;
            }
            
            .main-subtitle {
                font-size: 1.1rem;
                color: #666;
                margin-bottom: 1rem;
            }
            
            .metric-container {
                background: #2d3748;
                border-radius: 10px;
                padding: 1rem;
                margin: 0.5rem 0;
                border-left: 4px solid #4299e1;
                color: #ffffff;
            }
            
            .metric-title {
                font-weight: 600;
                color: #63b3ed;
                margin-bottom: 0.25rem;
            }
            
            .metric-value {
                font-size: 1.5rem;
                font-weight: bold;
                color: #ffffff;
            }
            
            .metric-description {
                font-size: 0.9rem;
                color: #cbd5e0;
            }
            
            .status-success {
                background: #1a202c;
                border: 1px solid #38a169;
                color: #68d391;
                padding: 1rem;
                border-radius: 5px;
                margin: 1rem 0;
            }
            
            .status-error {
                background: #1a202c;
                border: 1px solid #e53e3e;
                color: #fc8181;
                padding: 1rem;
                border-radius: 5px;
                margin: 1rem 0;
            }
            
            .status-info {
                background: #1a202c;
                border: 1px solid #3182ce;
                color: #63b3ed;
                padding: 1rem;
                border-radius: 5px;
                margin: 1rem 0;
            }
        </style>
    """, unsafe_allow_html=True)


def render_header():
    """Render the main application header with title and subtitle"""
    st.markdown("""
        <div class="main-header">
            <div class="main-title">🧠 Knowledge Graph Explorer</div>
            <div class="main-subtitle">Explore knowledge graphs intelligently using AI-powered entity and relation discovery</div>
        </div>
    """, unsafe_allow_html=True)


def display_exploration_results(result):
    """
    Display exploration results in a clean, organized format
    
    Args:
        result (dict): Exploration results containing paths, answer, and metadata
    """
    if not result:
        st.info("No exploration results available.")
        return
    
    # Show metrics first
    display_exploration_metrics(result)
    
    # Answer section
    if result.get('answer'):
        st.subheader("📝 Generated Answer")
        st.write(result['answer'])
        st.divider()
    
    # Paths section
    paths = result.get('paths', []) or []
    if paths:
        st.subheader("🛤️ Knowledge Paths")
        
        for i, path in enumerate(paths, 1):
            # Import here to avoid circular imports
            from data_processing import get_confidence_score
            
            confidence = get_confidence_score(path)
            confidence_str = f"{confidence:.1%}" if confidence > 0 else "N/A"
            
            with st.expander(f"Path {i} - Confidence: {confidence_str}", expanded=i == 1):
                _display_path_triples(path)
    else:
        st.info("No knowledge paths found")


def _display_path_triples(path):
    """
    Display triples for a single path in a structured format
    
    Args:
        path: Path object containing triples/relations
    """
    # Get triples from path
    triples = []
    if hasattr(path, 'triples'):
        triples = path.triples
    elif hasattr(path, 'path'):
        triples = path.path
    elif isinstance(path, dict):
        triples = path.get('triples', path.get('path', []))
    
    if triples:
        for j, triple in enumerate(triples):
            if not triple:
                continue
            
            col1, col2, col3 = st.columns([2, 1, 2])
            
            with col1:
                # Subject
                subject_name, subject_type = _extract_entity_info(triple, 'subject')
                st.write(f"**{subject_name}**")
                st.caption(f"Type: {subject_type}")
            
            with col2:
                # Predicate
                relation = _extract_relation_info(triple)
                st.write(f"*{relation}*")
            
            with col3:
                # Object
                object_name, object_type = _extract_entity_info(triple, 'object')
                st.write(f"**{object_name}**")
                st.caption(f"Type: {object_type}")
            
            if j < len(triples) - 1:
                st.write("↓")
    else:
        st.info("No triples found in this path")


def _extract_entity_info(triple, entity_type):
    """Extract name and type from an entity in a triple"""
    name = "Unknown"
    type_info = "Unknown"
    
    if hasattr(triple, entity_type):
        entity = getattr(triple, entity_type)
        if hasattr(entity, 'name'):
            name = entity.name
        if hasattr(entity, 'type'):
            type_info = entity.type
    elif isinstance(triple, dict) and entity_type in triple:
        entity = triple[entity_type]
        if isinstance(entity, dict):
            name = entity.get('name', 'Unknown')
            type_info = entity.get('type', 'Unknown')
    
    return name, type_info


def _extract_relation_info(triple):
    """Extract relation information from a triple"""
    relation = "relates to"
    
    if hasattr(triple, 'predicate') and hasattr(triple.predicate, 'type'):
        relation = triple.predicate.type
    elif isinstance(triple, dict) and 'predicate' in triple:
        pred = triple['predicate']
        if isinstance(pred, dict):
            relation = pred.get('type', 'relates to')
    
    return relation


def display_logs_section():
    """Display exploration logs with filtering options"""
    st.subheader("📋 Exploration Logs")
    
    if st.session_state.log_handler.logs:
        # Log level filter
        log_levels = ["ALL"] + list(set(log['level'] for log in st.session_state.log_handler.logs))
        selected_level = st.selectbox("Filter by log level:", log_levels)
        
        # Filter logs based on selection
        filtered_logs = st.session_state.log_handler.logs
        if selected_level != "ALL":
            filtered_logs = [log for log in filtered_logs if log['level'] == selected_level]
        
        if filtered_logs:
            logs_df = pd.DataFrame(filtered_logs)
            st.dataframe(logs_df, use_container_width=True)
        else:
            st.info("No logs available for the selected level")
    else:
        st.info("No exploration logs available. Run an exploration to see detailed logs.")


def display_history_section():
    """Display exploration history with expandable results"""
    st.subheader("📚 Exploration History")
    
    if st.session_state.exploration_history:
        for i, exploration in enumerate(reversed(st.session_state.exploration_history)):
            with st.expander(f"{exploration['query']} - {exploration['timestamp']}", expanded=i == 0):
                if exploration['result'] and exploration['result'].get('success'):
                    st.write("**Answer:**")
                    st.write(exploration['result'].get('answer', 'No answer available'))
                    paths = exploration['result'].get('paths', [])
                    st.write(f"**Paths found:** {len(paths) if paths else 0}")
                else:
                    st.error("Exploration failed")
    else:
        st.info("No exploration history available")