"""
Configuration Management
Handles all configuration settings and sidebar parameter controls
"""

import streamlit as st


def create_sidebar_config():
    """
    Create sidebar configuration panel with all exploration parameters
    
    Returns:
        dict: Configuration dictionary with all parameters
    """
    st.sidebar.header("⚙️ Configuration")
    
    # Exploration Parameters Section
    st.sidebar.subheader("🔍 Exploration Parameters")
    max_iterations = st.sidebar.slider("Max Iterations", 1, 5, 3)
    max_paths = st.sidebar.slider("Max Paths", 3, 10, 5)
    max_entities_per_round = st.sidebar.slider("Max Entities per Round", 2, 8, 5)
    max_relations = st.sidebar.slider("Max Relations", 2, 6, 3)
    
    # LLM Parameters Section
    st.sidebar.subheader("🤖 LLM Parameters")
    temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.3, 0.1)
    model_name = st.sidebar.selectbox("Model", ["gpt-4o", "gpt-3.5-turbo", "llama-2-70b"])
    
    # Return configuration dictionary
    return {
        'max_iterations': max_iterations,
        'max_paths': max_paths,
        'max_entities_per_round': max_entities_per_round,
        'max_relations': max_relations,
        'temperature': temperature,
        'model_name': model_name
    }