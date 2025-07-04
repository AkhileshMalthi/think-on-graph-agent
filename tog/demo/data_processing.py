"""
Data Processing Utilities
Functions for processing and analyzing exploration results data
"""

import streamlit as st


def get_confidence_score(path):
    """
    Extract confidence score from path object.
    Handles different possible formats and structures.
    
    Args:
        path: Path object or dictionary containing confidence information
        
    Returns:
        float: Confidence score between 0 and 1
    """
    confidence = 0.0
    
    try:
        # Method 1: Direct attribute access for Path objects
        if hasattr(path, 'confidence_score'):
            confidence = float(path.confidence_score)
        elif hasattr(path, 'confidence'):
            confidence = float(path.confidence)
        
        # Method 2: Dictionary access
        elif isinstance(path, dict):
            confidence = float(path.get('confidence_score', path.get('confidence', 0.0)))
        
        # Method 3: Check if it's nested in metadata
        elif hasattr(path, 'metadata') and isinstance(path.metadata, dict):
            confidence = float(path.metadata.get('confidence_score', path.metadata.get('confidence', 0.0)))
        
        # Method 4: Check for score attribute
        elif hasattr(path, 'score'):
            confidence = float(path.score)
        
        # Ensure confidence is between 0 and 1
        if confidence > 1.0:
            confidence = confidence / 100.0  # Convert percentage to decimal
            
    except (ValueError, TypeError, AttributeError) as e:
        st.warning(f"Could not extract confidence score: {e}")
        confidence = 0.0
    
    return confidence


def extract_entities_from_paths(paths):
    """
    Extract unique entities from a list of paths
    
    Args:
        paths (list): List of path objects
        
    Returns:
        list: List of unique entity names
    """
    entities = set()
    
    if not paths:
        return []
    
    for path in paths:
        try:
            # Get triples from path
            triples = []
            if hasattr(path, 'triples'):
                triples = path.triples
            elif hasattr(path, 'path'):
                triples = path.path
            elif isinstance(path, dict):
                triples = path.get('triples', path.get('path', []))
            
            # Extract entities from triples
            for triple in triples:
                if hasattr(triple, 'subject') and hasattr(triple.subject, 'name'):
                    entities.add(triple.subject.name)
                if hasattr(triple, 'object') and hasattr(triple.object, 'name'):
                    entities.add(triple.object.name)
                    
                # Handle dictionary format
                if isinstance(triple, dict):
                    subject = triple.get('subject', {})
                    obj = triple.get('object', {})
                    if isinstance(subject, dict) and 'name' in subject:
                        entities.add(subject['name'])
                    if isinstance(obj, dict) and 'name' in obj:
                        entities.add(obj['name'])
                        
        except Exception as e:
            st.warning(f"Error extracting entities from path: {e}")
            continue
    
    return list(entities)


def calculate_average_confidence(paths):
    """
    Calculate average confidence score from a list of paths
    
    Args:
        paths (list): List of path objects
        
    Returns:
        float: Average confidence score
    """
    if not paths:
        return 0.0
    
    total_confidence = 0.0
    valid_paths = 0
    
    for path in paths:
        confidence = get_confidence_score(path)
        if confidence > 0:
            total_confidence += confidence
            valid_paths += 1
    
    return total_confidence / valid_paths if valid_paths > 0 else 0.0


def display_exploration_metrics(result):
    """
    Display exploration metrics in a clean layout using custom styling
    
    Args:
        result (dict): Exploration results containing success status, paths, etc.
    """
    if not result:
        return
        
    col1, col2, col3, col4 = st.columns(4)
    
    # Success Rate
    with col1:
        success = result.get('success', False)
        success_icon = '✅' if success else '❌'
        success_text = 'Success' if success else 'Failed'
        
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">🎯 Status</div>
                <div class="metric-value">{success_icon} {success_text}</div>
                <div class="metric-description">Exploration Status</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Paths Found
    with col2:
        paths = result.get('paths', []) or []
        paths_count = len(paths)
        
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">🛤️ Paths</div>
                <div class="metric-value">{paths_count}</div>
                <div class="metric-description">Knowledge Paths Found</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Entities Found
    with col3:
        entities = extract_entities_from_paths(paths)
        entities_count = len(entities)
        
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">🏷️ Entities</div>
                <div class="metric-value">{entities_count}</div>
                <div class="metric-description">Unique Entities</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Average Confidence
    with col4:
        avg_confidence = calculate_average_confidence(paths)
        confidence_pct = f"{avg_confidence:.1%}"
        
        st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">📊 Confidence</div>
                <div class="metric-value">{confidence_pct}</div>
                <div class="metric-description">Average Score</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Debug information (optional, can be removed in production)
    if st.checkbox("Show Debug Info", value=False):
        st.write("**Debug - Confidence Scores:**")
        for i, path in enumerate(paths):
            conf = get_confidence_score(path)
            st.write(f"Path {i+1}: {conf:.3f}")