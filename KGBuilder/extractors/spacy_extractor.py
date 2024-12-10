import spacy


class SpaCyExtractor:
    def __init__(self, model="en_core_web_sm"):
        """
        Initialize the SpaCy Extractor with the specified model.

        :param model: The SpaCy model to use, default is "en_core_web_sm".
        """
        self.nlp = spacy.load(model)

    def extract(self, text):
        """
        Extract entities and basic subject-object relationships using SpaCy.

        :param text: The input text for extraction.
        :return: A dictionary containing entities and relationships.
        """
        doc = self.nlp(text)

        entities = list(set([(ent.text, ent.label_) for ent in doc.ents]))
        relationships = []

        for token in doc:
            # Identify subject-verb-object relationships
            if token.dep_ == "nsubj" and token.head.pos_ == "VERB":
                subject = token.text
                for child in token.head.children:
                    if child.dep_ == "dobj":
                        relationship = {
                            "source": subject,
                            "relation": token.head.text,
                            "target": child.text,
                        }
                        relationships.append(relationship)

        return {"entities": entities, "relationships": relationships}


# Example Usage
if __name__ == "__main__":
    text = "Barack Obama was the 44th President of the United States and married Michelle Obama."
    extractor = SpaCyExtractor()
    graph_data = extractor.extract(text)
    print(graph_data)
