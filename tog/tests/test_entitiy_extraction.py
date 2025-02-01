from ..llm.AzureOpenAI import AzureOpenAILLM

def test_extract_initial_entities():
    llm = AzureOpenAILLM(model_name="gpt-4o")
    query = "What is the capital of France?"
    entities = llm.extract_initial_entities(query)
    assert "France" in entities

def test_extract_initial_entities_no_entities():
    llm = AzureOpenAILLM(model_name="gpt-4o")
    query = "Hello, how are you?"
    entities = llm.extract_initial_entities(query)
    assert entities == []

def test_extract_initial_entities_multiple_entities():
    llm = AzureOpenAILLM(model_name="gpt-4o")
    query = "What are the capitals of France and Germany?"
    entities = llm.extract_initial_entities(query)
    assert all(entity in entities for entity in ["France", "Germany"])

def test_extract_initial_entities_with_special_characters():
    llm = AzureOpenAILLM(model_name="gpt-4o")
    query = "What is the capital of Côte d'Ivoire?"
    entities = llm.extract_initial_entities(query)
    assert all(entity in entities for entity in ["Côte d'Ivoire"])

def test_extract_initial_entities_with_numbers():
    llm = AzureOpenAILLM(model_name="gpt-4o")
    query = "What is the population of New York in 2020?"
    entities = llm.extract_initial_entities(query)
    assert all(entity in entities for entity in ["New York", "2020"])
