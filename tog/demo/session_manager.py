"""
Session State Management
Handles Streamlit session state initialization and logging configuration
"""

import streamlit as st
import logging
from datetime import datetime


class StreamlitLogHandler(logging.Handler):
    """
    Custom log handler to capture logs for Streamlit display
    Stores logs in memory for real-time viewing in the UI
    """
    def __init__(self):
        super().__init__()
        self.logs = []
    
    def emit(self, record):
        """Capture log records and format them for display"""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).strftime('%H:%M:%S'),
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage()
        }
        self.logs.append(log_entry)


def initialize_session_state():
    """
    Initialize all session state variables for the application
    Ensures consistent state management across page reloads
    """
    if 'exploration_results' not in st.session_state:
        st.session_state.exploration_results = None
    
    if 'log_handler' not in st.session_state:
        st.session_state.log_handler = StreamlitLogHandler()
    
    if 'explorer' not in st.session_state:
        st.session_state.explorer = None
    
    if 'exploration_history' not in st.session_state:
        st.session_state.exploration_history = []
    
    if 'exploration_running' not in st.session_state:
        st.session_state.exploration_running = False


def setup_logging():
    """
    Setup logging configuration to capture exploration steps
    Connects our custom log handler to relevant loggers
    """
    # List of logger names we want to capture
    loggers = [
        'ExplorationLoop',
        'Neo4jEntityExplorer', 
        'Neo4jRelationExplorer',
        'EntityMapper',
        'KnowledgeGraphExplorer'
    ]
    
    # Configure each logger to use our custom handler
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.addHandler(st.session_state.log_handler)
        logger.setLevel(logging.INFO)