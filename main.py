import os
from KGBuilder.extractors import AzureOpenAIExtractor
from KGBuilder.networkx_buillder import NxKG

text = '''Tesla, founded by Elon Musk in 2003, is a leading electric vehicle manufacturer headquartered in Palo Alto, California.
 The company focuses on sustainable energy solutions, with key products like the Tesla Model S, Model 3, Model X, and Model Y.
 In addition to vehicles, Tesla has expanded into solar energy through its SolarCity acquisition in 2016.
 SpaceX, another company founded by Musk, is focused on space exploration and collaborates with NASA on various missions. 
 Meanwhile, SpaceX's Starship program aims to enable human colonization of Mars. NASA has also partnered with Tesla for advanced battery technology in space missions. 
 In 2021, Tesla surpassed $1 trillion in market capitalization, making it one of the most valuable companies in the world.
'''
extractor = AzureOpenAIExtractor(
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"), 
    azure_deployment="gpt-4o-mini",  
    api_version="2024-02-01"
)
result = extractor.extract(text=text)

kg = NxKG()
kg.load_from_json(result)
kg.visualize(output_file="KG_sample12.html")