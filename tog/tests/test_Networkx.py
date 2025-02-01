from ..kg import NetworkxKG

def test_sample_kg_visualization():
    kg = NetworkxKG(graph_endpoint='knowledge_graph.json')
    kg.visualize()

class TestNetworkx:
    def test_extract_initial_entities(self):
        kg = NetworkxKG(graph_endpoint='knowledge_graph.json')
        entities = kg.extract_initial_entities("Who was the first president of the United States?")
        assert isinstance(entities, list)
        assert len(entities) > 0
        assert isinstance(entities[0], str)

    def test_retrieve_initial_triples(self):
        pass

    def test_retrieve_relations(self):
        pass

    def test_prune_relations(self):
        pass

    def test_evaluate_paths(self):
        pass

    def test_generate_answer(self):
        pass

    def test_run(self):
        pass

