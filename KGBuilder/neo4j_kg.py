from neo4j import GraphDatabase

class Neo4jKG:
    def __init__(self, uri, user, password, database="neo4j"):
        """
        Initializes a connection to the Neo4j database.
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database

    def close(self):
        """
        Closes the database connection.
        """
        if self.driver:
            self.driver.close()

    def create_node(self, label, properties):
        """
        Creates a node in the graph with the specified label and properties.
        :param label: The label for the node (e.g., "Person").
        :param properties: A dictionary of properties (e.g., {"name": "Alice", "age": 30}).
        """
        query = f"CREATE (n:{label} $properties) RETURN n"
        with self.driver.session(database=self.database) as session:
            result = session.run(query, properties=properties)
            return result.single()

    def create_relationship(self, node1, rel_type, node2):
        """
        Creates a relationship between two nodes.
        :param node1: A dictionary representing the first node's label and properties.
        :param rel_type: The type of the relationship (e.g., "FRIEND").
        :param node2: A dictionary representing the second node's label and properties.
        """
        query = (
            f"MATCH (a:{node1['label']}), (b:{node2['label']}) "
            f"WHERE a.name = $node1_name AND b.name = $node2_name "
            f"CREATE (a)-[r:{rel_type}]->(b) RETURN r"
        )
        parameters = {
            "node1_name": node1["properties"]["name"],
            "node2_name": node2["properties"]["name"],
        }
        with self.driver.session(database=self.database) as session:
            result = session.run(query, **parameters)
            return result.single()

    def query_graph(self, query, parameters=None):
        """
        Runs a custom Cypher query and returns the results.
        :param query: The Cypher query as a string.
        :param parameters: Optional dictionary of parameters.
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, **(parameters or {}))
            return [record for record in result]

    def delete_node(self, label, property_key, property_value):
        """
        Deletes a node based on a property key and value.
        :param label: The label of the node.
        :param property_key: The property key to match.
        :param property_value: The value of the property to match.
        """
        query = f"MATCH (n:{label} {{ {property_key}: $value }}) DELETE n"
        with self.driver.session(database=self.database) as session:
            session.run(query, value=property_value)

    def update_node(self, label, property_key, property_value, updates):
        """
        Updates properties of a node.
        :param label: The label of the node.
        :param property_key: The property key to match.
        :param property_value: The value of the property to match.
        :param updates: Dictionary of properties to update.
        """
        set_clause = ", ".join(f"n.{k} = ${k}" for k in updates.keys())
        query = (
            f"MATCH (n:{label} {{ {property_key}: $value }}) "
            f"SET {set_clause} RETURN n"
        )
        parameters = {"value": property_value, **updates}
        with self.driver.session(database=self.database) as session:
            result = session.run(query, **parameters)
            return result.single()

# Usage Example
if __name__ == "__main__":
    graph = Neo4jKG("bolt://localhost:7687", "neo4j", "password")
    graph.create_node("Person", {"name": "Alice", "age": 30})
    graph.create_node("Person", {"name": "Bob", "age": 35})
    graph.create_relationship(
        {"label": "Person", "properties": {"name": "Alice"}},
        "FRIEND",
        {"label": "Person", "properties": {"name": "Bob"}}
    )
    results = graph.query_graph("MATCH (n) RETURN n")
    print(results)
    graph.close()
