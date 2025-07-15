import json
import logging
from typing import Dict, Any
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Neo4jConnector:
    """
    Class to handle Neo4j database connections and operations
    """

    def __init__(self):
        """
        Initialize Neo4j connector using environment variables
        """
        load_dotenv()

        # Neo4j Connection Parameters
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")

        # Initialize connection
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            logger.info("Successfully connected to Neo4j database")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def close(self):
        """
        Close the Neo4j driver connection
        """
        if hasattr(self, "driver"):
            self.driver.close()
            logger.info("Neo4j connection closed")

    def clear_database(self):
        """
        Clear all nodes and relationships in the Neo4j database
        """
        with self.driver.session() as session:
            try:
                # Delete all relationships first
                result = session.run("MATCH ()-[r]-() DELETE r")
                count = result.consume().counters.relationships_deleted
                logger.info(f"All relationships deleted: {count}")

                # Then delete all nodes
                result = session.run("MATCH (n) DELETE n")
                count = result.consume().counters.nodes_deleted
                logger.info(f"All nodes deleted: {count}")

                # Drop all constraints - using a different approach
                constraints_query = "SHOW CONSTRAINTS"
                try:
                    constraints = list(session.run(constraints_query))
                    for constraint in constraints:
                        name = constraint.get("name", "")
                        if name:
                            session.run(f"DROP CONSTRAINT {name}")
                    logger.info(f"All constraints dropped: {len(constraints)}")
                except Exception as e:
                    logger.warning(f"Failed to drop constraints: {e}")

                # Drop all indexes - using a different approach
                indexes_query = "SHOW INDEXES"
                try:
                    indexes = list(session.run(indexes_query))
                    for index in indexes:
                        name = index.get("name", "")
                        if name:
                            session.run(f"DROP INDEX {name}")
                    logger.info(f"All indexes dropped: {len(indexes)}")
                except Exception as e:
                    logger.warning(f"Failed to drop indexes: {e}")

            except Exception as e:
                logger.error(f"Error while clearing database: {e}")
                raise

    def _create_entity(self, tx, entity: Dict[str, Any]):
        """
        Create an entity node in Neo4j
        """
        # Convert metadata to a string for Neo4j compatibility
        metadata_str = json.dumps(entity.get("metadata", {}))

        query = """
        CREATE (e:Entity {
            id: $id,
            name: $name,
            type: $type,
            metadata: $metadata
        })
        RETURN e
        """

        result = tx.run(
            query,
            id=entity.get("id"),
            name=entity.get("name"),
            type=entity.get("type"),
            metadata=metadata_str,
        )
        return result.single()

    def _create_relationship(self, tx, relationship: Dict[str, Any]):
        """
        Create a relationship between entities in Neo4j
        Updated to handle relationship type as a string
        """
        # Get relationship type (now as a string)
        rel_type = relationship.get("type", "RELATED_TO")

        # Ensure the relationship type is valid for Neo4j
        rel_type = self._sanitize_relationship_type(rel_type)

        # Convert metadata to a string for Neo4j compatibility
        metadata_str = json.dumps(relationship.get("metadata", {}))

        query = f"""
        MATCH (source:Entity {{id: $source_id}})
        MATCH (target:Entity {{id: $target_id}})
        CREATE (source)-[r:{rel_type} {{
            id: $id,
            metadata: $metadata
        }}]->(target)
        RETURN r
        """

        result = tx.run(
            query,
            id=relationship.get("id"),
            source_id=relationship.get("source_id"),
            target_id=relationship.get("target_id"),
            metadata=metadata_str,
        )
        return result.single()

    def _sanitize_relationship_type(self, rel_type: str) -> str:
        """
        Sanitize relationship type to be valid in Neo4j

        Neo4j relationship types:
        - Must begin with a letter
        - Can contain numbers, letters, and underscores
        - Are case-sensitive
        """
        # Replace spaces and special characters with underscores
        sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", rel_type)

        # Ensure it starts with a letter
        if not sanitized or not sanitized[0].isalpha():
            sanitized = "R_" + sanitized

        # Default if empty
        if not sanitized:
            sanitized = "RELATED_TO"

        return sanitized

    def save_knowledge_graph(self, knowledge_graph: Dict[str, Any], clear_first=True):
        """
        Save entire knowledge graph to Neo4j

        Args:
            knowledge_graph (Dict): The knowledge graph to save
            clear_first (bool): Whether to clear the database first
        """
        # Clear database if requested
        if clear_first:
            self.clear_database()

        # Create constraints and indexes
        self._create_constraints()

        # Create entities
        with self.driver.session() as session:
            entity_count = 0
            for entity in knowledge_graph.get("entities", []):
                try:
                    session.execute_write(self._create_entity, entity)
                    entity_count += 1
                except Exception as e:
                    logger.error(f"Failed to create entity {entity.get('name')}: {e}")
            logger.info(f"Created {entity_count} entities")

        # Create relationships
        with self.driver.session() as session:
            relationship_count = 0
            for relationship in knowledge_graph.get("relationships", []):
                try:
                    session.execute_write(self._create_relationship, relationship)
                    relationship_count += 1
                except Exception as e:
                    logger.error(f"Failed to create relationship {relationship.get('id')}: {e}")
            logger.info(f"Created {relationship_count} relationships")

    def _create_constraints(self):
        """
        Create necessary constraints and indexes in Neo4j
        """
        with self.driver.session() as session:
            # Create constraint on Entity id
            try:
                # For Neo4j 4.x
                try:
                    session.run("CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE")
                    logger.info("Created constraint on Entity.id")
                except Exception:
                    # For Neo4j 3.x
                    session.run("CREATE CONSTRAINT ON (e:Entity) ASSERT e.id IS UNIQUE")
                    logger.info("Created constraint on Entity.id (Neo4j 3.x syntax)")
            except Exception as e:
                logger.error(f"Failed to create constraint on Entity.id: {e}")
