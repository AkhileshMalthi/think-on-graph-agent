import spacy
import networkx as nx
from KGBuilder.extractor import SpaCyExtractor
from PyVis import visualize_graph_interactively

nlp = spacy.load("en_core_web_sm")

def extract_entities_and_relationships(text):
    doc = nlp(text)
    
    # Extract entities
    entities = [(ent.text, ent.label_) for ent in doc.ents]

    # Improved relationships based on more precise dependency rules
    relationships = []
    for token in doc:
        if token.dep_ in ["nsubj", "nsubjpass"]:
            subject = token.text
            predicate = token.head.lemma_  # Use lemma for verbs to unify (e.g., "is" and "are" -> "be")
            for child in token.head.children:
                if child.dep_ in ["dobj", "attr", "pobj"]:
                    obj = child.text
                    relationships.append((subject, predicate, obj))
    
    return entities, relationships

def create_graph(entities, relationships):
    G = nx.DiGraph()  # Use DiGraph for directed relationships
    
    # Add nodes (entities)
    for entity in entities:
        G.add_node(entity[0], type=entity[1])

    # Add edges (relationships)
    for relationship in relationships:
        subject, obj, rel_type = relationship
        G.add_edge(subject, obj, type=rel_type)
    
    return G

def main():
    # Example text
    text = """Anthony Edward "Tony" Stark was a billionaire industrialist, a founding member of the Avengers, and the former CEO of Stark Industries. A brash but brilliant inventor, Stark was self-described as a genius, billionaire, playboy, and philanthropist. With his great wealth and exceptional technical knowledge, Stark was one of the world's most powerful men following the deaths of his parents and enjoyed the playboy lifestyle for many years until he was kidnapped by the Ten Rings in Afghanistan, while demonstrating a fleet of Jericho missiles. With his life on the line, Stark created an armored suit which he used to escape his captors. Upon returning home, he utilized several more armors to use against terrorists, as well as Obadiah Stane who turned against Stark. Following his fight against Stane, Stark publicly revealed himself as Iron Man.
    Fresh off from defeating enemies all over the world, Stark found himself dying due to his own Arc Reactor poisoning his body, all while he was challenged by Ivan Vanko who attempted to destroy his legacy. After the Stark Expo incident, Stark reluctantly agreed to serve as a consultant for S.H.I.E.L.D. where he used his position to upgrade their technology while he began a relationship with Pepper Potts. With the world yet again being threatened, Stark joined the Avengers and helped defeat the Chitauri and Loki. Due to the battle, he suffered from post-traumatic stress disorder, leading him to create the Iron Legion to safeguard the world and help him retire.
    The 2013 "Mandarin" terrorist attacks forced Stark to come out of retirement to protect his country, inadvertently putting his loved ones at risk and leaving him defenseless when his home was destroyed. Stark continued his mission, finding Aldrich Killian as the mastermind of the attacks. Eventually, Stark defeated Killian, and was prompted to destroy all of his armors with the Clean Slate Protocol after almost losing Potts. However, when the Avengers were officially demobilized due to the War on HYDRA, Stark built more armors and resumed his role as Iron Man, aiding them in the capture of Baron Strucker and acquiring Loki's Scepter.
    Once the threat of HYDRA had been ended, at last, Stark, influenced by Wanda Maximoff's visions, built Ultron with the help of Bruce Banner as a new peacekeeping A.I. to protect the world and allow the Avengers to retire. However, Ultron believed that humanity threatened the world and thus, according to his program, decided to extinguish humanity. Through the work of the Avengers, Ultron was defeated, however, not without massive civilian cost and many lives being lost during which Sokovia was elevated into the sky.
    After the Ultron Offensive, Stark retired from active duty, still haunted by his role in the chaos the A.I. created. The guilt of creating Ultron and causing so much destruction and loss of life eventually convinced Stark to support the Sokovia Accords. Stark was forced to lead a manhunt for his ally Captain America when the latter began protecting the fugitive Winter Soldier, igniting the Avengers Civil War. The result left the Avengers in complete disarray, especially after Stark learned of the Winter Soldier's role in his parents' deaths. Afterwards, Stark returned to New York to mentor and guide Spider-Man into becoming a better hero than he ever was, also becoming engaged with Potts in the process.
    In 2018, when Thanos and the Black Order invaded Earth in their conquest to acquire the six Infinity Stones, Stark, Doctor Strange, and Spider-Man convened to battle Thanos on Titan with the help of the Guardians of the Galaxy. When Stark was held at Thanos' mercy, Doctor Strange surrendered the Time Stone for Stark's life. After the Snap, Stark and Nebula remained the sole survivors on Titan. Stark and Nebula used the Benatar to escape Titan, but were stranded in space as the ship was damaged. They were rescued by Captain Marvel, who brought them back to Earth.
    In the five years after the Snap, Stark chose to retire from being Iron Man, marrying Potts and having a daughter, Morgan. When Stark devised a method to safely travel through time and space, he rejoined the Avengers in their mission to acquire the six Infinity Stones from the past in order to resurrect those killed by the Snap, and traveled back in time to retrieve the Scepter and regain the Tesseract. During the Battle of Earth, Stark sacrificed himself to eliminate an alternate version of Thanos and his army, who traveled through time to collect their Infinity Stones, saving the universe from decimation and leaving behind a legacy as one of Earth's most revered superheroes."""

    # Extract entities and relationships
    extractor = SpaCyExtractor()
    result = extractor.extract(text)
    print(result)
    
    # Create and visualize the graph
    G = create_graph(result['entities'], result['relationships'])
    visualize_graph_interactively(G)

if __name__ == '__main__':
    main()
