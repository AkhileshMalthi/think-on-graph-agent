import os
from typing import Dict, List, Any
from dotenv import load_dotenv
from . import KnowledgeGraph
from tog.utils.logger import setup_logger

class Neo4jKnowledgeGraph(KnowledgeGraph):
    """
    Knowledge graph implementation using Neo4j.
    """
    
    def __init__(self, uri: str = None, user: str = None, password: str = None, **kwargs):
        import neo4j
        load_dotenv()  # Load environment variables from .env file
        uri = uri or os.getenv("NEO4J_URI")
        user = user or os.getenv("NEO4J_USERNAME")
        password = password or os.getenv("NEO4J_PASSWORD")
        if not uri or not user or not password:
            raise ValueError("Neo4j connection parameters are required")
        self.driver = neo4j.GraphDatabase.driver(uri, auth=(user, password))
        self.session = None
        self.logger = setup_logger(name="neo4j_knowledge_graph", log_filename="neo4j_knowledge_graph.log")
        self.logger.info(f"Neo4jKnowledgeGraph initialized with uri: {uri}, user: {user}")
    
    def query(self, query_str: str, **kwargs) -> List[Dict[str, Any]]:
        try:
            with self.driver.session() as session:
                result = session.run(query_str, **kwargs)
                return [record.data() for record in result]
        except Exception as e:
            self.logger.error(f"Error executing query: {query_str}, Error: {e}")
            return []
    
    def size(self) -> int:
        try:
            with self.driver.session() as session:
                result = session.run("MATCH (n) RETURN count(n) AS count")
                return result.single()["count"]
        except Exception as e:
            self.logger.error(f"Error getting size of knowledge graph: {e}")
            return 0
        
    def close(self):
        if self.driver is not None:
            self.driver.close()

# if __name__ == "__main__":
#     # Example usage
#     from pprint import pprint
#     kg = Neo4jKnowledgeGraph()
#     query = """
#         MATCH (subject)-[predicate]->(object)
#         RETURN subject, type(predicate) as predicate_type, predicate, object
#         LIMIT $limit
#     """
#     limit = 1
#     results = kg.query(query, limit=limit)
#     for result in results:
#         print(("=" * 50)+"\n")
#         pprint(result)