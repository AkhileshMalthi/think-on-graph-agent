import neo4j
from .BaseKG import BaseKG

class Neo4jKG(BaseKG):
    def __init__(self, graph_endpoint, username, password):
        """
        Initialize Neo4j Knowledge Graph with connection details
        
        :param graph_endpoint: Neo4j database URI
        :param username: Neo4j database username
        :param password: Neo4j database password
        """
        super().__init__(graph_endpoint)
        self.driver = neo4j.GraphDatabase.driver(
            graph_endpoint, 
            auth=(username, password)
        )

    def _extract_initial_triples(self, entities):
        """
        Internal method to retrieve initial triples for given entities
        
        :param entities: List of initial entities
        :return: List of initial triples for Think on Graph
        """
        initial_paths = []
        with self.driver.session() as session:
            for entity in entities:
                # Query to retrieve initial triples connected to the entity
                query = (
                    "MATCH (e {name: $entity})-[r]->(related_entity) "
                    "RETURN e.name as entity, type(r) as relation, related_entity.name as related_entity "
                    "LIMIT 5"
                )
                result = session.run(query, entity=entity)
                
                for record in result:
                    initial_paths.append([{
                        'entity': record['entity'],
                        'relation': record['relation'],
                        'related_entity': record['related_entity']
                    }])
        
        return initial_paths

    def _retrieve_relations_for_path(self, entity):
        """
        Internal method to retrieve relations for Think on Graph path expansion
        
        :param entity: Entity to find relations for
        :return: List of relations
        """
        relations = []
        with self.driver.session() as session:
            query = (
                "MATCH (e {name: $entity})-[r]->(related_entity) "
                "RETURN type(r) as relation, related_entity.name as entity"
            )
            result = session.run(query, entity=entity)
            
            for record in result:
                relations.append({
                    'relation': record['relation'],
                    'entity': record['entity']
                })
        
        return relations

    # Public methods for general knowledge graph operations
    def get_entity_details(self, entity_name):
        """
        Retrieve detailed information about an entity
        
        :param entity_name: Name of the entity
        :return: Entity details
        """
        with self.driver.session() as session:
            query = "MATCH (e {name: $entity_name}) RETURN e"
            result = session.run(query, entity_name=entity_name)
            return result.single()[0] if result.single() else None

    def search_entities(self, search_term):
        """
        Search for entities matching a search term
        
        :param search_term: Term to search for
        :return: List of matching entities
        """
        with self.driver.session() as session:
            query = "MATCH (e) WHERE e.name CONTAINS $search_term RETURN e.name"
            result = session.run(query, search_term=search_term)
            return [record['e.name'] for record in result]

    # Implementing abstract methods from BaseKG
    def retrieve_initial_triples(self, entities):
        """Public wrapper for initial triples retrieval"""
        return self._extract_initial_triples(entities)

    def retrieve_relations(self, entity):
        """Public wrapper for relations retrieval"""
        return self._retrieve_relations_for_path(entity)

    def create_entity(self, entity_data):
        """
        Create a new entity in the Knowledge Graph
        
        :param entity_data: Dictionary containing entity properties
        :return: Created entity details
        """
        with self.driver.session() as session:
            query = "CREATE (e:Entity $props) RETURN e"
            result = session.run(query, props=entity_data)
            return result.single()[0]

    def update_entity(self, entity_id, updated_data):
        """
        Update an existing entity in the Knowledge Graph
        
        :param entity_id: ID of the entity to update
        :param updated_data: Dictionary of updated properties
        :return: Updated entity details
        """
        with self.driver.session() as session:
            query = (
                "MATCH (e) WHERE ID(e) = $entity_id "
                "SET e += $updated_data "
                "RETURN e"
            )
            result = session.run(query, entity_id=entity_id, updated_data=updated_data)
            return result.single()[0]

    def delete_entity(self, entity_id):
        """
        Delete an entity from the Knowledge Graph
        
        :param entity_id: ID of the entity to delete
        """
        with self.driver.session() as session:
            query = "MATCH (e) WHERE ID(e) = $entity_id DELETE e"
            session.run(query, entity_id=entity_id)

    def correct_triples(self, triples):
        """
        Correct erroneous triples in the Knowledge Graph
        
        :param triples: List of triples to correct
        :return: Corrected triples
        """
        corrected_triples = []
        with self.driver.session() as session:
            for triple in triples:
                query = (
                    "MATCH (e {name: $from_entity})-[r]->(to_entity {name: $to_entity}) "
                    "DELETE r "
                    "CREATE (e)-[new_r:CORRECTED {type: $new_relation}]->(to_entity) "
                    "RETURN new_r"
                )
                result = session.run(query, 
                    from_entity=triple['from_entity'], 
                    to_entity=triple['to_entity'], 
                    new_relation=triple['corrected_relation']
                )
                corrected_triples.append(result.single()[0])
        
        return corrected_triples

    def query_kg(self, query):
        """
        Execute a Cypher query on the Knowledge Graph
        
        :param query: Cypher query string
        :return: Query results
        """
        with self.driver.session() as session:
            result = session.run(query)
            return [record for record in result]

    def __del__(self):
        """
        Close the Neo4j driver when the object is deleted
        """
        if hasattr(self, 'driver'):
            self.driver.close()