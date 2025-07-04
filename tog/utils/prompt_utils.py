import re
import json
import logging
from typing import Dict, List, Tuple
from tog.models.entity import Entity
from tog.models.relation import Relation

logger = logging.getLogger(__name__)

def format_relations_for_prompt(relations: List[Relation]) -> str:
    """Format relations for LLM prompt."""
    relations_text = ""
    for i, relation in enumerate(relations, 1):
        is_incoming = relation.metadata.get("is_incoming", False)
        source = relation.metadata.get('source_name', 'Unknown')
        target = relation.metadata.get('target_name', 'Unknown')
        direction = f"{source} → {target}"
        relations_text += f"{i}. Relation: {relation.type}, Direction: {direction}\n"
    return relations_text

def create_relations_prompt(query: str, relations_text: str, n: int, entity_name: str = "Unknown Entity") -> str:
    """Create prompt for relation scoring."""
    return f"""
    Please retrieve {n} relations that contribute to the question and rate their contribution on a scale from 0 to 1 (the sum of the scores of {n} relations is 1). Return the result in valid JSON format.
    
    Q: {query}
    Topic Entity: {entity_name}
    Relations: 
    {relations_text}
    """

def format_entity_relation_tuples(tuples: List[Tuple[Entity, Relation, Entity]]) -> str:
    """Format entity-relation tuples for prompt."""
    tuples_text = ""
    for i, (source, relation, target) in enumerate(tuples, 1):
        source_desc = f"{source.name} ({source.type})"
        relation_desc = relation.type
        target_desc = f"{target.name} ({target.type})"
        
        # Add descriptions if available
        if source.metadata and "description" in source.metadata:
            source_desc += f": {source.metadata['description']}"
        if relation.metadata and "description" in relation.metadata:
            relation_desc += f": {relation.metadata['description']}"
        if target.metadata and "description" in target.metadata:
            target_desc += f": {target.metadata['description']}"
        
        tuples_text += f"{i}. {source_desc} -[{relation_desc}]-> {target_desc}\n"
    return tuples_text

def create_entity_ranking_prompt(query: str, tuples_text: str) -> str:
    """Create prompt for entity ranking."""
    return f"""
    Please analyze the following knowledge graph triples and rank them based on their relevance to the query.
    
    QUERY: {query}
    
    KNOWLEDGE GRAPH TRIPLES:
    {tuples_text}
    
    For each triple, assign a relevance score between 0.0 and 1.0, where 1.0 is highly relevant and 0.0 is not relevant at all.
    Consider how useful each triple would be in answering the query.
    
    Return your response as a JSON object where the keys are the indexes of the triples and the values are their relevance scores.
    Example format:
    {{
        "1": 0.9,
        "2": 0.7,
        "3": 0.3
    }}
    
    Return only the JSON object, no additional explanations.
    """

def parse_llm_scores(response: str) -> Dict:
    """Parse scores from LLM response."""
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response as JSON: {response}")
            return {}
    else:
        logger.error(f"No JSON found in LLM response: {response}")
        return {}
