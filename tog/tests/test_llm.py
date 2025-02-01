from ..llm import AzureOpenAILLM

def test_evalute_paths():
    llm = AzureOpenAILLM(model_name="gpt-4o")
    assert llm.evaluate_paths(["Hello, my name is", "I am a student"]) == ["John", "at the University of Toronto"]