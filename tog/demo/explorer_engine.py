"""
Knowledge Graph Explorer Engine
Core logic for initializing and running knowledge graph explorations
"""

import streamlit as st
import time
from datetime import datetime

# Import your existing classes (assuming they're available)
from tog.pipeline.entity_extractor import AzureOpenAIEntityExtractor
from tog.pipeline.entity_mapper import EntityMapper
from tog.pipeline.mapping_handler import Neo4jMappingHandler
from tog.tog import ToG


def initialize_explorer(config):
    """
    Initialize the knowledge graph explorer with given configuration
    
    Args:
        config (dict): Configuration dictionary containing model settings
        
    Returns:
        KnowledgeGraphExplorer or None: Initialized explorer or None if failed
    """
    try:
        with st.spinner("🔄 Initializing Knowledge Graph Explorer..."):
            # Import specific implementations
            from tog.llms.azure_openai_llm import AzureOpenAILLM
            from tog.kgs.neo4j_kg import Neo4jKnowledgeGraph
            
            # Initialize core components
            llm = AzureOpenAILLM(model_name=config['model_name'])
            kg = Neo4jKnowledgeGraph()
            entity_extractor = AzureOpenAIEntityExtractor(model_name=config['model_name'])
            mapping_handler = Neo4jMappingHandler(kg=kg)
            entity_mapper = EntityMapper(kg=kg, mapping_handler=mapping_handler)
            
            # Create the main explorer
            explorer = ToG(
                llm=llm,
                kg=kg,
                entity_extractor=entity_extractor,
                entity_mapper=entity_mapper
            )
            
            return explorer
            
    except Exception as e:
        st.error(f"❌ Failed to initialize explorer: {str(e)}")
        return None


def run_exploration_with_progress(query, config):
    """
    Run exploration with visual progress tracking and status updates
    
    Args:
        query (str): User's natural language query
        config (dict): Configuration parameters for exploration
        
    Returns:
        dict or None: Exploration results or None if failed
    """
    # Clear previous logs and set running state
    st.session_state.log_handler.logs = []
    st.session_state.exploration_running = True
    
    # Initialize explorer if needed
    if st.session_state.explorer is None:
        st.session_state.explorer = initialize_explorer(config)
    
    if st.session_state.explorer is None:
        st.session_state.exploration_running = False
        return None
    
    try:
        # Create progress tracking elements
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Step 1: Start exploration
        status_text.text("🔍 Starting exploration...")
        progress_bar.progress(20)
        time.sleep(0.5)
        
        # Step 2: Entity mapping
        status_text.text("🗺️ Mapping entities...")
        progress_bar.progress(40)
        time.sleep(0.5)
        
        # Step 3: Relation exploration
        status_text.text("🔗 Exploring relations...")
        progress_bar.progress(60)
        time.sleep(0.5)
        
        # Step 4: Path analysis
        status_text.text("🧠 Analyzing paths...")
        progress_bar.progress(80)
        
        # Run the actual exploration
        result = st.session_state.explorer.explore_and_answer(
            query=query,
            max_iterations=config['max_iterations'],
            max_paths=config['max_paths']
        )
        
        # Complete progress
        progress_bar.progress(100)
        status_text.text("✅ Exploration completed!")
        time.sleep(1)
        
        # Clean up progress indicators
        progress_bar.empty()
        status_text.empty()
        
        # Store results in session state
        st.session_state.exploration_results = result
        st.session_state.exploration_history.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'query': query,
            'result': result
        })
        
        st.session_state.exploration_running = False
        return result
        
    except Exception as e:
        st.error(f"❌ Error during exploration: {str(e)}")
        st.session_state.exploration_running = False
        return None