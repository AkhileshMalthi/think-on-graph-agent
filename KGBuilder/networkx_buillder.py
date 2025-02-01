import networkx as nx
from pyvis.network import Network


class NxKG:
    def __init__(self):
        """
        Initialize a new knowledge graph using NetworkX.
        """
        self.graph = nx.MultiDiGraph()
        self.id_to_name = {}  # Mapping from ID to name for relationship resolution

    def add_entity(self, entity_id, name, **properties):
        """
        Add an entity to the knowledge graph with arbitrary properties.

        Args:
            entity_id (str): Unique identifier for the entity
            name (str): Name of the entity
            **properties: Arbitrary keyword arguments for entity properties
        """
        self.id_to_name[entity_id] = name
        self.graph.add_node(entity_id, name=name, **properties)

    def add_relationship(self, source_id, target_id, **properties):
        """
        Add a relationship between two entities with arbitrary properties.

        Args:
            source_id (str): ID of the source entity
            target_id (str): ID of the target entity
            **properties: Arbitrary keyword arguments for relationship properties
        """
        self.graph.add_edge(source_id, target_id, **properties)
        return self

    def load_from_json(self, json_data):
        """
        Load a knowledge graph from a JSON dictionary.

        Args:
            json_data (dict): JSON dictionary containing entities and relationships
        """
        # Add entities with all their properties
        for entity in json_data.get("entities", []):
            # Extract id and name, use remaining properties as is
            entity_id = entity.pop("id")
            name = entity.pop("name")
            self.add_entity(entity_id, name, **entity)

        # Add relationships with all their properties
        for relationship in json_data.get("relationships", []):
            # Create a copy of the relationship dictionary
            rel_props = relationship.copy()
            # Extract source and target IDs
            source_id = rel_props.pop("source_id")
            target_id = rel_props.pop("target_id")
            # Convert strength to string category for visualization
            if "strength" in rel_props:
                strength_value = rel_props["strength"]
                if strength_value >= 0.8:
                    rel_props["strength"] = "strong"
                elif strength_value >= 0.6:
                    rel_props["strength"] = "medium"
                else:
                    rel_props["strength"] = "weak"
            self.add_relationship(source_id, target_id, **rel_props)
        return self

    def visualize(
        self,
        output_file="knowledge_graph.html",
        node_color_property="type",
        node_color_map=None,
    ):
        """
        Visualize the knowledge graph using PyVis.

        Args:
            output_file (str): Path to save the HTML visualization
            node_color_property (str): Node property to use for coloring
            node_color_map (dict): Mapping of property values to colors
        """
        if node_color_map is None:
            node_color_map = {
                "Person": "#87CEFA",
                "Organization": "#90EE90",
                "Location": "#FFA07A",
                "Field of Study": "#DDA0DD",
            }

        net = Network(
            height="600px",
            width="100%",
            bgcolor="#ffffff",
            font_color="black",
            notebook=False,
        )

        # Add nodes
        for node_id, data in self.graph.nodes(data=True):
            # Get color based on the specified property if it exists
            color = node_color_map.get(
                data.get(node_color_property, ""), "#D3D3D3"  # Default color
            )

            # Create tooltip content
            tooltip_data = {k: v for k, v in data.items() if k != "name"}
            tooltip = "\n".join(f"{k}: {v}" for k, v in tooltip_data.items())

            # Use name for label, fall back to ID if name not available
            label = data.get("name", node_id)
            net.add_node(node_id, label=label, title=tooltip, color=color)

        # Add edges
        for source_id, target_id, data in self.graph.edges(data=True):
            # Create tooltip content
            tooltip = "\n".join(f"{k}: {v}" for k, v in data.items())

            # Use types as label if it exists
            label = ", ".join(data.get("types", []))

            # Use strength for color
            strength_color_map = {
                "strong": "#000000",
                "medium": "#808080",
                "weak": "#C0C0C0",
            }
            edge_color = strength_color_map.get(data.get("strength", ""), "#808080")

            net.add_edge(source_id, target_id, label=label, title=tooltip, color=edge_color)

        # Configure physics and interaction
        net.set_options(
            """
        var options = {
            "nodes": {
                "font": {"size": 12},
                "scaling": {"min": 10, "max": 30}
            },
            "edges": {
                "color": {"inherit": false},
                "smooth": false,
                "font": {"size": 10}
            },
            "physics": {
                "barnesHut": {
                    "gravitationalConstant": -3000,
                    "springLength": 200,
                    "springConstant": 0.01
                },
                "minVelocity": 0.75
            }
        }
        """
        )

        net.save_graph(output_file)
        print(f"Check out the visualization in {output_file}")
        return self

    def get_entities_by_property(self, property_name, property_value):
        """
        Retrieve all entities that have a specific property value.

        Args:
            property_name (str): Name of the property to filter by
            property_value: Value of the property to match

        Returns:
            list: Entities matching the property criteria
        """
        return [
            node
            for node, data in self.graph.nodes(data=True)
            if data.get(property_name) == property_value
        ]

    def get_relationships_for_entity(self, entity_id):
        """
        Get all relationships for a specific entity.

        Args:
            entity_id (str): ID of the entity

        Returns:
            dict: Outgoing and incoming relationships
        """
        return {
            "outgoing": list(self.graph.out_edges(entity_id, data=True)),
            "incoming": list(self.graph.in_edges(entity_id, data=True)),
        }

    def export_to_json(self):
        """
        Export the knowledge graph to a JSON format.

        Returns:
            dict: JSON representation of the knowledge graph
        """
        entities = []
        for node_id, data in self.graph.nodes(data=True):
            entity_data = data.copy()
            name = entity_data.pop("name")
            entities.append({"id": node_id, "name": name, **entity_data})

        relationships = []
        for source_id, target_id, data in self.graph.edges(data=True):
            rel_data = data.copy()
            relationships.append({
                "source_id": source_id,
                "target_id": target_id,
                **rel_data
            })

        return {"entities": entities, "relationships": relationships}


# Example usage
if __name__ == "__main__":
    # Sample data with the new schema
    sample_data =  {
    "entities": [
      {
        "id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "name": "Cannabidiol",
        "type": "Chemical Compound",
        "aliases": [
          "CBD"
        ],
        "description": "Cannabidiol is a non-psychoactive compound found in Cannabis spp. with broad therapeutic value.",
        "attributes": {
          "therapeutic_value": "broad",
          "source": "Cannabis spp."
        },
        "chunk_refs": [
          "527c0f3809acba8d4d487efffcdd1079",
          "fff700f33c96d074e1568b990992c9ac",
          "d1867014a49dc6d33d789ace285e7390",
          "a3fe9298a663e7d36c66f6fd6e8350a8",
          "434f4f7a509cc817c213d724c5121179",
          "1716edf8e0575017a4b1228820b78beb",
          "135e9ae6c1bd0fd8ce998ed7f2781862",
          "d8e7370962a1001898cf1e1cd9d2294e",
          "6df50e78b082ac5d95692b2e6a1192b0",
          "06c33232865b0a4e730522561c5aa2bc"
        ]
      },
      {
        "id": "7f6895ff3db6d325cb8ea0a2d121ad64",
        "name": "Cannabidiol Users",
        "type": "Demographic",
        "aliases": [],
        "description": "Individuals who use cannabidiol products for various reasons.",
        "attributes": {
          "reasons_for_use": "not specified"
        },
        "chunk_refs": [
          "06c33232865b0a4e730522561c5aa2bc"
        ]
      },
      {
        "id": "ad55f8d7c392c163d1b19494b50e1729",
        "name": "Cross-Sectional Study",
        "type": "Research Study",
        "aliases": [],
        "description": "A research study design used to examine the characteristics of cannabidiol users.",
        "attributes": {
          "study_type": "cross-sectional",
          "study_subject": "cannabidiol users"
        },
        "chunk_refs": [
          "06c33232865b0a4e730522561c5aa2bc"
        ]
      },
      {
        "id": "cfac4980cd10e31753b142a706920440",
        "name": "U.S. Drug Enforcement Administration",
        "type": "Government Agency",
        "aliases": [],
        "description": "A government agency that classifies cannabidiol as a Schedule I controlled substance.",
        "attributes": {
          "classification": "Schedule I controlled substance"
        },
        "chunk_refs": [
          "06c33232865b0a4e730522561c5aa2bc"
        ]
      },
      {
        "id": "75a0ee3665b474dcda1287014f0387ee",
        "name": "U.S. Food and Drug Administration",
        "type": "Government Agency",
        "aliases": [],
        "description": "A government agency that does not recognize cannabidiol as a dietary supplement ingredient.",
        "attributes": {
          "recognition": "not recognized as dietary supplement"
        },
        "chunk_refs": [
          "434f4f7a509cc817c213d724c5121179",
          "06c33232865b0a4e730522561c5aa2bc"
        ]
      },
      {
        "id": "fa5f7aaefcf6032635ed725d9f8ad6e0",
        "name": "Online Survey",
        "type": "Research Method",
        "aliases": [],
        "description": "A method used to recruit participants for the study on cannabidiol users.",
        "attributes": {
          "recruitment_method": "online survey"
        },
        "chunk_refs": [
          "225cbb08d037d4a7746d47c931e45ec7",
          "06c33232865b0a4e730522561c5aa2bc"
        ]
      },
      {
        "id": "5f39aa2e03c2d02af57ddb9c581eeaa2",
        "name": "CBD",
        "type": "Entity",
        "aliases": [
          "cannabidiol"
        ],
        "description": "Cannabidiol, a non-psychoactive compound, is being used by consumers as a therapy for various medical conditions.",
        "attributes": {
          "therapeutic potential": "high"
        },
        "chunk_refs": [
          "7e8a191787570c4f45f67384be57ba29",
          "f9dc543f76c25659e7d883a263585f7c",
          "3e0b5cdd3082797423f388409c351fbd",
          "befc75f0974d434765527d4b2de9f2c3",
          "b782e359c27dbde3a3084a4fae577a09",
          "7e17931eb101c758d54bfb0e7b4c8a84",
          "17fdeb30ccdf930b61fcb9a12d61afa3",
          "b1cf1023fec157e1eb9e6ec8751b5d87",
          "dc819420ff510d15bb4611c8e1e2e2e6",
          "fdac444e60e75aca0ccda30488843c84"
        ]
      },
      {
        "id": "3609aa0c27d6d33db45a3f9fe0ec89dd",
        "name": "Medical Conditions",
        "type": "Entity",
        "aliases": [
          "medical condition",
          "medical conditions"
        ],
        "description": "Various health issues being treated with CBD, including pain, anxiety, depression, and sleep disorders.",
        "attributes": {
          "types": [
            "pain",
            "anxiety",
            "depression",
            "sleep disorders"
          ]
        },
        "chunk_refs": [
          "7e8a191787570c4f45f67384be57ba29",
          "f9dc543f76c25659e7d883a263585f7c",
          "b782e359c27dbde3a3084a4fae577a09",
          "dc819420ff510d15bb4611c8e1e2e2e6",
          "17fdeb30ccdf930b61fcb9a12d61afa3"
        ]
      },
      {
        "id": "0e86c574a6bdd0b6668d0d3f88887434",
        "name": "Consumers",
        "type": "Entity",
        "aliases": [
          "users",
          "respondents"
        ],
        "description": "Individuals using CBD to treat medical conditions, with a significant proportion reporting positive results.",
        "attributes": {
          "usage rate": "62%"
        },
        "chunk_refs": [
          "7e8a191787570c4f45f67384be57ba29"
        ]
      },
      {
        "id": "8963c8182d0dd21bf0073007eac2f3c1",
        "name": "Cannabis",
        "type": "Entity",
        "aliases": [
          "marijuana"
        ],
        "description": "A plant from which CBD is derived, with regular and non-regular users exhibiting different usage patterns.",
        "attributes": {
          "relation to CBD": "source"
        },
        "chunk_refs": [
          "3e0b5cdd3082797423f388409c351fbd",
          "7e8a191787570c4f45f67384be57ba29"
        ]
      },
      {
        "id": "5a2013e3e31b464d3d9773b937f6da37",
        "name": "Research",
        "type": "Entity",
        "aliases": [
          "further research"
        ],
        "description": "A necessary step to better understand the therapeutic potential of CBD and its effects on various medical conditions.",
        "attributes": {
          "rationale": "compelling"
        },
        "chunk_refs": [
          "dc819420ff510d15bb4611c8e1e2e2e6",
          "7e8a191787570c4f45f67384be57ba29"
        ]
      },
      {
        "id": "4dab2eba3497c621ad5ddab69a2e14e8",
        "name": "Cannabis sativa L",
        "type": "Plant Species",
        "aliases": [
          "Cannabis spp.",
          "Cannabis",
          "marijuana",
          "hemp"
        ],
        "description": "A plant species that contains over a hundred cannabinoids, including Cannabidiol and tetrahydrocannabinol.",
        "attributes": {
          "common names": [
            "marijuana",
            "hemp"
          ]
        },
        "chunk_refs": [
          "434f4f7a509cc817c213d724c5121179"
        ]
      },
      {
        "id": "8cffefdfcd28ebd6b421f89fa72173ca",
        "name": "Tetrahydrocannabinol",
        "type": "Chemical Compound",
        "aliases": [
          "THC"
        ],
        "description": "A psychoactive cannabinoid found in Cannabis sativa L, often used in conjunction with Cannabidiol.",
        "attributes": {
          "abundance": "most abundant cannabinoid in Cannabis"
        },
        "chunk_refs": [
          "434f4f7a509cc817c213d724c5121179",
          "527c0f3809acba8d4d487efffcdd1079"
        ]
      },
      {
        "id": "b98e0837815ab77e51e1bef5719e080c",
        "name": "Medical Conditions",
        "type": "Disease or Disorder",
        "aliases": [
          "seizure disorders",
          "psychotic symptoms",
          "anxiety",
          "depression",
          "inflammation",
          "cancer",
          "cardiovascular diseases",
          "neurodegeneration",
          "multiple sclerosis",
          "chronic pain"
        ],
        "description": "Various health conditions that Cannabidiol has shown potential therapeutic efficacy against.",
        "attributes": {
          "treatment options": [
            "Cannabidiol",
            "THC"
          ]
        },
        "chunk_refs": [
          "434f4f7a509cc817c213d724c5121179"
        ]
      },
      {
        "id": "60e12faf5ad9c245816e5a625b4a0bde",
        "name": "FDA",
        "type": "Administration",
        "aliases": [
          "Administration"
        ],
        "description": "The Food and Drug Administration, responsible for approving drugs in the United States.",
        "attributes": {
          "abbreviation": "FDA"
        },
        "chunk_refs": [
          "3c83f56c2f5f40be06649e1dfc000bc7"
        ]
      },
      {
        "id": "0c4de6be81918a873c9c419592e5509f",
        "name": "Epidiolex",
        "type": "Drug",
        "aliases": [
          "cannabidiol"
        ],
        "description": "A plant-derived Cannabis compound approved as a drug by the FDA for the treatment of pediatric seizure disorders.",
        "attributes": {
          "type": "Cannabis compound",
          "approval_date": "June 2018"
        },
        "chunk_refs": [
          "3c83f56c2f5f40be06649e1dfc000bc7"
        ]
      },
      {
        "id": "ae85d731c7ee2616fdf34d8edd6addce",
        "name": "CBD",
        "type": "Compound",
        "aliases": [
          "isolated from marijuana"
        ],
        "description": "A compound derived from marijuana, used in the treatment of pediatric seizure disorders.",
        "attributes": {
          "source": "marijuana"
        },
        "chunk_refs": [
          "3c83f56c2f5f40be06649e1dfc000bc7",
          "e317b24947911f93f17fb3b1a68af31a"
        ]
      },
      {
        "id": "a16aed7a6e86ac4fc5884c50b2eadb13",
        "name": "Pediatric seizure disorders",
        "type": "Medical Condition",
        "aliases": [
          "two pediatric seizure disorders"
        ],
        "description": "A medical condition affecting children, treated with Epidiolex.",
        "attributes": {
          "treatment": "Epidiolex"
        },
        "chunk_refs": [
          "3c83f56c2f5f40be06649e1dfc000bc7"
        ]
      },
      {
        "id": "4668196353afbe5540abe5fc5c579fc6",
        "name": "DEA",
        "type": "Administration",
        "aliases": [
          "Drug Enforcement Administration"
        ],
        "description": "The Drug Enforcement Administration, responsible for regulating controlled substances in the United States.",
        "attributes": {
          "abbreviation": "DEA"
        },
        "chunk_refs": [
          "3c83f56c2f5f40be06649e1dfc000bc7"
        ]
      },
      {
        "id": "42f3adee1e368c03018a625408ca098a",
        "name": "Cannabis",
        "type": "ENTITY",
        "aliases": [
          "Cannabis"
        ],
        "description": "Cannabis is a plant-based substance that is the main topic of research in the given context.",
        "attributes": {
          "research_volume": "3.1"
        },
        "chunk_refs": [
          "14ea1677d12ed444aa1fc42a6f356a29",
          "f73165fbd7717b37de537750ca3ef2c8",
          "2e976f3ffc590a63916f0a466eb861e1",
          "dd08513ddb7318829d671fa32dc2cf3f"
        ]
      },
      {
        "id": "a661910ec6e666b2f6c361008c1ae236",
        "name": "Cannabinoid Research",
        "type": "ENTITY",
        "aliases": [
          "Cannabinoid Research",
          "Cannabis and Cannabinoid Research"
        ],
        "description": "Cannabinoid Research is a scientific study focused on the effects and properties of cannabinoids, which are found in the cannabis plant.",
        "attributes": {
          "volume": "3.1",
          "year": "2018",
          "doi": "10.1089/can.2018.0006"
        },
        "chunk_refs": [
          "f73165fbd7717b37de537750ca3ef2c8"
        ]
      },
      {
        "id": "61084b6195b088f4158b1c6f6b909ae0",
        "name": "Distribution",
        "type": "ENTITY",
        "aliases": [
          "distribution"
        ],
        "description": "Distribution refers to the act of making the research available to the public, which is permitted under the Creative Commons Attribution License.",
        "attributes": {
          "license": "Creative Commons Attribution License"
        },
        "chunk_refs": [
          "f73165fbd7717b37de537750ca3ef2c8"
        ]
      },
      {
        "id": "93ff93556b30583162232d212ad93928",
        "name": "Nabiximols",
        "type": "Drug",
        "aliases": [
          "Sativex"
        ],
        "description": "A combination drug with equal parts CBD and THC, approved to treat spasticity due to multiple sclerosis in many countries.",
        "attributes": {
          "approved_countries": ">30 countries"
        },
        "chunk_refs": [
          "6df50e78b082ac5d95692b2e6a1192b0"
        ]
      },
      {
        "id": "561d1b1307fa9ab46a66597a58346648",
        "name": "Multiple Sclerosis",
        "type": "Disease",
        "aliases": [],
        "description": "A condition treated by nabiximols (Sativex) in many countries.",
        "attributes": {
          "treatment": "spasticity"
        },
        "chunk_refs": [
          "1716edf8e0575017a4b1228820b78beb",
          "6df50e78b082ac5d95692b2e6a1192b0"
        ]
      },
      {
        "id": "aa4812e81e63eaa262314ddf4ca9ab6b",
        "name": "United States",
        "type": "Country",
        "aliases": [],
        "description": "A country where nabiximols (Sativex) is not approved.",
        "attributes": {
          "approval_status": "not approved"
        },
        "chunk_refs": [
          "e317b24947911f93f17fb3b1a68af31a",
          "0bf4cf8ef10cdcfe67c1b9ff9fd4baf4",
          "6df50e78b082ac5d95692b2e6a1192b0"
        ]
      },
      {
        "id": "71a3695466a233c43c6d03936330adbd",
        "name": "European Union",
        "type": "Region",
        "aliases": [],
        "description": "A region where individual member states determine the legality of CBD.",
        "attributes": {
          "legality_determination": "individual member states"
        },
        "chunk_refs": [
          "6df50e78b082ac5d95692b2e6a1192b0"
        ]
      },
      {
        "id": "9761f234f3d2b3a3ccc1e2b7d888e5ab",
        "name": "World Health Organization",
        "type": "Organization",
        "aliases": [],
        "description": "An organization with an Expert Committee on Drug Dependence that recommends.",
        "attributes": {
          "committee": "Expert Committee on Drug Dependence"
        },
        "chunk_refs": [
          "6df50e78b082ac5d95692b2e6a1192b0"
        ]
      },
      {
        "id": "a3dcdcf47634dd8ace09839f0f160461",
        "name": "Canada",
        "type": "Country",
        "aliases": [],
        "description": "A country that legalized Cannabis for recreational use in June 2018.",
        "attributes": {
          "legalization_date": "June 2018"
        },
        "chunk_refs": [
          "6df50e78b082ac5d95692b2e6a1192b0"
        ]
      },
      {
        "id": "64154fe0ef7a56f70668c352ea0d0383",
        "name": "CBD",
        "type": "Chemical Compound",
        "aliases": [
          "cannabidiol"
        ],
        "description": "A non-psychoactive compound found in the Cannabis sativa plant, with potential therapeutic benefits.",
        "attributes": {
          "schedule_status": "recommended not to be controlled by Schedule I of the 1961 UN Single Convention"
        },
        "chunk_refs": [
          "9d1e450b9c308c261f7837f9a43aae24",
          "1ccf2014205c26d63543890dd419d2b8",
          "f71f89736cc407d498719eb69377866f"
        ]
      },
      {
        "id": "e6d154e8ce36a036ce43fbfefc907f44",
        "name": "UN Single Convention",
        "type": "International Treaty",
        "aliases": [
          "1961 UN Single Convention on Narcotic Drugs"
        ],
        "description": "A global drug control treaty that aims to limit the production and trade of narcotic drugs.",
        "attributes": {
          "year": "1961"
        },
        "chunk_refs": [
          "1ccf2014205c26d63543890dd419d2b8"
        ]
      },
      {
        "id": "51b3eeb20a301035500441f919539ceb",
        "name": "DEA",
        "type": "Government Agency",
        "aliases": [
          "Drug Enforcement Administration"
        ],
        "description": "A United States federal law enforcement agency responsible for enforcing controlled substances laws and regulations.",
        "attributes": {
          "jurisdiction": "United States"
        },
        "chunk_refs": [
          "1ccf2014205c26d63543890dd419d2b8",
          "0bf4cf8ef10cdcfe67c1b9ff9fd4baf4"
        ]
      },
      {
        "id": "e659708baa7652120dd937268c3a2abd",
        "name": "Farm Act",
        "type": "Legislation",
        "aliases": [
          "2014 Farm Bill"
        ],
        "description": "A United States federal law that regulates agricultural production, including industrial hemp.",
        "attributes": {
          "year": "2014"
        },
        "chunk_refs": [
          "1ccf2014205c26d63543890dd419d2b8"
        ]
      },
      {
        "id": "c0f9fe0bc9d528b6b5f227249e3c76ab",
        "name": "Controlled Substances Act",
        "type": "Legislation",
        "aliases": [
          "CSA"
        ],
        "description": "A United States federal law that regulates the manufacture, distribution, and possession of controlled substances.",
        "attributes": {
          "enforced_by": "DEA"
        },
        "chunk_refs": [
          "1ccf2014205c26d63543890dd419d2b8"
        ]
      },
      {
        "id": "9a469c73620bfb9b1a543cff64b339ed",
        "name": "Industrial Hemp",
        "type": "Agricultural Product",
        "aliases": [
          "nonpsychoactive hemp"
        ],
        "description": "A type of hemp that is cultivated for industrial purposes, with low THC content.",
        "attributes": {
          "legal_status": "exempt from CSA regulations under Farm Act"
        },
        "chunk_refs": [
          "1ccf2014205c26d63543890dd419d2b8"
        ]
      },
      {
        "id": "0138ded66cd80350ada4523db0b67652",
        "name": "Cannabis sativa",
        "type": "Plant Species",
        "aliases": [
          "marijuana"
        ],
        "description": "A plant species that includes both marijuana and industrial hemp.",
        "attributes": {
          "parts_used": "extracts, including CBD"
        },
        "chunk_refs": [
          "1ccf2014205c26d63543890dd419d2b8"
        ]
      },
      {
        "id": "b2368990b635d8f104b95e8235fbe86f",
        "name": "Cannabis sativa",
        "type": "Plant",
        "aliases": [
          "Cannabis"
        ],
        "description": "A plant species from which CBD is derived.",
        "attributes": {
          "part_of": "Controlled Substances Act of 1970"
        },
        "chunk_refs": [
          "527c0f3809acba8d4d487efffcdd1079",
          "fff700f33c96d074e1568b990992c9ac",
          "e317b24947911f93f17fb3b1a68af31a"
        ]
      },
      {
        "id": "966713f7b5ba031466d81d12bce78e43",
        "name": "FDA",
        "type": "Organization",
        "aliases": [
          "Food and Drug Administration"
        ],
        "description": "A regulatory body that does not recognize CBD as a dietary supplement ingredient.",
        "attributes": {
          "stance_on_CBD": "non-recognized"
        },
        "chunk_refs": [
          "e317b24947911f93f17fb3b1a68af31a"
        ]
      },
      {
        "id": "1f65dcfae8a1ed083767dd0d1ef9652c",
        "name": "DEA",
        "type": "Organization",
        "aliases": [
          "Drug Enforcement Administration"
        ],
        "description": "A regulatory body that prohibits hemp-derived CBD products.",
        "attributes": {
          "stance_on_CBD": "prohibited"
        },
        "chunk_refs": [
          "e317b24947911f93f17fb3b1a68af31a"
        ]
      },
      {
        "id": "6f2320d2dd15fcf4b2cdbf537aab1588",
        "name": "Cannabis users",
        "type": "Demographic",
        "aliases": [
          "CBD users"
        ],
        "description": "A group of people who have been studied, but with scarce individual use data.",
        "attributes": {
          "study_goal": "characterize individual use of CBD"
        },
        "chunk_refs": [
          "e317b24947911f93f17fb3b1a68af31a"
        ]
      },
      {
        "id": "336d9c9d3781f53eb2cd748c83ddae80",
        "name": "CBD",
        "type": "SUBSTANCE",
        "aliases": [
          "self-described CBD"
        ],
        "description": "The primary substance of interest in the study, whose usage patterns and effects are being investigated.",
        "attributes": {
          "usage_patterns": "",
          "effects": ""
        },
        "chunk_refs": [
          "2ca47679a68bf438938ba31edd098093"
        ]
      },
      {
        "id": "bdf7edd1c983379da818ab7c8eb029c9",
        "name": "Study",
        "type": "RESEARCH_PROJECT",
        "aliases": [
          "this study"
        ],
        "description": "The research project aimed at understanding CBD usage patterns and effects.",
        "attributes": {
          "goal": "to collect survey data to elucidate how, and why, individuals are using CBD",
          "protocol": "study protocol"
        },
        "chunk_refs": [
          "2ca47679a68bf438938ba31edd098093"
        ]
      },
      {
        "id": "de56869561ce8f8d217c39ae9b7490e6",
        "name": "Survey",
        "type": "DATA_COLLECTION_METHOD",
        "aliases": [
          "questionnaire"
        ],
        "description": "The data collection method used to gather information about CBD users.",
        "attributes": {
          "type": "novel",
          "domains": [
            "sociodemographics",
            "reasons for use",
            "duration and frequency of use",
            "method of administration",
            "perceived clinical efficacy",
            "adverse effects"
          ]
        },
        "chunk_refs": [
          "2ca47679a68bf438938ba31edd098093"
        ]
      },
      {
        "id": "38583cad94bdec91c0cd4f102a867012",
        "name": "Individuals",
        "type": "PARTICIPANTS",
        "aliases": [
          "users",
          "participants"
        ],
        "description": "The people who are using CBD and are participating in the study.",
        "attributes": {
          "characteristics": "",
          "reasons_for_use": "",
          "methods_of_use": ""
        },
        "chunk_refs": [
          "2ca47679a68bf438938ba31edd098093"
        ]
      },
      {
        "id": "36eb84ce6dc67d34567b54b4db77d540",
        "name": "San Diego State University",
        "type": "INSTITUTION",
        "aliases": [
          "SDSU"
        ],
        "description": "The institution where the study was conducted and approved.",
        "attributes": {
          "IRB": "Institutional Review Board"
        },
        "chunk_refs": [
          "2ca47679a68bf438938ba31edd098093"
        ]
      },
      {
        "id": "affe5369bba776beb57f02daf509e45f",
        "name": "CBD",
        "type": "Substance",
        "aliases": [
          "CBD product"
        ],
        "description": "The central substance of interest in the study, CBD (Cannabidiol) is a non-psychoactive compound found in cannabis plants.",
        "attributes": {
          "type": "Non-psychoactive compound"
        },
        "chunk_refs": [
          "225cbb08d037d4a7746d47c931e45ec7",
          "9af3669e6d678788131236a32f915b63",
          "10d60f2c9e68f682154b01d9d3afd253",
          "0bf4cf8ef10cdcfe67c1b9ff9fd4baf4"
        ]
      },
      {
        "id": "ecc5af9a5ddcdf9e8dadbd13285ab975",
        "name": "Respondents",
        "type": "Study Participants",
        "aliases": [
          "participants",
          "subjects"
        ],
        "description": "Individuals who participated in the online survey, providing valuable insights into their demographics, usage characteristics, and experiences with CBD.",
        "attributes": {
          "selection method": "Self-selected convenience sample"
        },
        "chunk_refs": [
          "225cbb08d037d4a7746d47c931e45ec7",
          "9af3669e6d678788131236a32f915b63"
        ]
      },
      {
        "id": "2ee2010b82889e662382823709b20125",
        "name": "Manufacturers",
        "type": "Industry Stakeholders",
        "aliases": [
          "CBD product manufacturers",
          "herbal vaporizer manufacturers"
        ],
        "description": "Companies involved in the production and distribution of CBD products, who assisted in recruitment by promoting the survey to their customers.",
        "attributes": {
          "roles": [
            "Recruitment assistance",
            "Product provision"
          ]
        },
        "chunk_refs": [
          "225cbb08d037d4a7746d47c931e45ec7"
        ]
      },
      {
        "id": "b96691f84476c5339d50de841d9998b7",
        "name": "SAS University Edition",
        "type": "Data Analysis Tool",
        "aliases": [
          "SAS 9.4"
        ],
        "description": "A software tool used for data analysis, providing functionalities for descriptive statistics, univariate, and bivariate comparisons.",
        "attributes": {
          "version": "9.4",
          "provider": "SAS Institute Inc."
        },
        "chunk_refs": [
          "225cbb08d037d4a7746d47c931e45ec7"
        ]
      },
      {
        "id": "3629034ddd27e8bf331ded0eb380da9a",
        "name": "Cannabis",
        "type": "SUBSTANCE",
        "aliases": [
          "Cannabis"
        ],
        "description": "Cannabis is a substance being researched in the context of Cannabinoid Research.",
        "attributes": {
          "research_area": "Cannabinoid Research"
        },
        "chunk_refs": [
          "0c5c9994148ed73b472acdadfb7696f6",
          "7975dd7cb686c5fc94fbed8018693cc9",
          "00c25bd0a0c202d272a9a038440caea2"
        ]
      },
      {
        "id": "0a7acc2ef545e418c7f8f94aa08aaf99",
        "name": "Cannabinoid Research",
        "type": "FIELD_OF_STUDY",
        "aliases": [
          "Cannabinoid Research"
        ],
        "description": "Cannabinoid Research is a field of study that investigates the effects of cannabis and its compounds.",
        "attributes": {
          "focus_area": "Cannabis"
        },
        "chunk_refs": [
          "7975dd7cb686c5fc94fbed8018693cc9"
        ]
      },
      {
        "id": "1202ea6325564b812abe3e3cf3ded136",
        "name": "Corroon and Phillips",
        "type": "AUTHORS",
        "aliases": [
          "Corroon",
          "Phillips"
        ],
        "description": "Corroon and Phillips are authors of a research paper on cannabis and cannabinoid research.",
        "attributes": {
          "publication_year": "2018"
        },
        "chunk_refs": [
          "7975dd7cb686c5fc94fbed8018693cc9"
        ]
      },
      {
        "id": "eb441e634597ca7955c41b207843d220",
        "name": "Odds ratios",
        "type": "STATISTICAL_MEASURE",
        "aliases": [
          "ORs"
        ],
        "description": "Odds ratios are a statistical measure used to estimate the strength of association in the research.",
        "attributes": {
          "calculation_method": "PROC LOGISTIC"
        },
        "chunk_refs": [
          "7975dd7cb686c5fc94fbed8018693cc9"
        ]
      },
      {
        "id": "82bb4815eafa20ef13686e689d0eb98e",
        "name": "Demographics",
        "type": "Study Aspect",
        "aliases": [
          "Respondent Characteristics"
        ],
        "description": "The characteristics of the respondents in the study, including gender, age, education, and location.",
        "attributes": {
          "gender_distribution": "Female: 50.87%, Male: 47.40%",
          "age_range": "55-74 years",
          "education_level": "College or postgraduate program (71.22%)",
          "location_distribution": "United States (91.23%), California (21.90%)"
        },
        "chunk_refs": [
          "9af3669e6d678788131236a32f915b63"
        ]
      },
      {
        "id": "f3056b27a0796b296c798a29f479940a",
        "name": "Final Study",
        "type": "Research Study",
        "aliases": [
          "Survey"
        ],
        "description": "The comprehensive study examining the use of CBD for medical and general health purposes.",
        "attributes": {
          "sample_size": "2409",
          "response_rate": "81 excluded"
        },
        "chunk_refs": [
          "9af3669e6d678788131236a32f915b63"
        ]
      },
      {
        "id": "996984d9e0a814664b95815957c11518",
        "name": "United States",
        "type": "Location",
        "aliases": [
          "U.S."
        ],
        "description": "The primary location of the respondents in the study.",
        "attributes": {
          "state_representation": "All 50 states",
          "respondent_distribution": "91.23%"
        },
        "chunk_refs": [
          "9af3669e6d678788131236a32f915b63"
        ]
      },
      {
        "id": "d37930cbfb84fc45a096b95425a123f3",
        "name": "Medical Condition",
        "type": "Entity",
        "aliases": [
          "medical condition",
          "medical conditions",
          "seizure disorders"
        ],
        "description": "A health problem or disease that can be treated with CBD",
        "attributes": {
          "treatment": "CBD"
        },
        "chunk_refs": [
          "7e17931eb101c758d54bfb0e7b4c8a84",
          "b1cf1023fec157e1eb9e6ec8751b5d87"
        ]
      },
      {
        "id": "5c10a4e8598b51e705a52713fc72f36a",
        "name": "Women",
        "type": "Entity",
        "aliases": [
          "women"
        ],
        "description": "Female respondents who use CBD to treat medical conditions",
        "attributes": {
          "odds_ratio": 1.65
        },
        "chunk_refs": [
          "b1cf1023fec157e1eb9e6ec8751b5d87"
        ]
      },
      {
        "id": "831d42b9235d08deda282da5e27aaeda",
        "name": "Men",
        "type": "Entity",
        "aliases": [
          "men"
        ],
        "description": "Male respondents who use CBD to treat medical conditions",
        "attributes": {
          "odds_ratio": 1.0
        },
        "chunk_refs": [
          "b1cf1023fec157e1eb9e6ec8751b5d87"
        ]
      },
      {
        "id": "918d332bb1e96cc0d4ac7ede4fe855d0",
        "name": "Age",
        "type": "Entity",
        "aliases": [
          "age"
        ],
        "description": "A factor that influences the use of CBD to treat medical conditions",
        "attributes": {
          "influence": "positively correlated with CBD use"
        },
        "chunk_refs": [
          "b1cf1023fec157e1eb9e6ec8751b5d87"
        ]
      },
      {
        "id": "459ce27af49a9d0e8063a6751f3d81bb",
        "name": "Respondents",
        "type": "Entity",
        "aliases": [
          "respondents"
        ],
        "description": "Individuals who participated in the survey and reported using CBD",
        "attributes": {
          "percentage": 61.56
        },
        "chunk_refs": [
          "f9dc543f76c25659e7d883a263585f7c",
          "b782e359c27dbde3a3084a4fae577a09",
          "7e17931eb101c758d54bfb0e7b4c8a84",
          "dc819420ff510d15bb4611c8e1e2e2e6",
          "b1cf1023fec157e1eb9e6ec8751b5d87"
        ]
      },
      {
        "id": "c03fe34012d79d395c3591ebf85a48da",
        "name": "Survey Respondents",
        "type": "Entity",
        "aliases": [],
        "description": "A group of 2409 individuals participating in a survey on CBD use and demographics.",
        "attributes": {
          "sample_size": 2409
        },
        "chunk_refs": [
          "befc75f0974d434765527d4b2de9f2c3"
        ]
      },
      {
        "id": "9ab3d0c03d5250e3ec1ebbbd0df42870",
        "name": "Gender",
        "type": "Entity",
        "aliases": [],
        "description": "A demographic characteristic of survey respondents.",
        "attributes": {
          "male_percentage": 47.4,
          "female_percentage": 50.87
        },
        "chunk_refs": [
          "befc75f0974d434765527d4b2de9f2c3"
        ]
      },
      {
        "id": "a96383dee5efe71430a6aeff93724fb3",
        "name": "Geography",
        "type": "Entity",
        "aliases": [],
        "description": "The location of survey respondents, primarily from the United States.",
        "attributes": {
          "primary_location": "United States",
          "us_states": [
            "Oregon",
            "Florida"
          ]
        },
        "chunk_refs": [
          "befc75f0974d434765527d4b2de9f2c3"
        ]
      },
      {
        "id": "ad0363d256248a7be1fcde8007238683",
        "name": "Cannabis Use",
        "type": "Entity",
        "aliases": [],
        "description": "The frequency of cannabis use among survey respondents.",
        "attributes": {
          "regular_use_percentage": 55.17,
          "nonregular_use_percentage": 44.83
        },
        "chunk_refs": [
          "befc75f0974d434765527d4b2de9f2c3"
        ]
      },
      {
        "id": "99a8326869e5fe2c2f577235136fdeeb",
        "name": "General Health and Well-being",
        "type": "Entity",
        "aliases": [],
        "description": "A primary reason for CBD use among survey respondents.",
        "attributes": {
          "percentage": 38.44
        },
        "chunk_refs": [
          "7e17931eb101c758d54bfb0e7b4c8a84",
          "befc75f0974d434765527d4b2de9f2c3"
        ]
      },
      {
        "id": "2124cf13402fac304722dbf3a8901271",
        "name": "Cannabinoid Research",
        "type": "RESEARCH_AREA",
        "aliases": [
          "Cannabis Research"
        ],
        "description": "Cannabinoid Research is a scientific field that studies the effects and properties of cannabinoids, including their therapeutic potential.",
        "attributes": {
          "Publication URL": "http://online.liebertpub.com/doi/10.1089/can.2018.0006"
        },
        "chunk_refs": [
          "00c25bd0a0c202d272a9a038440caea2"
        ]
      },
      {
        "id": "30a99d20c790f3c1bf6623949507a834",
        "name": "Cannabidiol",
        "type": "Medical Substance",
        "aliases": [
          "CBD"
        ],
        "description": "A non-psychoactive compound used for treating medical conditions.",
        "attributes": {
          "medical_condition_treatment": "Yes"
        },
        "chunk_refs": [
          "f3c6376687f0ebbedaecad1723d39abb"
        ]
      },
      {
        "id": "ed564c1dd67f3ddbe6aab33fd53b2d1c",
        "name": "Medical Condition",
        "type": "Disease",
        "aliases": [
          "Health Issue"
        ],
        "description": "A health problem or illness that requires medical attention.",
        "attributes": {
          "treatment_options": "Cannabidiol, others"
        },
        "chunk_refs": [
          "f3c6376687f0ebbedaecad1723d39abb"
        ]
      },
      {
        "id": "a4a9a4d736d6b4fbc5124779bd70431b",
        "name": "Sociodemographic",
        "type": "Demographic",
        "aliases": [
          "Demographic Characteristics"
        ],
        "description": "A set of characteristics that define a population, including age, gender, education, etc.",
        "attributes": {
          "characteristics": "Age, Gender, Education, etc."
        },
        "chunk_refs": [
          "f3c6376687f0ebbedaecad1723d39abb"
        ]
      },
      {
        "id": "10f3e79f0a5b38f08c5d08879b7befee",
        "name": "General Health",
        "type": "Health Status",
        "aliases": [
          "Well-being"
        ],
        "description": "A person's overall health and wellness.",
        "attributes": {
          "influencing_factors": "Medical Condition, Lifestyle, etc."
        },
        "chunk_refs": [
          "f3c6376687f0ebbedaecad1723d39abb"
        ]
      },
      {
        "id": "e1377a6c82db81fb50dc7951d4b8501d",
        "name": "Male",
        "type": "Gender",
        "aliases": [
          "Men",
          "Women"
        ],
        "description": "A gender category.",
        "attributes": {
          "gender_ratio": "32.93%"
        },
        "chunk_refs": [
          "f3c6376687f0ebbedaecad1723d39abb"
        ]
      },
      {
        "id": "d648964e8eb2c63273272c4b5ac98028",
        "name": "Education",
        "type": "Academic Background",
        "aliases": [
          "Educational Level"
        ],
        "description": "A person's level of education.",
        "attributes": {
          "levels": "College, Primary/middle school, High school/GED, Postgraduate, etc."
        },
        "chunk_refs": [
          "f3c6376687f0ebbedaecad1723d39abb"
        ]
      },
      {
        "id": "90f7e79a13ddfc9a6d524edf6273679b",
        "name": "CBD",
        "type": "ENTITY",
        "aliases": [
          "cannabidiol"
        ],
        "description": "A compound derived from cannabis, used for medical conditions.",
        "attributes": {
          "compound_type": "cannabinoid"
        },
        "chunk_refs": [
          "e7015dfb7e48ef9f8d3b12d3cf366507",
          "2e976f3ffc590a63916f0a466eb861e1",
          "f657d8ccebf4fdc599752d300607679b"
        ]
      },
      {
        "id": "66b8a1d4928ed893660ca9a015c64ed9",
        "name": "Medical Conditions",
        "type": "ENTITY",
        "aliases": [
          "medical condition"
        ],
        "description": "The various health issues for which respondents used CBD.",
        "attributes": {
          "examples": [
            "COPD",
            "PTSD"
          ]
        },
        "chunk_refs": [
          "2e976f3ffc590a63916f0a466eb861e1"
        ]
      },
      {
        "id": "d7ce4f59818b504c0b656cf7fd39aef7",
        "name": "COPD",
        "type": "ENTITY",
        "aliases": [
          "chronic obstructive pulmonary disease"
        ],
        "description": "A medical condition for which respondents used CBD.",
        "attributes": {
          "disease_type": "respiratory"
        },
        "chunk_refs": [
          "2e976f3ffc590a63916f0a466eb861e1"
        ]
      },
      {
        "id": "2f9af561952c61a22b569ce351902238",
        "name": "PTSD",
        "type": "ENTITY",
        "aliases": [
          "post-traumatic stress disorder"
        ],
        "description": "A medical condition for which respondents used CBD.",
        "attributes": {
          "disease_type": "mental health"
        },
        "chunk_refs": [
          "2e976f3ffc590a63916f0a466eb861e1"
        ]
      },
      {
        "id": "63bbeffb3d3ab09a10ee6e037c348c15",
        "name": "Respondents",
        "type": "ENTITY",
        "aliases": [],
        "description": "The individuals who participated in the study and reported using CBD for medical conditions.",
        "attributes": {
          "study_participants": "3963"
        },
        "chunk_refs": [
          "8b1a29f81847b8de655733132afdc7e8",
          "0c252c1114841dcef2babbca0f421465",
          "2e976f3ffc590a63916f0a466eb861e1",
          "f657d8ccebf4fdc599752d300607679b"
        ]
      },
      {
        "id": "1e85fb3fe8da0718e9ac96bc9ca50dbb",
        "name": "Corroon and Phillips",
        "type": "ENTITY",
        "aliases": [],
        "description": "The authors of the study on cannabis and cannabinoid research.",
        "attributes": {
          "study_publication": "Cannabis and Cannabinoid Research 2018"
        },
        "chunk_refs": [
          "8b1a29f81847b8de655733132afdc7e8",
          "2e976f3ffc590a63916f0a466eb861e1"
        ]
      },
      {
        "id": "3aa6b574d76110a57c22fa9b556f88bf",
        "name": "Administration Method",
        "type": "Entity",
        "aliases": [
          "method of administration",
          "topical use",
          "sublingual or pill or capsule form"
        ],
        "description": "Ways in which CBD is consumed or applied",
        "attributes": {
          "types": "liquids, sprays, drops, tinctures, topical, sublingual, pill, capsule"
        },
        "chunk_refs": [
          "7e17931eb101c758d54bfb0e7b4c8a84"
        ]
      },
      {
        "id": "507d4e351ea16bef5f4e05799cf11eca",
        "name": "Medical Doctor",
        "type": "ENTITY",
        "aliases": [
          "Medical Doctor",
          "Naturopathic Doctor"
        ],
        "description": "A licensed medical professional who recommends CBD for medical conditions",
        "attributes": {
          "recommendation_source": "CBD"
        },
        "chunk_refs": [
          "f657d8ccebf4fdc599752d300607679b"
        ]
      },
      {
        "id": "578bda7641e8a61dd0139e64d7c362ce",
        "name": "Medical Condition",
        "type": "ENTITY",
        "aliases": [
          "Medical Condition",
          "Medical Condition(s)"
        ],
        "description": "A health issue treated with CBD",
        "attributes": {
          "treatment_efficacy": "very well by itself",
          "CBD_treatment": "yes"
        },
        "chunk_refs": [
          "8b1a29f81847b8de655733132afdc7e8",
          "0c252c1114841dcef2babbca0f421465",
          "dd08513ddb7318829d671fa32dc2cf3f",
          "f657d8ccebf4fdc599752d300607679b"
        ]
      },
      {
        "id": "88c7173516b99342c1878d33d831d49e",
        "name": "Treatment Efficacy",
        "type": "ENTITY",
        "aliases": [
          "Treatment Efficacy"
        ],
        "description": "The effectiveness of CBD in treating medical conditions",
        "attributes": {
          "rating": "very well by itself",
          "respondents_reporting_efficacy": "35.80%"
        },
        "chunk_refs": [
          "8b1a29f81847b8de655733132afdc7e8",
          "f657d8ccebf4fdc599752d300607679b"
        ]
      },
      {
        "id": "7e31e7c2e4ae96384a8c64da4b2ae674",
        "name": "Chronic Pain",
        "type": "Medical Condition",
        "aliases": [
          "chronic pain"
        ],
        "description": "Chronic pain is a significant medical condition that affects individuals, and CBD is used to alleviate its symptoms.",
        "attributes": {
          "symptoms": "pain"
        },
        "chunk_refs": [
          "10d60f2c9e68f682154b01d9d3afd253"
        ]
      },
      {
        "id": "e8bfae1cd5fc688533ecd3ef5e892b27",
        "name": "Arthritis/Joint Pain",
        "type": "Medical Condition",
        "aliases": [
          "arthritis/joint pain"
        ],
        "description": "Arthritis/Joint Pain is a medical condition that causes inflammation and pain in the joints, and CBD is used to treat its symptoms.",
        "attributes": {
          "symptoms": "pain, inflammation"
        },
        "chunk_refs": [
          "10d60f2c9e68f682154b01d9d3afd253"
        ]
      },
      {
        "id": "50760c209feb23f9600fa8ad19f8eebe",
        "name": "Anxiety",
        "type": "Medical Condition",
        "aliases": [
          "anxiety"
        ],
        "description": "Anxiety is a mental health condition characterized by feelings of worry and fear, and CBD is used to alleviate its symptoms.",
        "attributes": {
          "symptoms": "worry, fear"
        },
        "chunk_refs": [
          "10d60f2c9e68f682154b01d9d3afd253"
        ]
      },
      {
        "id": "bc1c0df89ae991acf1a7f9991e9ecdc4",
        "name": "Cannabis Use",
        "type": "Substance Use",
        "aliases": [
          "Cannabis use"
        ],
        "description": "Cannabis use refers to the consumption of cannabis products, including CBD, for recreational or therapeutic purposes.",
        "attributes": {
          "purpose": "recreational, therapeutic"
        },
        "chunk_refs": [
          "10d60f2c9e68f682154b01d9d3afd253"
        ]
      },
      {
        "id": "9e52d69c78a0825e706a1b88fed356da",
        "name": "Side Effects",
        "type": "Adverse Effects",
        "aliases": [
          "side effects"
        ],
        "description": "Side effects refer to the unwanted or adverse reactions experienced by individuals using CBD.",
        "attributes": {
          "frequency": "common"
        },
        "chunk_refs": [
          "10d60f2c9e68f682154b01d9d3afd253"
        ]
      },
      {
        "id": "d0d618f3a7c7fb68dda89382690ebbb2",
        "name": "Adverse Effects",
        "type": "Adverse Effects",
        "aliases": [
          "adverse effects"
        ],
        "description": "Adverse effects are the unwanted or harmful reactions experienced by individuals using CBD.",
        "attributes": {
          "frequency": "common"
        },
        "chunk_refs": [
          "10d60f2c9e68f682154b01d9d3afd253"
        ]
      },
      {
        "id": "5fbab8665adf7cfcd025973e2411cded",
        "name": "Medical Users",
        "type": "Entity",
        "aliases": [
          "medical Cannabis users"
        ],
        "description": "Medical users are a key entity, as they are compared to general health and well-being users in the survey.",
        "attributes": {
          "adverse_effect_reported": "28.46%"
        },
        "chunk_refs": [
          "17fdeb30ccdf930b61fcb9a12d61afa3"
        ]
      },
      {
        "id": "a4033169173cd04a2e5ffe8a1e5e4ba3",
        "name": "General Health and Well-being Users",
        "type": "Entity",
        "aliases": [
          "general health and well-being"
        ],
        "description": "General health and well-being users are an important entity, as they are compared to medical users in the survey.",
        "attributes": {
          "adverse_effect_reported": "34.56%"
        },
        "chunk_refs": [
          "17fdeb30ccdf930b61fcb9a12d61afa3"
        ]
      },
      {
        "id": "0a3d1e11a59a5b21d3ce39ce9533b5db",
        "name": "Pain",
        "type": "Entity",
        "aliases": [
          "pain relief"
        ],
        "description": "Pain is an important entity, as it is the most common medical condition for which CBD is used.",
        "attributes": {
          "associated_with": "CBD-based analgesia"
        },
        "chunk_refs": [
          "17fdeb30ccdf930b61fcb9a12d61afa3"
        ]
      },
      {
        "id": "a61e2bb30224b4608a4e775baaa6e8a7",
        "name": "Study",
        "type": "Entity",
        "aliases": [
          "published survey"
        ],
        "description": "The study is a key entity, as it provides the context and results for the survey.",
        "attributes": {
          "first_of_its_kind": "true"
        },
        "chunk_refs": [
          "17fdeb30ccdf930b61fcb9a12d61afa3"
        ]
      },
      {
        "id": "1ce5d3720b29c473660cb0f3923abdce",
        "name": "Cannabinoid Research",
        "type": "Research Study",
        "aliases": [
          "annabinoid Research"
        ],
        "description": "A research study focused on cannabinoids, published in 2018.",
        "attributes": {
          "Year": "2018",
          "DOI": "10.1089/can.2018.0006"
        },
        "chunk_refs": [
          "bbf7733f06eb724713580b38c98ec864"
        ]
      },
      {
        "id": "dd5dfad0986c2dde8c7d7e616e85c85e",
        "name": "endocannabinoid system",
        "type": "Entity",
        "aliases": [],
        "description": "A biological system involved in regulating various physiological and cognitive processes.",
        "attributes": {
          "role": [
            "CBD-mediated analgesia",
            "pain modulation"
          ]
        },
        "chunk_refs": [
          "fdac444e60e75aca0ccda30488843c84"
        ]
      },
      {
        "id": "e86358e108220befb712c481c7427aba",
        "name": "pain",
        "type": "Entity",
        "aliases": [
          "chronic pain",
          "acute pain"
        ],
        "description": "A complex and multifaceted experience involving physical and emotional distress.",
        "attributes": {
          "models": [
            "murine models",
            "preclinical models"
          ]
        },
        "chunk_refs": [
          "fdac444e60e75aca0ccda30488843c84"
        ]
      },
      {
        "id": "250f08d314a5aee210ade38b37e6af62",
        "name": "anxiety",
        "type": "Entity",
        "aliases": [
          "THC-associated anxiety"
        ],
        "description": "A common mental health disorder characterized by feelings of worry, fear, and apprehension.",
        "attributes": {
          "reasons": [
            "CBD use"
          ]
        },
        "chunk_refs": [
          "fdac444e60e75aca0ccda30488843c84"
        ]
      },
      {
        "id": "e82c2a29363bf1e10402b5dc596ed57b",
        "name": "depression",
        "type": "Entity",
        "aliases": [],
        "description": "A serious mental health disorder characterized by persistent feelings of sadness, hopelessness, and loss of interest.",
        "attributes": {
          "reasons": [
            "CBD use"
          ]
        },
        "chunk_refs": [
          "fdac444e60e75aca0ccda30488843c84"
        ]
      },
      {
        "id": "4d1fbd6d8adb6e57a0aac25e3247fd93",
        "name": "THC",
        "type": "Chemical Compound",
        "aliases": [
          "Tetrahydrocannabinol"
        ],
        "description": "A psychoactive compound found in the cannabis plant, associated with anxiety.",
        "attributes": {
          "anxiety_association": "Yes"
        },
        "chunk_refs": [
          "9d1e450b9c308c261f7837f9a43aae24",
          "d1867014a49dc6d33d789ace285e7390",
          "f71f89736cc407d498719eb69377866f"
        ]
      },
      {
        "id": "48eb2426a4a5e268483a7b99fe5464ee",
        "name": "Cannabinoid Receptor",
        "type": "Biological Entity",
        "aliases": [
          "Receptor"
        ],
        "description": "A biological receptor that interacts with cannabinoids, including THC and CBD, to produce various physiological effects.",
        "attributes": {
          "activation": "Inhibited by CBD"
        },
        "chunk_refs": [
          "f71f89736cc407d498719eb69377866f"
        ]
      },
      {
        "id": "240517ffb4f78b24cc018e9bc754c30c",
        "name": "Serotonin 5-HT1A Receptor",
        "type": "Biological Entity",
        "aliases": [
          "5-HT1A"
        ],
        "description": "A subtype of serotonin receptor involved in anxiety regulation, targeted by CBD for its anxiolytic effects.",
        "attributes": {
          "anxiety_regulation": "Yes"
        },
        "chunk_refs": [
          "f71f89736cc407d498719eb69377866f"
        ]
      },
      {
        "id": "fca6c99e5e76d30b8e2699899c77dbcc",
        "name": "GABAA Receptor",
        "type": "Biological Entity",
        "aliases": [
          "GABA"
        ],
        "description": "A subtype of GABA receptor involved in anxiety regulation, targeted by CBD for its anxiolytic effects.",
        "attributes": {
          "anxiety_regulation": "Yes"
        },
        "chunk_refs": [
          "f71f89736cc407d498719eb69377866f"
        ]
      },
      {
        "id": "3d4c30453046a0ec162d2bdefaf845c7",
        "name": "Survey Respondents",
        "type": "Demographic",
        "aliases": [
          "Respondents"
        ],
        "description": "Individuals who participated in a survey, providing insights into their experiences and preferences regarding CBD use.",
        "attributes": {
          "learning_source": "Internet research, family members, or friends",
          "usage_frequency": "Daily or more than daily"
        },
        "chunk_refs": [
          "f71f89736cc407d498719eb69377866f"
        ]
      },
      {
        "id": "fee8be600b9f5bc1666451e88d12fbc4",
        "name": "Industry Survey",
        "type": "Research Study",
        "aliases": [
          "CBD Survey"
        ],
        "description": "A research study funded by the CBD industry, exploring CBD use patterns and preferences among customers of an online medical marijuana recommendation service.",
        "attributes": {
          "funding_source": "CBD industry",
          "participant_source": "Online medical marijuana recommendation service"
        },
        "chunk_refs": [
          "f71f89736cc407d498719eb69377866f"
        ]
      },
      {
        "id": "b855fa24d0ebf9afb2fc6e6c234f9f45",
        "name": "Cannabidiol",
        "type": "ENTITY",
        "aliases": [
          "CBD"
        ],
        "description": "Cannabidiol is a key component of marijuana-derived products, and its usage characteristics are crucial in understanding its effects on medical conditions.",
        "attributes": {
          "medical_condition": "Yes"
        },
        "chunk_refs": [
          "8b1a29f81847b8de655733132afdc7e8",
          "0c252c1114841dcef2babbca0f421465",
          "14ea1677d12ed444aa1fc42a6f356a29"
        ]
      },
      {
        "id": "5bb2f5fded20f6decdf21ecec8de5835",
        "name": "General Health",
        "type": "ENTITY",
        "aliases": [
          "General health"
        ],
        "description": "General health and well-being are closely tied to the usage of Cannabidiol, and respondents' perceptions of its effects are important.",
        "attributes": {
          "well-being": "related"
        },
        "chunk_refs": [
          "0c252c1114841dcef2babbca0f421465"
        ]
      },
      {
        "id": "46625c2c0d5f2ae118ec985fbfcb02d2",
        "name": "Cannabidiol Usage Characteristics",
        "type": "ENTITY",
        "aliases": [
          "Cannabidiol Usage Characteristics"
        ],
        "description": "Cannabidiol usage characteristics, such as frequency and duration of use, are crucial in understanding its effects on medical conditions.",
        "attributes": {
          "frequency": "varies",
          "duration_of_use": "varies"
        },
        "chunk_refs": [
          "0c252c1114841dcef2babbca0f421465"
        ]
      },
      {
        "id": "425f25052919357ff622f3cc4135d81a",
        "name": "Regular Cannabis Use",
        "type": "ENTITY",
        "aliases": [
          "Regular cannabis use"
        ],
        "description": "The frequent use of cannabis products, including cannabidiol, for medical or recreational purposes.",
        "attributes": {
          "related_to_cbd_use": "true"
        },
        "chunk_refs": [
          "8b1a29f81847b8de655733132afdc7e8"
        ]
      },
      {
        "id": "43acb59498aeb13678b81af6be31b1aa",
        "name": "Marijuana Users",
        "type": "ENTITY",
        "aliases": [
          "Cannabis users"
        ],
        "description": "Individuals who use marijuana, a key demographic in the context of CBD use.",
        "attributes": {
          "percentage_of_regular_use": "55.17%",
          "national_estimates": "8.3% (22.2 million people)"
        },
        "chunk_refs": [
          "e7015dfb7e48ef9f8d3b12d3cf366507"
        ]
      },
      {
        "id": "1bda830f840e0636ef219d624e393657",
        "name": "Survey Respondents",
        "type": "ENTITY",
        "aliases": [
          "respondents"
        ],
        "description": "Individuals who participated in the survey, providing insights into CBD use.",
        "attributes": {
          "percentage_of_regular_cannabis_use": "55.17%"
        },
        "chunk_refs": [
          "e7015dfb7e48ef9f8d3b12d3cf366507"
        ]
      },
      {
        "id": "7b003e13cb2ac3a02a62afc9f8e0172d",
        "name": "THC",
        "type": "ENTITY",
        "aliases": [],
        "description": "Tetrahydrocannabinol, a psychoactive compound in cannabis.",
        "attributes": {
          "perceived_legal_route_to_consumption": "Not used as a legal route to THC consumption"
        },
        "chunk_refs": [
          "e7015dfb7e48ef9f8d3b12d3cf366507"
        ]
      },
      {
        "id": "33107244c5ee8b387fa80552cbd370d5",
        "name": "Adverse Effects",
        "type": "Entity",
        "aliases": [
          "adverse effects",
          "Nonserious adverse effects"
        ],
        "description": "The unwanted consequences of using CBD, including dry mouth, sedation/fatigue, decreased appetite, and diarrhea.",
        "attributes": {
          "types": [
            "dry mouth",
            "sedation/fatigue",
            "decreased appetite",
            "diarrhea"
          ]
        },
        "chunk_refs": [
          "f9dc543f76c25659e7d883a263585f7c"
        ]
      },
      {
        "id": "c71b519b377bbffe061c66d99c467f03",
        "name": "Dose",
        "type": "Entity",
        "aliases": [
          "dose"
        ],
        "description": "The amount of CBD used, which may influence the occurrence of adverse effects.",
        "attributes": {
          "types": [
            "high-dose"
          ]
        },
        "chunk_refs": [
          "f9dc543f76c25659e7d883a263585f7c"
        ]
      },
      {
        "id": "efc125ed8ba298d9fc6782b1d1b7d7e3",
        "name": "Prescription Medications",
        "type": "Entity",
        "aliases": [
          "prescription medications"
        ],
        "description": "The medications that may interact with CBD, potentially leading to adverse effects.",
        "attributes": {
          "interaction_type": "adverse"
        },
        "chunk_refs": [
          "f9dc543f76c25659e7d883a263585f7c"
        ]
      },
      {
        "id": "3b944c9e01a9dce71b40f38b0dee7837",
        "name": "Survey",
        "type": "ENTITY",
        "aliases": [
          "Survey Respondents"
        ],
        "description": "A research study that collected data from 742 respondents to understand the adverse effects of cannabis.",
        "attributes": {
          "number_of_respondents": "742"
        },
        "chunk_refs": [
          "dd08513ddb7318829d671fa32dc2cf3f"
        ]
      },
      {
        "id": "8916ee83ae0bf2bbde2ffc4db85bda70",
        "name": "Adverse Effects",
        "type": "ENTITY",
        "aliases": [
          "Adverse effect",
          "Total adverse effects"
        ],
        "description": "Unwanted symptoms or reactions experienced by individuals after consuming cannabis.",
        "attributes": {
          "common_effects": [
            "Dry mouth",
            "Euphoria",
            "Hunger",
            "Red eyes",
            "Sleepy/groggy"
          ]
        },
        "chunk_refs": [
          "dd08513ddb7318829d671fa32dc2cf3f"
        ]
      },
      {
        "id": "d746dd7d06db44e480d9ba44852bedd9",
        "name": "General Health and Well-being",
        "type": "ENTITY",
        "aliases": [
          "well-being"
        ],
        "description": "A state of being healthy and happy, which may be influenced by cannabis use.",
        "attributes": {
          "number_of_cases": "926"
        },
        "chunk_refs": [
          "dd08513ddb7318829d671fa32dc2cf3f"
        ]
      },
      {
        "id": "afbb4b752bf2edfe6bdb24b38f234624",
        "name": "Study",
        "type": "Research",
        "aliases": [
          "analyses"
        ],
        "description": "A scientific investigation into the effects of CBD and THC, highlighting the importance of accurate labeling.",
        "attributes": {
          "findings": [
            "mislabeled products",
            "underlabeled products",
            "detectable THC levels"
          ]
        },
        "chunk_refs": [
          "9d1e450b9c308c261f7837f9a43aae24"
        ]
      },
      {
        "id": "56b0271ed6d3db35bcb0a0db669e3bd1",
        "name": "Users",
        "type": "Demographic",
        "aliases": [
          "consumers"
        ],
        "description": "Individuals who consume CBD products, often confused about the source and concentration of CBD.",
        "attributes": {
          "concerns": [
            "source of CBD",
            "concentration of CBD and other ingredients"
          ]
        },
        "chunk_refs": [
          "9d1e450b9c308c261f7837f9a43aae24"
        ]
      },
      {
        "id": "de8c3e8513b854afe3aecb60f7c6d4ba",
        "name": "products",
        "type": "Entity",
        "aliases": [
          "CBD-containing products"
        ],
        "description": "Unregulated products containing CBD, with unknown quantities and constituents.",
        "attributes": {
          "regulation_status": "unregulated"
        },
        "chunk_refs": [
          "3e0b5cdd3082797423f388409c351fbd"
        ]
      },
      {
        "id": "16d71dd49cca4a49be6263325f770ad7",
        "name": "users",
        "type": "Entity",
        "aliases": [
          "respondents",
          "Individuals"
        ],
        "description": "People using CBD products, with varying opinions and experiences.",
        "attributes": {
          "age_range": "wide"
        },
        "chunk_refs": [
          "3e0b5cdd3082797423f388409c351fbd"
        ]
      },
      {
        "id": "dd5337829767dd529d841b372e7fd646",
        "name": "study",
        "type": "Entity",
        "aliases": [
          "this study"
        ],
        "description": "A research study focused on CBD users, with strengths and limitations.",
        "attributes": {
          "strengths": [
            "size",
            "geographic representation",
            "wide age range",
            "specific usage characteristics"
          ],
          "limitations": [
            "self-selected convenience sample"
          ]
        },
        "chunk_refs": [
          "3e0b5cdd3082797423f388409c351fbd"
        ]
      },
      {
        "id": "afcba590101b7ec58025f441b00882ee",
        "name": "Survey",
        "type": "RESEARCH_METHOD",
        "aliases": [
          "questionnaire"
        ],
        "description": "A research tool used to collect data from respondents.",
        "attributes": {
          "medium": "internet",
          "limitations": "underrepresentation of CBD users with limited social media connectivity"
        },
        "chunk_refs": [
          "0c5c9994148ed73b472acdadfb7696f6"
        ]
      },
      {
        "id": "a4f57f9e95037811b330b17eea6e954e",
        "name": "Respondents",
        "type": "PARTICIPANT",
        "aliases": [
          "individuals"
        ],
        "description": "People who participated in the survey.",
        "attributes": {
          "characteristics": "may have distorted results"
        },
        "chunk_refs": [
          "0c5c9994148ed73b472acdadfb7696f6"
        ]
      },
      {
        "id": "e2834cf3a00cffd3e510f4fa60f45b2b",
        "name": "Healthcare Professionals",
        "type": "OCCUPATION",
        "aliases": [
          "healthcare professionals"
        ],
        "description": "Experts in the healthcare field.",
        "attributes": {
          "role": "not a primary source of information for CBD users"
        },
        "chunk_refs": [
          "0c5c9994148ed73b472acdadfb7696f6"
        ]
      },
      {
        "id": "8139283fdb66a2c7829f21c624426a5a",
        "name": "Medical Conditions",
        "type": "HEALTH_ISSUE",
        "aliases": [
          "health conditions",
          "inflammatory disorder"
        ],
        "description": "Various health problems that CBD is used to treat.",
        "attributes": {
          "examples": "pain, inflammatory disorder"
        },
        "chunk_refs": [
          "0c5c9994148ed73b472acdadfb7696f6"
        ]
      },
      {
        "id": "354a0b7241f41f8ef479fb985b31f798",
        "name": "Conventional Medicine",
        "type": "Entity",
        "aliases": [
          "traditional medicine"
        ],
        "description": "Mainstream medical practices and treatments.",
        "attributes": {
          "effectiveness for chronic pain": "limited",
          "side effects": "serious"
        },
        "chunk_refs": [
          "dc819420ff510d15bb4611c8e1e2e2e6"
        ]
      },
      {
        "id": "c5164ed3a3bc4ee4832e92ac93377e81",
        "name": "American Herbal Pharmacopia",
        "type": "ENTITY",
        "aliases": [],
        "description": "A publisher of a monograph on Cannabis in\ufb02orescence standards.",
        "attributes": {
          "location": "Scotts Valley, CA"
        },
        "chunk_refs": [
          "14ea1677d12ed444aa1fc42a6f356a29"
        ]
      },
      {
        "id": "a4e62124372b3094c7cf224edf6620d3",
        "name": "World Health Organization Expert Committee on Drug Dependence",
        "type": "ENTITY",
        "aliases": [],
        "description": "A committee reviewing Cannabidiol (CBD) for its potential therapeutic uses.",
        "attributes": {
          "report type": "Pre-Review Report"
        },
        "chunk_refs": [
          "14ea1677d12ed444aa1fc42a6f356a29"
        ]
      },
      {
        "id": "7b9a98b65d1fd87b66bfaafdb068b294",
        "name": "Devinsky O",
        "type": "ENTITY",
        "aliases": [],
        "description": "A researcher conducting an open-label interventional trial on Cannabidiol in patients with treatment-resistant epilepsy.",
        "attributes": {
          "study type": "open-label interventional trial"
        },
        "chunk_refs": [
          "14ea1677d12ed444aa1fc42a6f356a29"
        ]
      },
      {
        "id": "574b90d5bddfa56d7c812048c6a5cde4",
        "name": "Dravet Syndrome",
        "type": "Medical Condition",
        "aliases": [
          "pilepsy"
        ],
        "description": "A rare and severe form of epilepsy, characterized by frequent and prolonged seizures.",
        "attributes": {
          "symptoms": [
            "drug-resistant seizures"
          ]
        },
        "chunk_refs": [
          "135e9ae6c1bd0fd8ce998ed7f2781862"
        ]
      },
      {
        "id": "58ee22de99682c1856cc5df9f248ae53",
        "name": "Schizophrenia",
        "type": "Medical Condition",
        "aliases": [],
        "description": "A chronic and severe mental disorder, characterized by hallucinations, delusions, and disorganized thinking.",
        "attributes": {
          "symptoms": [
            "psychotic symptoms"
          ]
        },
        "chunk_refs": [
          "135e9ae6c1bd0fd8ce998ed7f2781862"
        ]
      },
      {
        "id": "df3d7f873674ea224dfab51613661772",
        "name": "Lancet Neurol",
        "type": "Academic Journal",
        "aliases": [],
        "description": "A peer-reviewed medical journal publishing original research and reviews on neurology and neuroscience.",
        "attributes": {
          "publication_year": [
            "2016"
          ]
        },
        "chunk_refs": [
          "135e9ae6c1bd0fd8ce998ed7f2781862"
        ]
      },
      {
        "id": "30b9445a06ad7f2b816eece1b34598af",
        "name": "Devinsky O",
        "type": "Researcher",
        "aliases": [],
        "description": "A researcher and author of a study on cannabidiol for drug-resistant seizures in Dravet syndrome.",
        "attributes": {
          "study_publication": [
            "N Engl J Med. 2017;376:2011\u20132020."
          ]
        },
        "chunk_refs": [
          "135e9ae6c1bd0fd8ce998ed7f2781862"
        ]
      },
      {
        "id": "cf2bf2d2614c15dd0fd4a10f48379296",
        "name": "Anxiety",
        "type": "Psychological Condition",
        "aliases": [
          "Social phobia",
          "Generalized social anxiety disorder"
        ],
        "description": "A psychological condition characterized by feelings of worry, nervousness, and fear.",
        "attributes": {
          "symptoms": "Fear of public speaking, nervousness, worry",
          "treatment": "Cannabidiol, anxiolytic-like effects"
        },
        "chunk_refs": [
          "fff700f33c96d074e1568b990992c9ac"
        ]
      },
      {
        "id": "01235f306a58938c061bcb3f03a8a778",
        "name": "Social Anxiety Disorder",
        "type": "Psychological Condition",
        "aliases": [
          "Social phobia"
        ],
        "description": "A psychological condition characterized by excessive fear of social or performance situations.",
        "attributes": {
          "symptoms": "Fear of public speaking, nervousness, worry",
          "treatment": "Cannabidiol, anxiolytic-like effects"
        },
        "chunk_refs": [
          "fff700f33c96d074e1568b990992c9ac"
        ]
      },
      {
        "id": "4fc0f7fcd2ce1be7377c78aba195ad14",
        "name": "Neuropsychopharmacology",
        "type": "Scientific Field",
        "aliases": [],
        "description": "A field of study that focuses on the effects of drugs on the nervous system and behavior.",
        "attributes": {
          "research_areas": "Cannabidiol, anxiolytic effects, anxiety treatment"
        },
        "chunk_refs": [
          "fff700f33c96d074e1568b990992c9ac"
        ]
      },
      {
        "id": "f6c487a37480f3431fab364441d4a1e3",
        "name": "Sativex",
        "type": "Medication",
        "aliases": [
          "Delta-9-tetrahydrocannabinol/cannabidiol oromucosal spray"
        ],
        "description": "A pharmaceutical product containing a combination of THC and CBD, used to treat multiple sclerosis-related spasticity.",
        "attributes": {
          "indication": "multiple sclerosis-related spasticity"
        },
        "chunk_refs": [
          "d1867014a49dc6d33d789ace285e7390"
        ]
      },
      {
        "id": "1ee8aa95571089b3f782ecd5691d01b2",
        "name": "Epilepsy",
        "type": "Medical Condition",
        "aliases": [
          "treatment-resistant epilepsy"
        ],
        "description": "A neurological disorder characterized by recurrent seizures.",
        "attributes": {
          "treatment options": "cannabinoids, CBD"
        },
        "chunk_refs": [
          "d1867014a49dc6d33d789ace285e7390"
        ]
      },
      {
        "id": "33221dce60dd5b43b4e387091e0e2204",
        "name": "Multiple Sclerosis",
        "type": "Medical Condition",
        "aliases": [
          "multiple sclerosis-related spasticity"
        ],
        "description": "A chronic autoimmune disease affecting the central nervous system.",
        "attributes": {
          "symptoms": "spasticity, pain"
        },
        "chunk_refs": [
          "d1867014a49dc6d33d789ace285e7390"
        ]
      },
      {
        "id": "84145963c903685f41f83b97e20fa32c",
        "name": "Cancer-Related Pain",
        "type": "Medical Condition",
        "aliases": [
          "intractable cancer-related pain"
        ],
        "description": "Chronic pain associated with cancer.",
        "attributes": {
          "treatment options": "THC:CBD extract, THC extract"
        },
        "chunk_refs": [
          "d1867014a49dc6d33d789ace285e7390"
        ]
      },
      {
        "id": "330f3ee92d4af50cf4de54bf710c0703",
        "name": "Cannabinoids",
        "type": "ENTITY",
        "aliases": [
          "cannabidiol"
        ],
        "description": "Plant-based pharmaceutical used for medical purposes",
        "attributes": {
          "medical_use": "treatment of Lennox\u2013Gastaut syndrome and Dravet syndrome"
        },
        "chunk_refs": [
          "e802d7202d123ac2f7a83544b007978b"
        ]
      },
      {
        "id": "4d1fb09186cd0bed7a4a7fc105ea4e07",
        "name": "GW Pharmaceuticals",
        "type": "ENTITY",
        "aliases": [
          "GW"
        ],
        "description": "Pharmaceutical company developing plant-based treatments",
        "attributes": {
          "subsidiary": "Greenwich Biosciences",
          "location": "U.S."
        },
        "chunk_refs": [
          "e802d7202d123ac2f7a83544b007978b"
        ]
      },
      {
        "id": "223e0a1e8fea5489a47e58bf41aebf95",
        "name": "Epidiolex",
        "type": "ENTITY",
        "aliases": [
          "cannabidiol"
        ],
        "description": "First plant-based pharmaceutical treatment for seizures",
        "attributes": {
          "treatment_for": "seizures in patients with Lennox\u2013Gastaut syndrome and Dravet syndrome"
        },
        "chunk_refs": [
          "e802d7202d123ac2f7a83544b007978b"
        ]
      },
      {
        "id": "eb0c7991481bd9beeef59e2bcf8dba4f",
        "name": "U.S. Food and Drug Administration",
        "type": "ENTITY",
        "aliases": [
          "FDA"
        ],
        "description": "Regulatory body for pharmaceutical approvals",
        "attributes": {
          "advisory_committee_meeting": "unanimous positive result"
        },
        "chunk_refs": [
          "e802d7202d123ac2f7a83544b007978b"
        ]
      },
      {
        "id": "8efe25615da7e28e81b5aa4db0b4c258",
        "name": "Lennox\u2013Gastaut syndrome",
        "type": "ENTITY",
        "aliases": [
          "rare, severe forms of epilepsy"
        ],
        "description": "Rare and severe form of epilepsy",
        "attributes": {
          "treatment": "Epidiolex"
        },
        "chunk_refs": [
          "e802d7202d123ac2f7a83544b007978b"
        ]
      },
      {
        "id": "29faae47e8b26b68b8fde945f1228e0a",
        "name": "Dravet syndrome",
        "type": "ENTITY",
        "aliases": [
          "rare, severe forms of epilepsy"
        ],
        "description": "Rare and severe form of epilepsy",
        "attributes": {
          "treatment": "Epidiolex"
        },
        "chunk_refs": [
          "e802d7202d123ac2f7a83544b007978b"
        ]
      },
      {
        "id": "2f47e40d64bed711c22f4cbb9ce38a2b",
        "name": "GW Pharmaceuticals",
        "type": "Company",
        "aliases": [
          "GW"
        ],
        "description": "GW Pharmaceuticals is a biopharmaceutical company that developed EPIDIOLEX, a plant-derived cannabinoid prescription medicine.",
        "attributes": {
          "industry": "Pharmaceuticals",
          "subsidiary": "Greenwich Biosciences"
        },
        "chunk_refs": [
          "0bf4cf8ef10cdcfe67c1b9ff9fd4baf4"
        ]
      },
      {
        "id": "bb0d43eeb1f4c17dd73970bb209b90f4",
        "name": "EPIDIOLEX",
        "type": "Medicine",
        "aliases": [
          "cannabidiol oral solution"
        ],
        "description": "EPIDIOLEX is a plant-derived cannabinoid prescription medicine developed by GW Pharmaceuticals for the treatment of certain medical conditions.",
        "attributes": {
          "active_ingredient": "cannabidiol",
          "formulation": "oral solution"
        },
        "chunk_refs": [
          "0bf4cf8ef10cdcfe67c1b9ff9fd4baf4"
        ]
      },
      {
        "id": "7917601f2f008540b21a27fea0f68ead",
        "name": "FDA",
        "type": "Government Agency",
        "aliases": [
          "Food and Drug Administration"
        ],
        "description": "The FDA is a government agency responsible for regulating and approving drugs, including EPIDIOLEX.",
        "attributes": {
          "jurisdiction": "United States"
        },
        "chunk_refs": [
          "0bf4cf8ef10cdcfe67c1b9ff9fd4baf4"
        ]
      },
      {
        "id": "186a569d87e8026fb84d73da86ae0e48",
        "name": "Drug Enforcement Agency",
        "type": "Organization",
        "aliases": [
          "DEA",
          "C. DEA"
        ],
        "description": "The primary agency responsible for enforcing drug laws in the United States.",
        "attributes": {
          "jurisdiction": "United States"
        },
        "chunk_refs": [
          "a7544fe505c7aa86aeabfd7ca46e5fe2",
          "6c1404cec40df041e6f0fddc750238ff"
        ]
      },
      {
        "id": "a4b1abd08bf61197cfe94a8ab12fb4ac",
        "name": "Cannabidiol",
        "type": "Substance",
        "aliases": [
          "CBD"
        ],
        "description": "A non-psychoactive compound found in the Cannabis plant.",
        "attributes": {
          "legal_status": "Illegal according to DEA"
        },
        "chunk_refs": [
          "a7544fe505c7aa86aeabfd7ca46e5fe2",
          "6c1404cec40df041e6f0fddc750238ff",
          "ddd9357949ed40371465425bececbc1c"
        ]
      },
      {
        "id": "4ad010cc9960b94e07da719dc39c6658",
        "name": "Marihuana Extract",
        "type": "Substance",
        "aliases": [],
        "description": "A substance derived from the Cannabis plant.",
        "attributes": {
          "related_to": "Cannabidiol"
        },
        "chunk_refs": [
          "a7544fe505c7aa86aeabfd7ca46e5fe2"
        ]
      },
      {
        "id": "a5930aceeea9d8ea93262ad5a8a0e220",
        "name": "United States Congress",
        "type": "Organization",
        "aliases": [
          "Congress"
        ],
        "description": "The legislative branch of the United States government.",
        "attributes": {
          "jurisdiction": "United States"
        },
        "chunk_refs": [
          "a7544fe505c7aa86aeabfd7ca46e5fe2"
        ]
      },
      {
        "id": "0dd69ebb83df5c5855f60a605f9bae1d",
        "name": "Agricultural Act of 2014",
        "type": "Legislation",
        "aliases": [
          "Public Law 79"
        ],
        "description": "A federal law enacted by the United States Congress.",
        "attributes": {
          "year": "2014"
        },
        "chunk_refs": [
          "a7544fe505c7aa86aeabfd7ca46e5fe2"
        ]
      },
      {
        "id": "f9ad848701841e9d808654fabdad095c",
        "name": "Comprehensive Drug Abuse Prevention and Control Act of 1970",
        "type": "Legislation",
        "aliases": [
          "Public Law 513"
        ],
        "description": "A federal law enacted by the United States Congress.",
        "attributes": {
          "year": "1970"
        },
        "chunk_refs": [
          "a7544fe505c7aa86aeabfd7ca46e5fe2"
        ]
      },
      {
        "id": "96b499466313455f28c5c9c71a44b513",
        "name": "United States Court of Appeals for the Ninth Circuit",
        "type": "Organization",
        "aliases": [
          "Ninth Circuit"
        ],
        "description": "A federal court with jurisdiction over appeals from district courts in the western United States.",
        "attributes": {
          "location": "San Francisco, CA"
        },
        "chunk_refs": [
          "6c1404cec40df041e6f0fddc750238ff"
        ]
      },
      {
        "id": "e2ab0c2d3e22334998c8a725311b351b",
        "name": "Marijuana Extract",
        "type": "Substance",
        "aliases": [
          "Cannabis Extract"
        ],
        "description": "A substance derived from the cannabis plant, containing cannabinoids and terpenes.",
        "attributes": {
          "schedule": "Schedule I"
        },
        "chunk_refs": [
          "6c1404cec40df041e6f0fddc750238ff"
        ]
      },
      {
        "id": "f49597595ce4c742f4f109345766de11",
        "name": "Food and Drug Administration",
        "type": "Organization",
        "aliases": [
          "FDA"
        ],
        "description": "A government agency responsible for protecting and promoting public health through the regulation of food, drugs, and other products.",
        "attributes": {
          "jurisdiction": "United States"
        },
        "chunk_refs": [
          "6c1404cec40df041e6f0fddc750238ff",
          "ddd9357949ed40371465425bececbc1c"
        ]
      },
      {
        "id": "ec98402314d3b356d26f72674f728516",
        "name": "Industrial Hemp",
        "type": "Substance",
        "aliases": [
          "Hemp"
        ],
        "description": "A variety of the cannabis plant, cultivated for its seeds, stalks, and leaves, with low THC content.",
        "attributes": {
          "uses": [
            "CBD production"
          ]
        },
        "chunk_refs": [
          "6c1404cec40df041e6f0fddc750238ff"
        ]
      },
      {
        "id": "20ec01f1935a20f90f4b921c9a2c7bba",
        "name": "Cannabis Law",
        "type": "Legislation",
        "aliases": [
          "Marijuana Law"
        ],
        "description": "A set of laws and regulations governing the use, possession, and distribution of cannabis and its derivatives.",
        "attributes": {
          "jurisdiction": "United States"
        },
        "chunk_refs": [
          "6c1404cec40df041e6f0fddc750238ff"
        ]
      },
      {
        "id": "acd26fe9826ed6981fda4cc7092a43f6",
        "name": "Macrophage",
        "type": "Cell Type",
        "aliases": [],
        "description": "A type of immune cell involved in inflammation and studied for its response to Tetrahydrocannabinol.",
        "attributes": {
          "function": "phagocytosis"
        },
        "chunk_refs": [
          "527c0f3809acba8d4d487efffcdd1079"
        ]
      },
      {
        "id": "36a592f8ccc903653d49cab513b354f9",
        "name": "Nitric oxide",
        "type": "Molecule",
        "aliases": [],
        "description": "A molecule involved in inflammation and studied for its production in response to Tetrahydrocannabinol.",
        "attributes": {
          "formula": "NO"
        },
        "chunk_refs": [
          "527c0f3809acba8d4d487efffcdd1079"
        ]
      },
      {
        "id": "405fee22b47d100158d476964b7a710f",
        "name": "Inflammation",
        "type": "Biological Process",
        "aliases": [],
        "description": "A biological response studied in the context of Cannabis sativa compounds and their therapeutic effects.",
        "attributes": {
          "type": "acute/chronic"
        },
        "chunk_refs": [
          "527c0f3809acba8d4d487efffcdd1079",
          "a3fe9298a663e7d36c66f6fd6e8350a8",
          "5ced33b136bf979de23a9f198f5d171d"
        ]
      },
      {
        "id": "47d608461357e567dcb0cee49e279b79",
        "name": "Cannabis",
        "type": "Plant",
        "aliases": [
          "cannabis"
        ],
        "description": "A plant with potential therapeutic properties.",
        "attributes": {
          "therapeutic_properties": "anti-inflammatory, anti-autoimmune"
        },
        "chunk_refs": [
          "1716edf8e0575017a4b1228820b78beb",
          "a3fe9298a663e7d36c66f6fd6e8350a8",
          "ddd9357949ed40371465425bececbc1c"
        ]
      },
      {
        "id": "16cef93096e44b1ef3747b3dc672a8cb",
        "name": "Diabetes",
        "type": "Disease",
        "aliases": [
          "diabetes",
          "autoimmune diabetes"
        ],
        "description": "A metabolic disorder characterized by high blood sugar levels.",
        "attributes": {
          "type": "autoimmune"
        },
        "chunk_refs": [
          "1716edf8e0575017a4b1228820b78beb"
        ]
      },
      {
        "id": "2984edd3371f8bae42dfd5e0460ed363",
        "name": "Adenosine A2A receptor",
        "type": "Protein",
        "aliases": [
          "adenosine A2A receptor"
        ],
        "description": "A protein involved in inflammatory responses.",
        "attributes": {
          "function": "inflammatory response"
        },
        "chunk_refs": [
          "1716edf8e0575017a4b1228820b78beb"
        ]
      },
      {
        "id": "c277d8749c5c8d89f6db8e4e92dc428b",
        "name": "cAMP",
        "type": "Molecule",
        "aliases": [
          "cyclic adenosine monophosphate"
        ],
        "description": "A potent inhibitor of the NF-kappa B pathway.",
        "attributes": {
          "function": "inhibitor"
        },
        "chunk_refs": [
          "5ced33b136bf979de23a9f198f5d171d"
        ]
      },
      {
        "id": "cfaf1255abe5cf40ce5e545bb4b116c4",
        "name": "NF-kappa B pathway",
        "type": "Biological Pathway",
        "aliases": [
          "NF-\u03baB pathway"
        ],
        "description": "A key pathway involved in inflammation and immune responses.",
        "attributes": {
          "function": "regulation of inflammation"
        },
        "chunk_refs": [
          "5ced33b136bf979de23a9f198f5d171d"
        ]
      },
      {
        "id": "a53ba12ca4a28da5a67fad18d439bff5",
        "name": "A2A adenosine receptor",
        "type": "Protein",
        "aliases": [
          "A2A receptor"
        ],
        "description": "A receptor involved in regulating inflammation.",
        "attributes": {
          "function": "regulation of inflammation"
        },
        "chunk_refs": [
          "5ced33b136bf979de23a9f198f5d171d"
        ]
      },
      {
        "id": "36c0b95679ae555a5ba50224e36f0289",
        "name": "Glycine",
        "type": "Amino Acid",
        "aliases": [
          "Gly"
        ],
        "description": "A simple physiological compound with protective effects against ischaemia-reperfusion injury.",
        "attributes": {
          "function": "protective effects"
        },
        "chunk_refs": [
          "5ced33b136bf979de23a9f198f5d171d"
        ]
      },
      {
        "id": "be5e5f1173c01ce1bffdf2280d8ebdd5",
        "name": "TRPV1",
        "type": "Protein",
        "aliases": [
          "Transient receptor potential vanilloid 1"
        ],
        "description": "A receptor involved in regulating inflammation.",
        "attributes": {
          "function": "regulation of inflammation"
        },
        "chunk_refs": [
          "5ced33b136bf979de23a9f198f5d171d"
        ]
      },
      {
        "id": "2b0e05bf8d4e36249615a04cec9d8dc4",
        "name": "Clozapine",
        "type": "Medication",
        "aliases": [
          "CLZ"
        ],
        "description": "An antipsychotic medication used to treat schizophrenia and other mental health conditions.",
        "attributes": {
          "therapeutic_effects": "reverses MK-801-induced deficits in social interaction and hyperactivity"
        },
        "chunk_refs": [
          "a3fe9298a663e7d36c66f6fd6e8350a8"
        ]
      },
      {
        "id": "b4802a7447acd2093133f67ff8e0a312",
        "name": "Social Interaction",
        "type": "Behavioral Trait",
        "aliases": [
          "social behavior"
        ],
        "description": "The ability to interact and communicate with others in a socially acceptable manner.",
        "attributes": {
          "deficits": "reversed by Cannabidiol and Clozapine"
        },
        "chunk_refs": [
          "a3fe9298a663e7d36c66f6fd6e8350a8"
        ]
      },
      {
        "id": "0f36a7fc0c4a8847a915e51ae6b4aacf",
        "name": "Hyperactivity",
        "type": "Behavioral Trait",
        "aliases": [
          "hyperactive behavior"
        ],
        "description": "A state of excessive physical or mental activity, often associated with attention deficit hyperactivity disorder (ADHD).",
        "attributes": {
          "deficits": "reversed by Cannabidiol and Clozapine"
        },
        "chunk_refs": [
          "a3fe9298a663e7d36c66f6fd6e8350a8"
        ]
      },
      {
        "id": "1c3942fd4afbe352f0e33a9fb05ab1e2",
        "name": "Sprague-Dawley Rats",
        "type": "Animal Model",
        "aliases": [
          "SD Rats"
        ],
        "description": "A strain of laboratory rats commonly used in scientific research, particularly in the fields of psychology and pharmacology.",
        "attributes": {
          "model_for": "social interaction and hyperactivity studies"
        },
        "chunk_refs": [
          "a3fe9298a663e7d36c66f6fd6e8350a8"
        ]
      },
      {
        "id": "0aeb6d004aac3b76529a3ae49354d63f",
        "name": "Vagus nerve stimulation",
        "type": "Entity",
        "aliases": [
          "VNS"
        ],
        "description": "A therapeutic technique that has been shown to attenuate the systemic inflammatory response to endotoxin.",
        "attributes": {
          "Effect on inflammation": "attenuates"
        },
        "chunk_refs": [
          "14a605842b2ab436fa7988e3eb1296ee"
        ]
      },
      {
        "id": "e788087fa6f1797953fb00affacbcefc",
        "name": "Inflammation",
        "type": "Entity",
        "aliases": [
          "inflammatory response"
        ],
        "description": "A complex biological response to harmful stimuli, which can be attenuated by vagus nerve stimulation.",
        "attributes": {
          "Type": "systemic"
        },
        "chunk_refs": [
          "14a605842b2ab436fa7988e3eb1296ee"
        ]
      },
      {
        "id": "26e8ebf2ef91755162802ef292a58fd4",
        "name": "Endotoxin",
        "type": "Entity",
        "aliases": [
          "LPS"
        ],
        "description": "A molecule that can trigger an inflammatory response, which can be attenuated by vagus nerve stimulation.",
        "attributes": {
          "Effect on body": "triggers inflammation"
        },
        "chunk_refs": [
          "14a605842b2ab436fa7988e3eb1296ee"
        ]
      },
      {
        "id": "445c719cf6f8c694768393a6f84d52c9",
        "name": "Cannabinoids",
        "type": "Entity",
        "aliases": [
          "endocannabinoids",
          "analogs"
        ],
        "description": "A class of compounds that have been shown to have anti-inflammatory effects.",
        "attributes": {
          "Effect on inflammation": "anti-inflammatory"
        },
        "chunk_refs": [
          "14a605842b2ab436fa7988e3eb1296ee"
        ]
      },
      {
        "id": "8b3092cce15866ed52d248d10f238c55",
        "name": "Endocannabinoid hydrolysis inhibitor",
        "type": "Entity",
        "aliases": [
          "SA-57"
        ],
        "description": "A compound that has been shown to have intrinsic antinociceptive effects and can augment morphine-induced antinociception.",
        "attributes": {
          "Effect on pain": "antinociceptive"
        },
        "chunk_refs": [
          "14a605842b2ab436fa7988e3eb1296ee"
        ]
      },
      {
        "id": "44a42552a75a5823d14a85f507ef05c3",
        "name": "Heroin",
        "type": "Entity",
        "aliases": [
          "opioid"
        ],
        "description": "A drug that can lead to seeking behavior, which can be attenuated by the endocannabinoid hydrolysis inhibitor SA-57.",
        "attributes": {
          "Effect on behavior": "seeking behavior"
        },
        "chunk_refs": [
          "14a605842b2ab436fa7988e3eb1296ee"
        ]
      },
      {
        "id": "f69c8b8cd2e1b654312b9bcf8eb83652",
        "name": "Delta-9-Tetrahydrocannabinol",
        "type": "Chemical Compound",
        "aliases": [
          "delta-9-tetrahydrocannabinol",
          "THC"
        ],
        "description": "A psychoactive compound found in the cannabis plant, known for its intoxicating effects.",
        "attributes": {
          "interactions": [
            "cannabidiol"
          ]
        },
        "chunk_refs": [
          "d8e7370962a1001898cf1e1cd9d2294e"
        ]
      },
      {
        "id": "d2778d127147de95c2dc48d46076edf1",
        "name": "GABAA Receptors",
        "type": "Biological Entity",
        "aliases": [
          "GABA receptors"
        ],
        "description": "A type of receptor in the brain that plays a crucial role in regulating various physiological processes.",
        "attributes": {
          "actions": [
            "direct actions of cannabidiol"
          ]
        },
        "chunk_refs": [
          "d8e7370962a1001898cf1e1cd9d2294e"
        ]
      },
      {
        "id": "bd09c70169651b00b1ae3ac5594569a2",
        "name": "Emotion",
        "type": "Psychological Concept",
        "aliases": [
          "emotional memory"
        ],
        "description": "A complex psychological and physiological state that plays a vital role in human behavior and well-being.",
        "attributes": {
          "regulation": [
            "cannabidiol regulation"
          ]
        },
        "chunk_refs": [
          "d8e7370962a1001898cf1e1cd9d2294e"
        ]
      },
      {
        "id": "cf0690b2a63f3aa2a2bd9123757800fe",
        "name": "Anxiety-Related Disorders",
        "type": "Medical Condition",
        "aliases": [
          "anxiety-related disorders",
          "substance abuse disorders"
        ],
        "description": "A range of mental health disorders characterized by excessive fear, anxiety, or avoidance behaviors.",
        "attributes": {
          "treatment": [
            "cannabidiol"
          ]
        },
        "chunk_refs": [
          "d8e7370962a1001898cf1e1cd9d2294e"
        ]
      },
      {
        "id": "a0e6a3b0b509392674ffd8d58a2c862e",
        "name": "Cannabidiol",
        "type": "Drug",
        "aliases": [
          "CBD"
        ],
        "description": "A non-psychoactive cannabinoid with potential therapeutic effects.",
        "attributes": {
          "effects": "antipsychotic",
          "study_type": "translational investigation"
        },
        "chunk_refs": [
          "337a320bea52098f16b9783800ca95c9"
        ]
      },
      {
        "id": "63112860ce850633ea103649df228c9c",
        "name": "Medical Cannabis Users",
        "type": "Demographic",
        "aliases": [
          "cannabis users"
        ],
        "description": "Individuals who use cannabis for medical purposes.",
        "attributes": {
          "study_type": "cross-sectional survey",
          "perceived_efficacy": "medical use"
        },
        "chunk_refs": [
          "337a320bea52098f16b9783800ca95c9"
        ]
      },
      {
        "id": "cdf1a90bf727b190bac99c9e4093851b",
        "name": "National Survey on Drug Use and Health",
        "type": "Survey",
        "aliases": [
          "NSDUH"
        ],
        "description": "A national survey conducted by the US Department of Health and Human Services.",
        "attributes": {
          "year": "2015",
          "publication_no": "SMA 16-4984"
        },
        "chunk_refs": [
          "337a320bea52098f16b9783800ca95c9"
        ]
      },
      {
        "id": "560f041fe68c7e6f724f5e36134dd95f",
        "name": "Center for Behavioral Health Statistics and Quality",
        "type": "Organization",
        "aliases": [
          "Center"
        ],
        "description": "A US government organization responsible for behavioral health statistics and quality.",
        "attributes": {
          "publication_no": "SMA 16-4984"
        },
        "chunk_refs": [
          "337a320bea52098f16b9783800ca95c9"
        ]
      },
      {
        "id": "23e64780cba821c6279a8e4726189f71",
        "name": "Cannabis",
        "type": "Substance",
        "aliases": [
          "Cannabis Canna-"
        ],
        "description": "A plant-based substance with psychoactive and non-psychoactive compounds.",
        "attributes": {
          "compound": "cannabinoid"
        },
        "chunk_refs": [
          "337a320bea52098f16b9783800ca95c9"
        ]
      },
      {
        "id": "ebe7d213a70e825d079ed976b8c5f0a3",
        "name": "Cannabinoid Research",
        "type": "Journal",
        "aliases": [
          "Cannabis and Cannabinoid Research"
        ],
        "description": "A journal publishing research on cannabinoids, including cannabidiol.",
        "attributes": {
          "publishing features": [
            "immediate online access",
            "rigorous peer review",
            "compliance with open access mandates",
            "authors retain copyright",
            "highly indexed",
            "targeted email marketing"
          ]
        },
        "chunk_refs": [
          "0767cadfa559f2d7cc86b3525fb11250",
          "ddd9357949ed40371465425bececbc1c"
        ]
      },
      {
        "id": "ad215225995a4d154c7c36039e7de554",
        "name": "Corroon J",
        "type": "Author",
        "aliases": [
          "Corroon"
        ],
        "description": "Author of a study on cannabidiol users.",
        "attributes": {},
        "chunk_refs": [
          "ddd9357949ed40371465425bececbc1c"
        ]
      },
      {
        "id": "8a8ab60aebbca9151db7e09e7cde1274",
        "name": "Phillips JA",
        "type": "Author",
        "aliases": [
          "Phillips"
        ],
        "description": "Author of a study on cannabidiol users.",
        "attributes": {},
        "chunk_refs": [
          "ddd9357949ed40371465425bececbc1c"
        ]
      }
    ],
    "relationships": [
      {
        "id": "ebf15288ddc24d45f6692ad948bf74ab",
        "source_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "target_id": "7f6895ff3db6d325cb8ea0a2d121ad64",
        "types": [
          "USES"
        ],
        "strength": 0.8,
        "description": "Cannabidiol users consume cannabidiol products.",
        "chunk_refs": [
          "06c33232865b0a4e730522561c5aa2bc"
        ]
      },
      {
        "id": "529826245a348f1bd7f43325276cc85e",
        "source_id": "ad55f8d7c392c163d1b19494b50e1729",
        "target_id": "7f6895ff3db6d325cb8ea0a2d121ad64",
        "types": [
          "STUDY_SUBJECT"
        ],
        "strength": 0.9,
        "description": "The cross-sectional study examines the characteristics of cannabidiol users.",
        "chunk_refs": [
          "06c33232865b0a4e730522561c5aa2bc"
        ]
      },
      {
        "id": "a07f54cd5e61420eadc4002c5d2417d0",
        "source_id": "cfac4980cd10e31753b142a706920440",
        "target_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "types": [
          "CLASSIFIES"
        ],
        "strength": 0.7,
        "description": "The U.S. Drug Enforcement Administration classifies cannabidiol as a Schedule I controlled substance.",
        "chunk_refs": [
          "06c33232865b0a4e730522561c5aa2bc"
        ]
      },
      {
        "id": "847d3839def0999ba62816893235926e",
        "source_id": "75a0ee3665b474dcda1287014f0387ee",
        "target_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "types": [
          "REGULATES"
        ],
        "strength": 0.6,
        "description": "The U.S. Food and Drug Administration regulates cannabidiol as a non-dietary supplement ingredient.",
        "chunk_refs": [
          "06c33232865b0a4e730522561c5aa2bc",
          "434f4f7a509cc817c213d724c5121179"
        ]
      },
      {
        "id": "8f6bd20a347c60c78b8f79dac70ff244",
        "source_id": "fa5f7aaefcf6032635ed725d9f8ad6e0",
        "target_id": "ad55f8d7c392c163d1b19494b50e1729",
        "types": [
          "RESEARCH_METHOD"
        ],
        "strength": 0.8,
        "description": "The online survey is a research method used in the cross-sectional study.",
        "chunk_refs": [
          "06c33232865b0a4e730522561c5aa2bc"
        ]
      },
      {
        "id": "1d32d2f7db14fe7e604ccee37e1e049f",
        "source_id": "5f39aa2e03c2d02af57ddb9c581eeaa2",
        "target_id": "3609aa0c27d6d33db45a3f9fe0ec89dd",
        "types": [
          "treats"
        ],
        "strength": 0.8,
        "description": "CBD is being used to treat various medical conditions, including pain, anxiety, depression, and sleep disorders.",
        "chunk_refs": [
          "7e8a191787570c4f45f67384be57ba29",
          "b782e359c27dbde3a3084a4fae577a09",
          "17fdeb30ccdf930b61fcb9a12d61afa3",
          "dc819420ff510d15bb4611c8e1e2e2e6"
        ]
      },
      {
        "id": "1cc41bf6b89a35d615b653a1ad8b2b5a",
        "source_id": "0e86c574a6bdd0b6668d0d3f88887434",
        "target_id": "5f39aa2e03c2d02af57ddb9c581eeaa2",
        "types": [
          "uses"
        ],
        "strength": 0.9,
        "description": "A significant proportion of consumers are using CBD to treat medical conditions, with many reporting positive results.",
        "chunk_refs": [
          "7e8a191787570c4f45f67384be57ba29"
        ]
      },
      {
        "id": "58de98126ffd736ee97a2767efac620a",
        "source_id": "8963c8182d0dd21bf0073007eac2f3c1",
        "target_id": "5f39aa2e03c2d02af57ddb9c581eeaa2",
        "types": [
          "derivative"
        ],
        "strength": 0.7,
        "description": "CBD is derived from the Cannabis plant, and its usage patterns vary among regular and non-regular users.",
        "chunk_refs": [
          "7e8a191787570c4f45f67384be57ba29",
          "3e0b5cdd3082797423f388409c351fbd"
        ]
      },
      {
        "id": "dcc5a9bc0394c3356b33b56ff6eab847",
        "source_id": "5a2013e3e31b464d3d9773b937f6da37",
        "target_id": "5f39aa2e03c2d02af57ddb9c581eeaa2",
        "types": [
          "investigates"
        ],
        "strength": 0.9,
        "description": "Further research is necessary to better understand the therapeutic potential of CBD and its effects on various medical conditions.",
        "chunk_refs": [
          "7e8a191787570c4f45f67384be57ba29",
          "dc819420ff510d15bb4611c8e1e2e2e6"
        ]
      },
      {
        "id": "acd531cc6f21d6c2b95111706b9295a8",
        "source_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "target_id": "4dab2eba3497c621ad5ddab69a2e14e8",
        "types": [
          "found in"
        ],
        "strength": 0.8,
        "description": "Cannabidiol is a cannabinoid found in Cannabis sativa L.",
        "chunk_refs": [
          "434f4f7a509cc817c213d724c5121179"
        ]
      },
      {
        "id": "48b6a0cd034931a47eeed7796093a691",
        "source_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "target_id": "8cffefdfcd28ebd6b421f89fa72173ca",
        "types": [
          "co-occurring"
        ],
        "strength": 0.6,
        "description": "Cannabidiol and Tetrahydrocannabinol are both cannabinoids found in Cannabis sativa L.",
        "chunk_refs": [
          "434f4f7a509cc817c213d724c5121179"
        ]
      },
      {
        "id": "4342dc6f07442346904070dcbf6d60a5",
        "source_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "target_id": "b98e0837815ab77e51e1bef5719e080c",
        "types": [
          "treats"
        ],
        "strength": 0.9,
        "description": "Cannabidiol has shown potential therapeutic efficacy against various medical conditions.",
        "chunk_refs": [
          "434f4f7a509cc817c213d724c5121179"
        ]
      },
      {
        "id": "447b53735ca3d6c666c60bca58313737",
        "source_id": "60e12faf5ad9c245816e5a625b4a0bde",
        "target_id": "0c4de6be81918a873c9c419592e5509f",
        "types": [
          "approval"
        ],
        "strength": 1.0,
        "description": "The FDA approved Epidiolex as a drug for the treatment of pediatric seizure disorders.",
        "chunk_refs": [
          "3c83f56c2f5f40be06649e1dfc000bc7"
        ]
      },
      {
        "id": "a40275479e79ddb7d516179e700c9c40",
        "source_id": "0c4de6be81918a873c9c419592e5509f",
        "target_id": "ae85d731c7ee2616fdf34d8edd6addce",
        "types": [
          "composition"
        ],
        "strength": 1.0,
        "description": "Epidiolex is a plant-derived Cannabis compound containing CBD.",
        "chunk_refs": [
          "3c83f56c2f5f40be06649e1dfc000bc7"
        ]
      },
      {
        "id": "73cdc2bdfa9028e6d5ad741f0ce69127",
        "source_id": "0c4de6be81918a873c9c419592e5509f",
        "target_id": "a16aed7a6e86ac4fc5884c50b2eadb13",
        "types": [
          "treatment"
        ],
        "strength": 1.0,
        "description": "Epidiolex is used to treat pediatric seizure disorders.",
        "chunk_refs": [
          "3c83f56c2f5f40be06649e1dfc000bc7"
        ]
      },
      {
        "id": "5cc2d73910f6d513f030f352f2e7caad",
        "source_id": "4668196353afbe5540abe5fc5c579fc6",
        "target_id": "0c4de6be81918a873c9c419592e5509f",
        "types": [
          "regulation"
        ],
        "strength": 0.8,
        "description": "The DEA regulates Epidiolex as a controlled substance.",
        "chunk_refs": [
          "3c83f56c2f5f40be06649e1dfc000bc7"
        ]
      },
      {
        "id": "6ca3ac24b519a906232fe285f802d630",
        "source_id": "42f3adee1e368c03018a625408ca098a",
        "target_id": "a661910ec6e666b2f6c361008c1ae236",
        "types": [
          "TOPIC_OF_RESEARCH"
        ],
        "strength": 0.8,
        "description": "Cannabis is the primary topic of research in Cannabinoid Research.",
        "chunk_refs": [
          "f73165fbd7717b37de537750ca3ef2c8",
          "7975dd7cb686c5fc94fbed8018693cc9",
          "00c25bd0a0c202d272a9a038440caea2"
        ]
      },
      {
        "id": "1335d9c2eb1d136ecaed3ef68404f187",
        "source_id": "a661910ec6e666b2f6c361008c1ae236",
        "target_id": "61084b6195b088f4158b1c6f6b909ae0",
        "types": [
          "PERMITTED_UNDER"
        ],
        "strength": 0.7,
        "description": "Cannabinoid Research is permitted for distribution under the Creative Commons Attribution License.",
        "chunk_refs": [
          "f73165fbd7717b37de537750ca3ef2c8"
        ]
      },
      {
        "id": "3495c3bc511846dd266469cad05c2810",
        "source_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "target_id": "93ff93556b30583162232d212ad93928",
        "types": [
          "Component"
        ],
        "strength": 0.8,
        "description": "Cannabidiol is a component of nabiximols (Sativex).",
        "chunk_refs": [
          "6df50e78b082ac5d95692b2e6a1192b0"
        ]
      },
      {
        "id": "97d449334592ddb7d1edcca0c92f99e6",
        "source_id": "93ff93556b30583162232d212ad93928",
        "target_id": "561d1b1307fa9ab46a66597a58346648",
        "types": [
          "Treatment"
        ],
        "strength": 0.9,
        "description": "Nabiximols (Sativex) is approved to treat spasticity due to multiple sclerosis.",
        "chunk_refs": [
          "6df50e78b082ac5d95692b2e6a1192b0"
        ]
      },
      {
        "id": "e73403e49be21bef706fd5548cc0392c",
        "source_id": "aa4812e81e63eaa262314ddf4ca9ab6b",
        "target_id": "93ff93556b30583162232d212ad93928",
        "types": [
          "Approval"
        ],
        "strength": 0.7,
        "description": "Nabiximols (Sativex) is not approved in the United States.",
        "chunk_refs": [
          "6df50e78b082ac5d95692b2e6a1192b0"
        ]
      },
      {
        "id": "1562a8a4b9b26dba103d5211dd847701",
        "source_id": "71a3695466a233c43c6d03936330adbd",
        "target_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "types": [
          "Legality"
        ],
        "strength": 0.8,
        "description": "Individual European Union member states determine the legality of CBD.",
        "chunk_refs": [
          "6df50e78b082ac5d95692b2e6a1192b0"
        ]
      },
      {
        "id": "69ecce024d0aff9cc50844d5d108f275",
        "source_id": "9761f234f3d2b3a3ccc1e2b7d888e5ab",
        "target_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "types": [
          "Recommendation"
        ],
        "strength": 0.6,
        "description": "The World Health Organization's Expert Committee on Drug Dependence recommends.",
        "chunk_refs": [
          "6df50e78b082ac5d95692b2e6a1192b0"
        ]
      },
      {
        "id": "8d35568c1291ce32f41b1c3f26f9148f",
        "source_id": "64154fe0ef7a56f70668c352ea0d0383",
        "target_id": "0138ded66cd80350ada4523db0b67652",
        "types": [
          "part_of"
        ],
        "strength": 0.8,
        "description": "CBD is a compound found in the Cannabis sativa plant.",
        "chunk_refs": [
          "1ccf2014205c26d63543890dd419d2b8"
        ]
      },
      {
        "id": "d7644a3bcd306086fabeaecc08d9b563",
        "source_id": "e6d154e8ce36a036ce43fbfefc907f44",
        "target_id": "64154fe0ef7a56f70668c352ea0d0383",
        "types": [
          "regulates"
        ],
        "strength": 0.7,
        "description": "The UN Single Convention recommends the scheduling of CBD.",
        "chunk_refs": [
          "1ccf2014205c26d63543890dd419d2b8"
        ]
      },
      {
        "id": "3c94a0bf16eb196f3b137197d9b6016d",
        "source_id": "51b3eeb20a301035500441f919539ceb",
        "target_id": "64154fe0ef7a56f70668c352ea0d0383",
        "types": [
          "regulates"
        ],
        "strength": 0.6,
        "description": "The DEA enforces controlled substances laws, including those related to CBD.",
        "chunk_refs": [
          "1ccf2014205c26d63543890dd419d2b8",
          "e317b24947911f93f17fb3b1a68af31a"
        ]
      },
      {
        "id": "9289fee9cdf135ce62bcda9dc6109e71",
        "source_id": "e659708baa7652120dd937268c3a2abd",
        "target_id": "9a469c73620bfb9b1a543cff64b339ed",
        "types": [
          "regulates"
        ],
        "strength": 0.9,
        "description": "The Farm Act regulates the production of industrial hemp.",
        "chunk_refs": [
          "1ccf2014205c26d63543890dd419d2b8"
        ]
      },
      {
        "id": "55aa004122ef6f08dc9feb09f90d40c7",
        "source_id": "c0f9fe0bc9d528b6b5f227249e3c76ab",
        "target_id": "64154fe0ef7a56f70668c352ea0d0383",
        "types": [
          "regulates"
        ],
        "strength": 0.5,
        "description": "The CSA regulates controlled substances, including CBD, but is preempted by the Farm Act for industrial hemp.",
        "chunk_refs": [
          "1ccf2014205c26d63543890dd419d2b8"
        ]
      },
      {
        "id": "af5b84fa4182625a86d9cd1a754ff29a",
        "source_id": "b2368990b635d8f104b95e8235fbe86f",
        "target_id": "ae85d731c7ee2616fdf34d8edd6addce",
        "types": [
          "DERIVATION"
        ],
        "strength": 0.8,
        "description": "CBD is derived from Cannabis sativa.",
        "chunk_refs": [
          "e317b24947911f93f17fb3b1a68af31a"
        ]
      },
      {
        "id": "97596cae696a5cfab0ecb1a7c5581f91",
        "source_id": "966713f7b5ba031466d81d12bce78e43",
        "target_id": "ae85d731c7ee2616fdf34d8edd6addce",
        "types": [
          "REGULATION"
        ],
        "strength": 0.9,
        "description": "FDA does not recognize CBD as a dietary supplement ingredient.",
        "chunk_refs": [
          "e317b24947911f93f17fb3b1a68af31a"
        ]
      },
      {
        "id": "60ac9030589ec133dea2890aae3d27ad",
        "source_id": "aa4812e81e63eaa262314ddf4ca9ab6b",
        "target_id": "ae85d731c7ee2616fdf34d8edd6addce",
        "types": [
          "MARKET"
        ],
        "strength": 0.8,
        "description": "Hemp-derived CBD products are sold in the United States.",
        "chunk_refs": [
          "e317b24947911f93f17fb3b1a68af31a"
        ]
      },
      {
        "id": "386f5965da4b788b805b9ef6ea1968ef",
        "source_id": "6f2320d2dd15fcf4b2cdbf537aab1588",
        "target_id": "ae85d731c7ee2616fdf34d8edd6addce",
        "types": [
          "USAGE"
        ],
        "strength": 0.7,
        "description": "Cannabis users consume CBD, but individual use data is scarce.",
        "chunk_refs": [
          "e317b24947911f93f17fb3b1a68af31a"
        ]
      },
      {
        "id": "766c544e1a0fbbb4268fa722844dda4a",
        "source_id": "bdf7edd1c983379da818ab7c8eb029c9",
        "target_id": "336d9c9d3781f53eb2cd748c83ddae80",
        "types": [
          "FOCUS_OF_STUDY"
        ],
        "strength": 1.0,
        "description": "The study is focused on understanding CBD usage patterns and effects.",
        "chunk_refs": [
          "2ca47679a68bf438938ba31edd098093",
          "17fdeb30ccdf930b61fcb9a12d61afa3"
        ]
      },
      {
        "id": "1fa9f387f8a1480099174ca1c48a3445",
        "source_id": "bdf7edd1c983379da818ab7c8eb029c9",
        "target_id": "de56869561ce8f8d217c39ae9b7490e6",
        "types": [
          "DATA_COLLECTION_METHOD"
        ],
        "strength": 1.0,
        "description": "The study uses a survey as the data collection method.",
        "chunk_refs": [
          "2ca47679a68bf438938ba31edd098093"
        ]
      },
      {
        "id": "201cf5ec6d5f219ea85b3b047a6fd941",
        "source_id": "de56869561ce8f8d217c39ae9b7490e6",
        "target_id": "38583cad94bdec91c0cd4f102a867012",
        "types": [
          "PARTICIPANTS"
        ],
        "strength": 1.0,
        "description": "The survey is administered to individuals who are using CBD.",
        "chunk_refs": [
          "2ca47679a68bf438938ba31edd098093"
        ]
      },
      {
        "id": "3b6462f1e49e496c80104d2e39dca561",
        "source_id": "bdf7edd1c983379da818ab7c8eb029c9",
        "target_id": "36eb84ce6dc67d34567b54b4db77d540",
        "types": [
          "INSTITUTIONAL_AFFILIATION"
        ],
        "strength": 1.0,
        "description": "The study was conducted at San Diego State University.",
        "chunk_refs": [
          "2ca47679a68bf438938ba31edd098093"
        ]
      },
      {
        "id": "e0494781cf5a454404b403e6c880b1f1",
        "source_id": "ecc5af9a5ddcdf9e8dadbd13285ab975",
        "target_id": "fa5f7aaefcf6032635ed725d9f8ad6e0",
        "types": [
          "Participated in"
        ],
        "strength": 0.8,
        "description": "Respondents participated in the online survey, providing valuable data for the study.",
        "chunk_refs": [
          "225cbb08d037d4a7746d47c931e45ec7"
        ]
      },
      {
        "id": "0059a594dcd4106924c001d18b6cb344",
        "source_id": "2ee2010b82889e662382823709b20125",
        "target_id": "ecc5af9a5ddcdf9e8dadbd13285ab975",
        "types": [
          "Assisted in recruitment"
        ],
        "strength": 0.6,
        "description": "Manufacturers assisted in recruiting respondents by promoting the survey to their customers.",
        "chunk_refs": [
          "225cbb08d037d4a7746d47c931e45ec7"
        ]
      },
      {
        "id": "7198515842578b4f7e584abf22101137",
        "source_id": "fa5f7aaefcf6032635ed725d9f8ad6e0",
        "target_id": "affe5369bba776beb57f02daf509e45f",
        "types": [
          "Focused on"
        ],
        "strength": 0.9,
        "description": "The online survey focused on collecting data related to CBD use and experiences.",
        "chunk_refs": [
          "225cbb08d037d4a7746d47c931e45ec7"
        ]
      },
      {
        "id": "2d34e5706d3aaf3a90c30ae08aed40ae",
        "source_id": "b96691f84476c5339d50de841d9998b7",
        "target_id": "fa5f7aaefcf6032635ed725d9f8ad6e0",
        "types": [
          "Used for data analysis"
        ],
        "strength": 0.7,
        "description": "SAS University Edition was used to analyze the data collected from the online survey.",
        "chunk_refs": [
          "225cbb08d037d4a7746d47c931e45ec7"
        ]
      },
      {
        "id": "6fe6a5b18654f2927a0e0a20afdc3ac6",
        "source_id": "1202ea6325564b812abe3e3cf3ded136",
        "target_id": "0a7acc2ef545e418c7f8f94aa08aaf99",
        "types": [
          "AUTHORS_TO_FIELD_OF_STUDY"
        ],
        "strength": 0.7,
        "description": "Corroon and Phillips are authors of a research paper on cannabis and cannabinoid research.",
        "chunk_refs": [
          "7975dd7cb686c5fc94fbed8018693cc9"
        ]
      },
      {
        "id": "844cfd6aecc294e7e09cc07bfbdda0e2",
        "source_id": "eb441e634597ca7955c41b207843d220",
        "target_id": "0a7acc2ef545e418c7f8f94aa08aaf99",
        "types": [
          "STATISTICAL_MEASURE_TO_FIELD_OF_STUDY"
        ],
        "strength": 0.6,
        "description": "Odds ratios are used to estimate the strength of association in the research on cannabis and cannabinoid research.",
        "chunk_refs": [
          "7975dd7cb686c5fc94fbed8018693cc9"
        ]
      },
      {
        "id": "48463051d129a0f27d49bbe0c1532ecd",
        "source_id": "f3056b27a0796b296c798a29f479940a",
        "target_id": "ecc5af9a5ddcdf9e8dadbd13285ab975",
        "types": [
          "HAS_PARTICIPANTS"
        ],
        "strength": 0.8,
        "description": "The final study consists of the respondents who participated in the survey.",
        "chunk_refs": [
          "9af3669e6d678788131236a32f915b63"
        ]
      },
      {
        "id": "d8cd77902b2d37157c7b2324f381c309",
        "source_id": "ecc5af9a5ddcdf9e8dadbd13285ab975",
        "target_id": "82bb4815eafa20ef13686e689d0eb98e",
        "types": [
          "HAS_CHARACTERISTICS"
        ],
        "strength": 0.9,
        "description": "The respondents have certain demographic characteristics, such as gender, age, education, and location.",
        "chunk_refs": [
          "9af3669e6d678788131236a32f915b63"
        ]
      },
      {
        "id": "9eecedd875071d6214c9e54dfe3d09aa",
        "source_id": "f3056b27a0796b296c798a29f479940a",
        "target_id": "affe5369bba776beb57f02daf509e45f",
        "types": [
          "STUDIES"
        ],
        "strength": 0.9,
        "description": "The final study examines the use of CBD for medical and general health purposes.",
        "chunk_refs": [
          "9af3669e6d678788131236a32f915b63"
        ]
      },
      {
        "id": "ef4388b1a5267a73765b140e3e8ffc88",
        "source_id": "ecc5af9a5ddcdf9e8dadbd13285ab975",
        "target_id": "996984d9e0a814664b95815957c11518",
        "types": [
          "RESIDES_IN"
        ],
        "strength": 0.8,
        "description": "The majority of respondents reside in the United States.",
        "chunk_refs": [
          "9af3669e6d678788131236a32f915b63"
        ]
      },
      {
        "id": "76babaec3ea15c0822446f9feb9e4fba",
        "source_id": "5f39aa2e03c2d02af57ddb9c581eeaa2",
        "target_id": "d37930cbfb84fc45a096b95425a123f3",
        "types": [
          "treats"
        ],
        "strength": 0.8,
        "description": "CBD is used to treat medical conditions",
        "chunk_refs": [
          "b1cf1023fec157e1eb9e6ec8751b5d87",
          "7e17931eb101c758d54bfb0e7b4c8a84",
          "f657d8ccebf4fdc599752d300607679b"
        ]
      },
      {
        "id": "b4cb9b8dc0762f83ba3d5e1d3009dfcd",
        "source_id": "5c10a4e8598b51e705a52713fc72f36a",
        "target_id": "5f39aa2e03c2d02af57ddb9c581eeaa2",
        "types": [
          "uses"
        ],
        "strength": 0.7,
        "description": "Women are more likely to use CBD to treat medical conditions",
        "chunk_refs": [
          "b1cf1023fec157e1eb9e6ec8751b5d87"
        ]
      },
      {
        "id": "6c785fd7b6cf4925f3263eb1edab57ca",
        "source_id": "831d42b9235d08deda282da5e27aaeda",
        "target_id": "5f39aa2e03c2d02af57ddb9c581eeaa2",
        "types": [
          "uses"
        ],
        "strength": 0.5,
        "description": "Men also use CBD to treat medical conditions, but at a lower rate than women",
        "chunk_refs": [
          "b1cf1023fec157e1eb9e6ec8751b5d87"
        ]
      },
      {
        "id": "ba0a950f6e88f39d6f2d0e9f186ce0fd",
        "source_id": "918d332bb1e96cc0d4ac7ede4fe855d0",
        "target_id": "5f39aa2e03c2d02af57ddb9c581eeaa2",
        "types": [
          "influences"
        ],
        "strength": 0.6,
        "description": "Age is positively correlated with the use of CBD to treat medical conditions",
        "chunk_refs": [
          "b1cf1023fec157e1eb9e6ec8751b5d87"
        ]
      },
      {
        "id": "63ff29e66605748af386231a6b11de66",
        "source_id": "459ce27af49a9d0e8063a6751f3d81bb",
        "target_id": "5f39aa2e03c2d02af57ddb9c581eeaa2",
        "types": [
          "reports"
        ],
        "strength": 0.9,
        "description": "Respondents reported using CBD to treat medical conditions",
        "chunk_refs": [
          "b1cf1023fec157e1eb9e6ec8751b5d87",
          "b782e359c27dbde3a3084a4fae577a09",
          "f657d8ccebf4fdc599752d300607679b",
          "dc819420ff510d15bb4611c8e1e2e2e6"
        ]
      },
      {
        "id": "95caa1de3e16ecbbbb3e5765ad41e582",
        "source_id": "459ce27af49a9d0e8063a6751f3d81bb",
        "target_id": "3609aa0c27d6d33db45a3f9fe0ec89dd",
        "types": [
          "reports"
        ],
        "strength": 0.7,
        "description": "Respondents reported using CBD to treat medical conditions.",
        "chunk_refs": [
          "b782e359c27dbde3a3084a4fae577a09",
          "2e976f3ffc590a63916f0a466eb861e1",
          "f9dc543f76c25659e7d883a263585f7c"
        ]
      },
      {
        "id": "95c1e78d0540dfd443acf1517705cfcc",
        "source_id": "c03fe34012d79d395c3591ebf85a48da",
        "target_id": "9ab3d0c03d5250e3ec1ebbbd0df42870",
        "types": [
          "Demographic Characteristic"
        ],
        "strength": 0.8,
        "description": "Survey respondents were characterized by their gender.",
        "chunk_refs": [
          "befc75f0974d434765527d4b2de9f2c3"
        ]
      },
      {
        "id": "ac2ec5e8c7a7cfa2836db2e4769bf058",
        "source_id": "c03fe34012d79d395c3591ebf85a48da",
        "target_id": "a96383dee5efe71430a6aeff93724fb3",
        "types": [
          "Location"
        ],
        "strength": 0.8,
        "description": "Survey respondents were primarily from the United States.",
        "chunk_refs": [
          "befc75f0974d434765527d4b2de9f2c3"
        ]
      },
      {
        "id": "863f6fda9fbf67749366b3c1cc980dd3",
        "source_id": "c03fe34012d79d395c3591ebf85a48da",
        "target_id": "ad0363d256248a7be1fcde8007238683",
        "types": [
          "Behavioral Characteristic"
        ],
        "strength": 0.8,
        "description": "Survey respondents were characterized by their cannabis use frequency.",
        "chunk_refs": [
          "befc75f0974d434765527d4b2de9f2c3"
        ]
      },
      {
        "id": "8d2ec128e409ac1f04771cb9a9099ccc",
        "source_id": "5f39aa2e03c2d02af57ddb9c581eeaa2",
        "target_id": "99a8326869e5fe2c2f577235136fdeeb",
        "types": [
          "Therapeutic Use"
        ],
        "strength": 0.9,
        "description": "CBD was primarily used for general health and well-being.",
        "chunk_refs": [
          "befc75f0974d434765527d4b2de9f2c3",
          "7e17931eb101c758d54bfb0e7b4c8a84"
        ]
      },
      {
        "id": "e62a4e98e09d52341d28afaa651afcba",
        "source_id": "30a99d20c790f3c1bf6623949507a834",
        "target_id": "ed564c1dd67f3ddbe6aab33fd53b2d1c",
        "types": [
          "TREATS"
        ],
        "strength": 0.8,
        "description": "Cannabidiol is used to treat medical conditions.",
        "chunk_refs": [
          "f3c6376687f0ebbedaecad1723d39abb",
          "0c252c1114841dcef2babbca0f421465",
          "8b1a29f81847b8de655733132afdc7e8"
        ]
      },
      {
        "id": "70d11b2cc19f58b7f6071d6684d163d8",
        "source_id": "a4a9a4d736d6b4fbc5124779bd70431b",
        "target_id": "10f3e79f0a5b38f08c5d08879b7befee",
        "types": [
          "INFLUENCES"
        ],
        "strength": 0.7,
        "description": "Sociodemographic characteristics influence general health.",
        "chunk_refs": [
          "f3c6376687f0ebbedaecad1723d39abb"
        ]
      },
      {
        "id": "2b382ea8d561baf55aff0d0650767bf6",
        "source_id": "e1377a6c82db81fb50dc7951d4b8501d",
        "target_id": "30a99d20c790f3c1bf6623949507a834",
        "types": [
          "USES"
        ],
        "strength": 0.6,
        "description": "Males use Cannabidiol for medical conditions.",
        "chunk_refs": [
          "f3c6376687f0ebbedaecad1723d39abb"
        ]
      },
      {
        "id": "ac6d5d3d8cfa83c588a3eaa2ad446f89",
        "source_id": "c4aa686acecb5884c4d8184b7dc9573a",
        "target_id": "30a99d20c790f3c1bf6623949507a834",
        "types": [
          "USES"
        ],
        "strength": 0.6,
        "description": "Females use Cannabidiol for medical conditions.",
        "chunk_refs": [
          "f3c6376687f0ebbedaecad1723d39abb"
        ]
      },
      {
        "id": "36507c25a5302c237b5900d56986024e",
        "source_id": "d648964e8eb2c63273272c4b5ac98028",
        "target_id": "10f3e79f0a5b38f08c5d08879b7befee",
        "types": [
          "CORRELATES"
        ],
        "strength": 0.5,
        "description": "Education level correlates with general health.",
        "chunk_refs": [
          "f3c6376687f0ebbedaecad1723d39abb"
        ]
      },
      {
        "id": "ed88c11c1813bc85fe60b5ec30b6233b",
        "source_id": "42f3adee1e368c03018a625408ca098a",
        "target_id": "66b8a1d4928ed893660ca9a015c64ed9",
        "types": [
          "TREATS"
        ],
        "strength": 0.8,
        "description": "Cannabis is used to treat various medical conditions.",
        "chunk_refs": [
          "2e976f3ffc590a63916f0a466eb861e1",
          "0c5c9994148ed73b472acdadfb7696f6"
        ]
      },
      {
        "id": "03fe1ebd36d1e8182db4f2c82015adb7",
        "source_id": "90f7e79a13ddfc9a6d524edf6273679b",
        "target_id": "42f3adee1e368c03018a625408ca098a",
        "types": [
          "PART_OF"
        ],
        "strength": 0.9,
        "description": "CBD is a compound derived from cannabis.",
        "chunk_refs": [
          "2e976f3ffc590a63916f0a466eb861e1"
        ]
      },
      {
        "id": "95d908336c263442608e06400c5d4a3a",
        "source_id": "1e85fb3fe8da0718e9ac96bc9ca50dbb",
        "target_id": "42f3adee1e368c03018a625408ca098a",
        "types": [
          "STUDIED"
        ],
        "strength": 0.8,
        "description": "Corroon and Phillips conducted a study on cannabis and cannabinoid research.",
        "chunk_refs": [
          "2e976f3ffc590a63916f0a466eb861e1"
        ]
      },
      {
        "id": "784ca9e221eef9e95b00b29c891a432a",
        "source_id": "459ce27af49a9d0e8063a6751f3d81bb",
        "target_id": "3aa6b574d76110a57c22fa9b556f88bf",
        "types": [
          "uses"
        ],
        "strength": 0.9,
        "description": "Respondents use various methods to administer CBD",
        "chunk_refs": [
          "7e17931eb101c758d54bfb0e7b4c8a84"
        ]
      },
      {
        "id": "4e5630fa634edc29bd07d51544df33dc",
        "source_id": "3aa6b574d76110a57c22fa9b556f88bf",
        "target_id": "5f39aa2e03c2d02af57ddb9c581eeaa2",
        "types": [
          "is_used_in"
        ],
        "strength": 0.9,
        "description": "CBD is used in various administration methods",
        "chunk_refs": [
          "7e17931eb101c758d54bfb0e7b4c8a84"
        ]
      },
      {
        "id": "1436e7742e6ed64f9d2f4b5ed85bffb8",
        "source_id": "63bbeffb3d3ab09a10ee6e037c348c15",
        "target_id": "507d4e351ea16bef5f4e05799cf11eca",
        "types": [
          "RECOMMENDATION"
        ],
        "strength": 0.8,
        "description": "Respondents learned about CBD from Medical Doctors",
        "chunk_refs": [
          "f657d8ccebf4fdc599752d300607679b"
        ]
      },
      {
        "id": "9c264683c9e3321c4ca9196427c09c2b",
        "source_id": "578bda7641e8a61dd0139e64d7c362ce",
        "target_id": "88c7173516b99342c1878d33d831d49e",
        "types": [
          "EVALUATION"
        ],
        "strength": 0.8,
        "description": "Respondents evaluated the efficacy of CBD in treating medical conditions",
        "chunk_refs": [
          "f657d8ccebf4fdc599752d300607679b"
        ]
      },
      {
        "id": "9a1921cba0614936d5efdc49d6a3f764",
        "source_id": "affe5369bba776beb57f02daf509e45f",
        "target_id": "7e31e7c2e4ae96384a8c64da4b2ae674",
        "types": [
          "TREATS"
        ],
        "strength": 0.8,
        "description": "CBD is used to treat chronic pain.",
        "chunk_refs": [
          "10d60f2c9e68f682154b01d9d3afd253"
        ]
      },
      {
        "id": "bfe192d230761df450a1f09f7f646167",
        "source_id": "affe5369bba776beb57f02daf509e45f",
        "target_id": "e8bfae1cd5fc688533ecd3ef5e892b27",
        "types": [
          "TREATS"
        ],
        "strength": 0.8,
        "description": "CBD is used to treat arthritis/joint pain.",
        "chunk_refs": [
          "10d60f2c9e68f682154b01d9d3afd253"
        ]
      },
      {
        "id": "f6ecf0270b3f3a90294860c438638b26",
        "source_id": "affe5369bba776beb57f02daf509e45f",
        "target_id": "50760c209feb23f9600fa8ad19f8eebe",
        "types": [
          "TREATS"
        ],
        "strength": 0.8,
        "description": "CBD is used to treat anxiety.",
        "chunk_refs": [
          "10d60f2c9e68f682154b01d9d3afd253"
        ]
      },
      {
        "id": "254b3958b19284c5bba4abbce6500af7",
        "source_id": "bc1c0df89ae991acf1a7f9991e9ecdc4",
        "target_id": "affe5369bba776beb57f02daf509e45f",
        "types": [
          "CONTAINS"
        ],
        "strength": 0.9,
        "description": "Cannabis use involves the consumption of CBD.",
        "chunk_refs": [
          "10d60f2c9e68f682154b01d9d3afd253"
        ]
      },
      {
        "id": "58a88556c81baff597b413808ca492ec",
        "source_id": "affe5369bba776beb57f02daf509e45f",
        "target_id": "9e52d69c78a0825e706a1b88fed356da",
        "types": [
          "HAS_ADVERSE_EFFECTS"
        ],
        "strength": 0.7,
        "description": "CBD use is associated with side effects.",
        "chunk_refs": [
          "10d60f2c9e68f682154b01d9d3afd253"
        ]
      },
      {
        "id": "c4150a18dad66309383f7061586fd52a",
        "source_id": "9e52d69c78a0825e706a1b88fed356da",
        "target_id": "d0d618f3a7c7fb68dda89382690ebbb2",
        "types": [
          "IS_A"
        ],
        "strength": 0.9,
        "description": "Side effects are a type of adverse effect.",
        "chunk_refs": [
          "10d60f2c9e68f682154b01d9d3afd253"
        ]
      },
      {
        "id": "01136fb7fffe22af436d653daa7419a0",
        "source_id": "5fbab8665adf7cfcd025973e2411cded",
        "target_id": "5f39aa2e03c2d02af57ddb9c581eeaa2",
        "types": [
          "uses"
        ],
        "strength": 0.7,
        "description": "Medical users use CBD.",
        "chunk_refs": [
          "17fdeb30ccdf930b61fcb9a12d61afa3"
        ]
      },
      {
        "id": "1fb5717d5a7b798823a9e927ec18fcf0",
        "source_id": "a4033169173cd04a2e5ffe8a1e5e4ba3",
        "target_id": "5f39aa2e03c2d02af57ddb9c581eeaa2",
        "types": [
          "uses"
        ],
        "strength": 0.6,
        "description": "General health and well-being users also use CBD.",
        "chunk_refs": [
          "17fdeb30ccdf930b61fcb9a12d61afa3"
        ]
      },
      {
        "id": "13656cd1a5a88a5ff686f1daa0396d82",
        "source_id": "0a3d1e11a59a5b21d3ce39ce9533b5db",
        "target_id": "3609aa0c27d6d33db45a3f9fe0ec89dd",
        "types": [
          "is_a"
        ],
        "strength": 0.8,
        "description": "Pain is a type of medical condition.",
        "chunk_refs": [
          "17fdeb30ccdf930b61fcb9a12d61afa3"
        ]
      },
      {
        "id": "19776c3833786282dc275350f5144e46",
        "source_id": "5f39aa2e03c2d02af57ddb9c581eeaa2",
        "target_id": "dd5dfad0986c2dde8c7d7e616e85c85e",
        "types": [
          "interacts with"
        ],
        "strength": 0.8,
        "description": "CBD interacts with the endocannabinoid system to produce analgesic effects.",
        "chunk_refs": [
          "fdac444e60e75aca0ccda30488843c84"
        ]
      },
      {
        "id": "71bba863a21533f44e8b5cb171da905b",
        "source_id": "5f39aa2e03c2d02af57ddb9c581eeaa2",
        "target_id": "e86358e108220befb712c481c7427aba",
        "types": [
          "relieves"
        ],
        "strength": 0.9,
        "description": "CBD has been shown to reduce chronic and acute pain in various models.",
        "chunk_refs": [
          "fdac444e60e75aca0ccda30488843c84"
        ]
      },
      {
        "id": "44704cc825cb425f4ba725bc789c7902",
        "source_id": "5f39aa2e03c2d02af57ddb9c581eeaa2",
        "target_id": "250f08d314a5aee210ade38b37e6af62",
        "types": [
          "inhibits"
        ],
        "strength": 0.7,
        "description": "CBD has been proposed to inhibit THC-associated anxiety.",
        "chunk_refs": [
          "fdac444e60e75aca0ccda30488843c84"
        ]
      },
      {
        "id": "1e7e7ea4e66f115d2849f34a1ac14fb9",
        "source_id": "5f39aa2e03c2d02af57ddb9c581eeaa2",
        "target_id": "e82c2a29363bf1e10402b5dc596ed57b",
        "types": [
          "treats"
        ],
        "strength": 0.6,
        "description": "CBD has been reported to be used for treating depression.",
        "chunk_refs": [
          "fdac444e60e75aca0ccda30488843c84"
        ]
      },
      {
        "id": "6161bdf8789ad59be1dc77b8affe938c",
        "source_id": "64154fe0ef7a56f70668c352ea0d0383",
        "target_id": "48eb2426a4a5e268483a7b99fe5464ee",
        "types": [
          "Interacts_with"
        ],
        "strength": 0.8,
        "description": "CBD interacts with cannabinoid receptors to produce its therapeutic effects.",
        "chunk_refs": [
          "f71f89736cc407d498719eb69377866f"
        ]
      },
      {
        "id": "63cd7fc4e4cac35f935aadf075a4bdd5",
        "source_id": "4d1fbd6d8adb6e57a0aac25e3247fd93",
        "target_id": "48eb2426a4a5e268483a7b99fe5464ee",
        "types": [
          "Interacts_with"
        ],
        "strength": 0.8,
        "description": "THC interacts with cannabinoid receptors to produce its psychoactive effects.",
        "chunk_refs": [
          "f71f89736cc407d498719eb69377866f"
        ]
      },
      {
        "id": "5be1d3d7af58e48b02a44f07eb4b546f",
        "source_id": "64154fe0ef7a56f70668c352ea0d0383",
        "target_id": "240517ffb4f78b24cc018e9bc754c30c",
        "types": [
          "Targets"
        ],
        "strength": 0.7,
        "description": "CBD targets serotonin 5-HT1A receptors to reduce anxiety.",
        "chunk_refs": [
          "f71f89736cc407d498719eb69377866f"
        ]
      },
      {
        "id": "838b3d482a6458601a123adaae7998c7",
        "source_id": "64154fe0ef7a56f70668c352ea0d0383",
        "target_id": "fca6c99e5e76d30b8e2699899c77dbcc",
        "types": [
          "Targets"
        ],
        "strength": 0.7,
        "description": "CBD targets GABAA receptors to reduce anxiety.",
        "chunk_refs": [
          "f71f89736cc407d498719eb69377866f"
        ]
      },
      {
        "id": "a71c1bea9152e1e6975e8418f0598a5a",
        "source_id": "3d4c30453046a0ec162d2bdefaf845c7",
        "target_id": "64154fe0ef7a56f70668c352ea0d0383",
        "types": [
          "Uses"
        ],
        "strength": 0.9,
        "description": "Survey respondents use CBD for its therapeutic benefits.",
        "chunk_refs": [
          "f71f89736cc407d498719eb69377866f"
        ]
      },
      {
        "id": "7cc867725fcdeeb1b5b7b3ad776659bc",
        "source_id": "fee8be600b9f5bc1666451e88d12fbc4",
        "target_id": "3d4c30453046a0ec162d2bdefaf845c7",
        "types": [
          "Recruits"
        ],
        "strength": 0.9,
        "description": "The industry survey recruits participants from customers of an online medical marijuana recommendation service.",
        "chunk_refs": [
          "f71f89736cc407d498719eb69377866f"
        ]
      },
      {
        "id": "ad8aada9a74fdd260f27d06104e99491",
        "source_id": "63bbeffb3d3ab09a10ee6e037c348c15",
        "target_id": "46625c2c0d5f2ae118ec985fbfcb02d2",
        "types": [
          "HAS_CHARACTERISTICS"
        ],
        "strength": 0.9,
        "description": "Respondents provided information about their Cannabidiol usage characteristics.",
        "chunk_refs": [
          "0c252c1114841dcef2babbca0f421465"
        ]
      },
      {
        "id": "80977512c6e86b75dfb0e1ecf6633dfd",
        "source_id": "5bb2f5fded20f6decdf21ecec8de5835",
        "target_id": "578bda7641e8a61dd0139e64d7c362ce",
        "types": [
          "RELATED_TO"
        ],
        "strength": 0.7,
        "description": "General health and well-being are related to medical conditions.",
        "chunk_refs": [
          "0c252c1114841dcef2babbca0f421465"
        ]
      },
      {
        "id": "e7f387bb4da00c5c66341cd1ad6ca74a",
        "source_id": "63bbeffb3d3ab09a10ee6e037c348c15",
        "target_id": "b855fa24d0ebf9afb2fc6e6c234f9f45",
        "types": [
          "USES"
        ],
        "strength": 0.7,
        "description": "Respondents use cannabidiol for medical conditions.",
        "chunk_refs": [
          "8b1a29f81847b8de655733132afdc7e8"
        ]
      },
      {
        "id": "ddadb85d3839cccc89d3ddebc16b94cb",
        "source_id": "88c7173516b99342c1878d33d831d49e",
        "target_id": "b855fa24d0ebf9afb2fc6e6c234f9f45",
        "types": [
          "RATED_BY"
        ],
        "strength": 0.6,
        "description": "Respondents rated the efficacy of cannabidiol in treating medical conditions.",
        "chunk_refs": [
          "8b1a29f81847b8de655733132afdc7e8"
        ]
      },
      {
        "id": "0240c12a1969b382e30d5c81cbbff7c9",
        "source_id": "425f25052919357ff622f3cc4135d81a",
        "target_id": "b855fa24d0ebf9afb2fc6e6c234f9f45",
        "types": [
          "RELATED_TO"
        ],
        "strength": 0.5,
        "description": "Regular cannabis use is related to the use of cannabidiol for medical conditions.",
        "chunk_refs": [
          "8b1a29f81847b8de655733132afdc7e8"
        ]
      },
      {
        "id": "d317ca80906f712570964c7d8b6b4c4f",
        "source_id": "1e85fb3fe8da0718e9ac96bc9ca50dbb",
        "target_id": "b855fa24d0ebf9afb2fc6e6c234f9f45",
        "types": [
          "STUDIED"
        ],
        "strength": 0.9,
        "description": "Corroon and Phillips conducted a study on the use of cannabidiol for medical conditions.",
        "chunk_refs": [
          "8b1a29f81847b8de655733132afdc7e8"
        ]
      },
      {
        "id": "f2e7e8464da77a540dc14aeaf5141dc3",
        "source_id": "43acb59498aeb13678b81af6be31b1aa",
        "target_id": "90f7e79a13ddfc9a6d524edf6273679b",
        "types": [
          "USE"
        ],
        "strength": 0.8,
        "description": "Marijuana users are more likely to use CBD.",
        "chunk_refs": [
          "e7015dfb7e48ef9f8d3b12d3cf366507"
        ]
      },
      {
        "id": "306779e7dce0c5a9d4a417b876102c38",
        "source_id": "1bda830f840e0636ef219d624e393657",
        "target_id": "43acb59498aeb13678b81af6be31b1aa",
        "types": [
          "INCLUDE"
        ],
        "strength": 0.9,
        "description": "Survey respondents include marijuana users.",
        "chunk_refs": [
          "e7015dfb7e48ef9f8d3b12d3cf366507"
        ]
      },
      {
        "id": "3d89fdd8df949e2881ec1890d2554c8a",
        "source_id": "90f7e79a13ddfc9a6d524edf6273679b",
        "target_id": "7b003e13cb2ac3a02a62afc9f8e0172d",
        "types": [
          "RELATED_TO"
        ],
        "strength": 0.7,
        "description": "CBD is related to THC, but not used as a legal route to THC consumption.",
        "chunk_refs": [
          "e7015dfb7e48ef9f8d3b12d3cf366507"
        ]
      },
      {
        "id": "20a750908882ca1a3747b3793e1d394c",
        "source_id": "5f39aa2e03c2d02af57ddb9c581eeaa2",
        "target_id": "33107244c5ee8b387fa80552cbd370d5",
        "types": [
          "has_adverse_effects"
        ],
        "strength": 0.8,
        "description": "CBD use can lead to various adverse effects.",
        "chunk_refs": [
          "f9dc543f76c25659e7d883a263585f7c"
        ]
      },
      {
        "id": "65ae49036ea93791c01a51a57a2cb2ab",
        "source_id": "c71b519b377bbffe061c66d99c467f03",
        "target_id": "33107244c5ee8b387fa80552cbd370d5",
        "types": [
          "influences"
        ],
        "strength": 0.6,
        "description": "The dose of CBD may influence the occurrence of adverse effects.",
        "chunk_refs": [
          "f9dc543f76c25659e7d883a263585f7c"
        ]
      },
      {
        "id": "db30e8dd942f4d992e7f58f891b4ee95",
        "source_id": "efc125ed8ba298d9fc6782b1d1b7d7e3",
        "target_id": "33107244c5ee8b387fa80552cbd370d5",
        "types": [
          "interacts_with"
        ],
        "strength": 0.5,
        "description": "Prescription medications may interact with CBD, leading to adverse effects.",
        "chunk_refs": [
          "f9dc543f76c25659e7d883a263585f7c"
        ]
      },
      {
        "id": "eef549f8f35b1f67aadce939738b30be",
        "source_id": "3b944c9e01a9dce71b40f38b0dee7837",
        "target_id": "8916ee83ae0bf2bbde2ffc4db85bda70",
        "types": [
          "HAS_TOPIC"
        ],
        "strength": 0.8,
        "description": "The survey studied the adverse effects of cannabis.",
        "chunk_refs": [
          "dd08513ddb7318829d671fa32dc2cf3f"
        ]
      },
      {
        "id": "4dba07e1ccd717955d202384164ac069",
        "source_id": "42f3adee1e368c03018a625408ca098a",
        "target_id": "8916ee83ae0bf2bbde2ffc4db85bda70",
        "types": [
          "CAUSES"
        ],
        "strength": 0.9,
        "description": "Cannabis use can lead to adverse effects.",
        "chunk_refs": [
          "dd08513ddb7318829d671fa32dc2cf3f"
        ]
      },
      {
        "id": "a388faf374c787a496209d66f0e547bc",
        "source_id": "578bda7641e8a61dd0139e64d7c362ce",
        "target_id": "8916ee83ae0bf2bbde2ffc4db85bda70",
        "types": [
          "IS_RELATED_TO"
        ],
        "strength": 0.7,
        "description": "Medical conditions may be related to adverse effects of cannabis.",
        "chunk_refs": [
          "dd08513ddb7318829d671fa32dc2cf3f"
        ]
      },
      {
        "id": "04f45e4726c2a6921af1b2c28f4782e5",
        "source_id": "d746dd7d06db44e480d9ba44852bedd9",
        "target_id": "8916ee83ae0bf2bbde2ffc4db85bda70",
        "types": [
          "IS_INFLUENCED_BY"
        ],
        "strength": 0.6,
        "description": "Adverse effects of cannabis can influence general health and well-being.",
        "chunk_refs": [
          "dd08513ddb7318829d671fa32dc2cf3f"
        ]
      },
      {
        "id": "5e4266ec8772bb1eb3ec8c181dfcdebd",
        "source_id": "64154fe0ef7a56f70668c352ea0d0383",
        "target_id": "afbb4b752bf2edfe6bdb24b38f234624",
        "types": [
          "subject of"
        ],
        "strength": 0.8,
        "description": "The study investigates the effects of CBD and THC.",
        "chunk_refs": [
          "9d1e450b9c308c261f7837f9a43aae24"
        ]
      },
      {
        "id": "779d213cc7c1743d4167ee61b7d28739",
        "source_id": "4d1fbd6d8adb6e57a0aac25e3247fd93",
        "target_id": "afbb4b752bf2edfe6bdb24b38f234624",
        "types": [
          "subject of"
        ],
        "strength": 0.8,
        "description": "The study examines the effects of THC and its content in CBD products.",
        "chunk_refs": [
          "9d1e450b9c308c261f7837f9a43aae24"
        ]
      },
      {
        "id": "bc82cea20d77c92a703c55eb13992de9",
        "source_id": "56b0271ed6d3db35bcb0a0db669e3bd1",
        "target_id": "64154fe0ef7a56f70668c352ea0d0383",
        "types": [
          "consumes"
        ],
        "strength": 0.9,
        "description": "Users consume CBD products, often unaware of the source and concentration of CBD.",
        "chunk_refs": [
          "9d1e450b9c308c261f7837f9a43aae24"
        ]
      },
      {
        "id": "54f8761d06923e5aee619c26efadc01e",
        "source_id": "afbb4b752bf2edfe6bdb24b38f234624",
        "target_id": "56b0271ed6d3db35bcb0a0db669e3bd1",
        "types": [
          "informs"
        ],
        "strength": 0.7,
        "description": "The study's findings inform users about the importance of accurate labeling and the potential risks of THC contamination.",
        "chunk_refs": [
          "9d1e450b9c308c261f7837f9a43aae24"
        ]
      },
      {
        "id": "9504860fa9eba4b4d2c68cf96fee06ba",
        "source_id": "5f39aa2e03c2d02af57ddb9c581eeaa2",
        "target_id": "de8c3e8513b854afe3aecb60f7c6d4ba",
        "types": [
          "CONTAINS"
        ],
        "strength": 0.8,
        "description": "CBD is a constituent of CBD-containing products.",
        "chunk_refs": [
          "3e0b5cdd3082797423f388409c351fbd"
        ]
      },
      {
        "id": "603314fee8adb679881ecc62ea378053",
        "source_id": "16d71dd49cca4a49be6263325f770ad7",
        "target_id": "de8c3e8513b854afe3aecb60f7c6d4ba",
        "types": [
          "USES"
        ],
        "strength": 0.9,
        "description": "Users consume CBD-containing products.",
        "chunk_refs": [
          "3e0b5cdd3082797423f388409c351fbd"
        ]
      },
      {
        "id": "db63935675a6b282539693fdcf01cbae",
        "source_id": "dd5337829767dd529d841b372e7fd646",
        "target_id": "16d71dd49cca4a49be6263325f770ad7",
        "types": [
          "FOCUSES_ON"
        ],
        "strength": 0.9,
        "description": "The study focuses on CBD users and their experiences.",
        "chunk_refs": [
          "3e0b5cdd3082797423f388409c351fbd"
        ]
      },
      {
        "id": "5ad44716a64bbc991825a66e3cfdf782",
        "source_id": "3629034ddd27e8bf331ded0eb380da9a",
        "target_id": "afcba590101b7ec58025f441b00882ee",
        "types": [
          "TOPIC"
        ],
        "strength": 0.8,
        "description": "Cannabis was the topic of the survey.",
        "chunk_refs": [
          "0c5c9994148ed73b472acdadfb7696f6"
        ]
      },
      {
        "id": "1550cb35a4a6f80dead32190967657bf",
        "source_id": "a4f57f9e95037811b330b17eea6e954e",
        "target_id": "afcba590101b7ec58025f441b00882ee",
        "types": [
          "PARTICIPANT"
        ],
        "strength": 0.9,
        "description": "Respondents participated in the survey.",
        "chunk_refs": [
          "0c5c9994148ed73b472acdadfb7696f6"
        ]
      },
      {
        "id": "3eb871fc9a9693b9e72892b9f543acc7",
        "source_id": "e2834cf3a00cffd3e510f4fa60f45b2b",
        "target_id": "a4f57f9e95037811b330b17eea6e954e",
        "types": [
          "INFORMATION_SOURCE"
        ],
        "strength": 0.4,
        "description": "Respondents did not primarily learn about CBD from healthcare professionals.",
        "chunk_refs": [
          "0c5c9994148ed73b472acdadfb7696f6"
        ]
      },
      {
        "id": "a88ff6425198dad3b5aa42202202cd3b",
        "source_id": "354a0b7241f41f8ef479fb985b31f798",
        "target_id": "3609aa0c27d6d33db45a3f9fe0ec89dd",
        "types": [
          "ineffective for"
        ],
        "strength": 0.7,
        "description": "Conventional medicine is often ineffective for chronic pain and other medical conditions.",
        "chunk_refs": [
          "dc819420ff510d15bb4611c8e1e2e2e6"
        ]
      },
      {
        "id": "784673ed66af0f91aca8e289457cfe6f",
        "source_id": "42f3adee1e368c03018a625408ca098a",
        "target_id": "b855fa24d0ebf9afb2fc6e6c234f9f45",
        "types": [
          "PART_OF"
        ],
        "strength": 0.8,
        "description": "Cannabidiol is a product isolated from Cannabis.",
        "chunk_refs": [
          "14ea1677d12ed444aa1fc42a6f356a29",
          "a3fe9298a663e7d36c66f6fd6e8350a8"
        ]
      },
      {
        "id": "d9916beb0186c2f500f0680e920837bd",
        "source_id": "c5164ed3a3bc4ee4832e92ac93377e81",
        "target_id": "42f3adee1e368c03018a625408ca098a",
        "types": [
          "PUBLISHER_OF"
        ],
        "strength": 0.7,
        "description": "American Herbal Pharmacopia published a monograph on Cannabis in\ufb02orescence standards.",
        "chunk_refs": [
          "14ea1677d12ed444aa1fc42a6f356a29"
        ]
      },
      {
        "id": "c1a2a24fed792c7de6c2cfa2d0fcc2c8",
        "source_id": "a4e62124372b3094c7cf224edf6620d3",
        "target_id": "b855fa24d0ebf9afb2fc6e6c234f9f45",
        "types": [
          "REVIEWER_OF"
        ],
        "strength": 0.9,
        "description": "The World Health Organization Expert Committee on Drug Dependence reviewed Cannabidiol for its potential therapeutic uses.",
        "chunk_refs": [
          "14ea1677d12ed444aa1fc42a6f356a29"
        ]
      },
      {
        "id": "9f569dde0ac343a7d6c991b6b606346b",
        "source_id": "7b9a98b65d1fd87b66bfaafdb068b294",
        "target_id": "b855fa24d0ebf9afb2fc6e6c234f9f45",
        "types": [
          "RESEARCHER_OF"
        ],
        "strength": 0.8,
        "description": "Devinsky O conducted a study on Cannabidiol in patients with treatment-resistant epilepsy.",
        "chunk_refs": [
          "14ea1677d12ed444aa1fc42a6f356a29",
          "135e9ae6c1bd0fd8ce998ed7f2781862"
        ]
      },
      {
        "id": "04b6a5b608f055732e1423edbe8c611b",
        "source_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "target_id": "574b90d5bddfa56d7c812048c6a5cde4",
        "types": [
          "TREATS"
        ],
        "strength": 0.8,
        "description": "Cannabidiol has been shown to reduce drug-resistant seizures in Dravet syndrome.",
        "chunk_refs": [
          "135e9ae6c1bd0fd8ce998ed7f2781862"
        ]
      },
      {
        "id": "beb74cadbb2329b33aec485eee0a45b8",
        "source_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "target_id": "58ee22de99682c1856cc5df9f248ae53",
        "types": [
          "ALLEVIALES"
        ],
        "strength": 0.7,
        "description": "Cannabidiol has been found to alleviate psychotic symptoms of schizophrenia.",
        "chunk_refs": [
          "135e9ae6c1bd0fd8ce998ed7f2781862"
        ]
      },
      {
        "id": "5d3503314ec802df6491e5f32bd4c4bb",
        "source_id": "df3d7f873674ea224dfab51613661772",
        "target_id": "30b9445a06ad7f2b816eece1b34598af",
        "types": [
          "PUBLISHED_IN"
        ],
        "strength": 0.8,
        "description": "Devinsky O's study was published in Lancet Neurol.",
        "chunk_refs": [
          "135e9ae6c1bd0fd8ce998ed7f2781862"
        ]
      },
      {
        "id": "bb084cc706ba5634357633eaacbe81bb",
        "source_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "target_id": "cf2bf2d2614c15dd0fd4a10f48379296",
        "types": [
          "TREATS"
        ],
        "strength": 0.8,
        "description": "Cannabidiol has been shown to reduce anxiety in various studies.",
        "chunk_refs": [
          "fff700f33c96d074e1568b990992c9ac"
        ]
      },
      {
        "id": "2bf12839779d008f055e29f06f2f60e0",
        "source_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "target_id": "b2368990b635d8f104b95e8235fbe86f",
        "types": [
          "DERIVED_FROM"
        ],
        "strength": 0.9,
        "description": "Cannabidiol is a constituent of Cannabis sativa.",
        "chunk_refs": [
          "fff700f33c96d074e1568b990992c9ac"
        ]
      },
      {
        "id": "bd1c0ca914eaa796290af494fac97b0b",
        "source_id": "cf2bf2d2614c15dd0fd4a10f48379296",
        "target_id": "01235f306a58938c061bcb3f03a8a778",
        "types": [
          "IS_A"
        ],
        "strength": 0.7,
        "description": "Social anxiety disorder is a specific type of anxiety disorder.",
        "chunk_refs": [
          "fff700f33c96d074e1568b990992c9ac"
        ]
      },
      {
        "id": "7c763b6356ed89dac384a5f433df4dd7",
        "source_id": "4fc0f7fcd2ce1be7377c78aba195ad14",
        "target_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "types": [
          "STUDIES"
        ],
        "strength": 0.6,
        "description": "Neuropsychopharmacology is a field that studies the effects of cannabidiol on the nervous system and behavior.",
        "chunk_refs": [
          "fff700f33c96d074e1568b990992c9ac"
        ]
      },
      {
        "id": "6beb6e391004bdcdd56ef7409cddb52b",
        "source_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "target_id": "1ee8aa95571089b3f782ecd5691d01b2",
        "types": [
          "TREATMENT_OPTION"
        ],
        "strength": 0.8,
        "description": "Cannabidiol is a potential treatment option for epilepsy.",
        "chunk_refs": [
          "d1867014a49dc6d33d789ace285e7390"
        ]
      },
      {
        "id": "4a569b4032be0dde34aea7372a033425",
        "source_id": "f6c487a37480f3431fab364441d4a1e3",
        "target_id": "33221dce60dd5b43b4e387091e0e2204",
        "types": [
          "INDICATION"
        ],
        "strength": 0.9,
        "description": "Sativex is indicated for the treatment of multiple sclerosis-related spasticity.",
        "chunk_refs": [
          "d1867014a49dc6d33d789ace285e7390"
        ]
      },
      {
        "id": "c731331f2777b4895ee0acaf09a82d42",
        "source_id": "4d1fbd6d8adb6e57a0aac25e3247fd93",
        "target_id": "84145963c903685f41f83b97e20fa32c",
        "types": [
          "TREATMENT_OPTION"
        ],
        "strength": 0.7,
        "description": "THC is a potential treatment option for cancer-related pain.",
        "chunk_refs": [
          "d1867014a49dc6d33d789ace285e7390"
        ]
      },
      {
        "id": "95bd2e8a45c69541ed34a2c484b80e6f",
        "source_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "target_id": "33221dce60dd5b43b4e387091e0e2204",
        "types": [
          "TREATMENT_OPTION"
        ],
        "strength": 0.6,
        "description": "Cannabidiol is a potential treatment option for multiple sclerosis-related spasticity.",
        "chunk_refs": [
          "d1867014a49dc6d33d789ace285e7390",
          "1716edf8e0575017a4b1228820b78beb"
        ]
      },
      {
        "id": "8ae9debd133f0671a679f32347e34b56",
        "source_id": "4d1fb09186cd0bed7a4a7fc105ea4e07",
        "target_id": "223e0a1e8fea5489a47e58bf41aebf95",
        "types": [
          "develops"
        ],
        "strength": 0.8,
        "description": "GW Pharmaceuticals develops Epidiolex for treatment of seizures",
        "chunk_refs": [
          "e802d7202d123ac2f7a83544b007978b"
        ]
      },
      {
        "id": "d090985312093a1a4be497719b323184",
        "source_id": "223e0a1e8fea5489a47e58bf41aebf95",
        "target_id": "eb0c7991481bd9beeef59e2bcf8dba4f",
        "types": [
          "approved_by"
        ],
        "strength": 0.9,
        "description": "Epidiolex received unanimous positive result from FDA Advisory Committee Meeting",
        "chunk_refs": [
          "e802d7202d123ac2f7a83544b007978b"
        ]
      },
      {
        "id": "837568b6cbc6d67ec876dbcc80f4df8c",
        "source_id": "4d1fb09186cd0bed7a4a7fc105ea4e07",
        "target_id": "eb0c7991481bd9beeef59e2bcf8dba4f",
        "types": [
          "submits_to"
        ],
        "strength": 0.7,
        "description": "GW Pharmaceuticals submits Epidiolex for FDA approval",
        "chunk_refs": [
          "e802d7202d123ac2f7a83544b007978b"
        ]
      },
      {
        "id": "673a6db2a398695bae76e0430b01bf4c",
        "source_id": "330f3ee92d4af50cf4de54bf710c0703",
        "target_id": "223e0a1e8fea5489a47e58bf41aebf95",
        "types": [
          "constituent_of"
        ],
        "strength": 0.9,
        "description": "Epidiolex is a plant-based pharmaceutical containing cannabinoids",
        "chunk_refs": [
          "e802d7202d123ac2f7a83544b007978b"
        ]
      },
      {
        "id": "a1ee75765fae14bbc97923459099b02d",
        "source_id": "2f47e40d64bed711c22f4cbb9ce38a2b",
        "target_id": "bb0d43eeb1f4c17dd73970bb209b90f4",
        "types": [
          "Developer"
        ],
        "strength": 0.8,
        "description": "GW Pharmaceuticals developed EPIDIOLEX.",
        "chunk_refs": [
          "0bf4cf8ef10cdcfe67c1b9ff9fd4baf4"
        ]
      },
      {
        "id": "c24464515508dcb099832ad2b886635a",
        "source_id": "bb0d43eeb1f4c17dd73970bb209b90f4",
        "target_id": "7917601f2f008540b21a27fea0f68ead",
        "types": [
          "Approved_by"
        ],
        "strength": 0.9,
        "description": "EPIDIOLEX was approved by the FDA.",
        "chunk_refs": [
          "0bf4cf8ef10cdcfe67c1b9ff9fd4baf4"
        ]
      },
      {
        "id": "177178396bfedd718347b3eb2c269e2e",
        "source_id": "7917601f2f008540b21a27fea0f68ead",
        "target_id": "aa4812e81e63eaa262314ddf4ca9ab6b",
        "types": [
          "Jurisdiction"
        ],
        "strength": 0.9,
        "description": "The FDA has jurisdiction over the United States.",
        "chunk_refs": [
          "0bf4cf8ef10cdcfe67c1b9ff9fd4baf4"
        ]
      },
      {
        "id": "82619ee52fee803d2782fbc8fa7275b4",
        "source_id": "51b3eeb20a301035500441f919539ceb",
        "target_id": "aa4812e81e63eaa262314ddf4ca9ab6b",
        "types": [
          "Jurisdiction"
        ],
        "strength": 0.9,
        "description": "The DEA has jurisdiction over the United States.",
        "chunk_refs": [
          "0bf4cf8ef10cdcfe67c1b9ff9fd4baf4"
        ]
      },
      {
        "id": "03e194b9b9008662f9236296795adecc",
        "source_id": "affe5369bba776beb57f02daf509e45f",
        "target_id": "bb0d43eeb1f4c17dd73970bb209b90f4",
        "types": [
          "Active_ingredient"
        ],
        "strength": 0.8,
        "description": "EPIDIOLEX contains CBD as its active ingredient.",
        "chunk_refs": [
          "0bf4cf8ef10cdcfe67c1b9ff9fd4baf4"
        ]
      },
      {
        "id": "718746fc637bc99e1a90a828840a5e19",
        "source_id": "186a569d87e8026fb84d73da86ae0e48",
        "target_id": "a4b1abd08bf61197cfe94a8ab12fb4ac",
        "types": [
          "Regulation"
        ],
        "strength": 0.8,
        "description": "The DEA has classified Cannabidiol as illegal.",
        "chunk_refs": [
          "a7544fe505c7aa86aeabfd7ca46e5fe2"
        ]
      },
      {
        "id": "d26e00b90adc7ed261692394b5897e83",
        "source_id": "a5930aceeea9d8ea93262ad5a8a0e220",
        "target_id": "0dd69ebb83df5c5855f60a605f9bae1d",
        "types": [
          "Enactment"
        ],
        "strength": 0.9,
        "description": "The Congress enacted the Agricultural Act of 2014.",
        "chunk_refs": [
          "a7544fe505c7aa86aeabfd7ca46e5fe2"
        ]
      },
      {
        "id": "d8287ebac63cb831091a811545924584",
        "source_id": "a5930aceeea9d8ea93262ad5a8a0e220",
        "target_id": "f9ad848701841e9d808654fabdad095c",
        "types": [
          "Enactment"
        ],
        "strength": 0.9,
        "description": "The Congress enacted the Comprehensive Drug Abuse Prevention and Control Act of 1970.",
        "chunk_refs": [
          "a7544fe505c7aa86aeabfd7ca46e5fe2"
        ]
      },
      {
        "id": "8ffc4318fbccd7d2458d4450c6e00ae5",
        "source_id": "a4b1abd08bf61197cfe94a8ab12fb4ac",
        "target_id": "4ad010cc9960b94e07da719dc39c6658",
        "types": [
          "Part_of"
        ],
        "strength": 0.7,
        "description": "Cannabidiol is a compound found in Marihuana Extract.",
        "chunk_refs": [
          "a7544fe505c7aa86aeabfd7ca46e5fe2"
        ]
      },
      {
        "id": "4c3bc223ce8141c54eda59e879df447c",
        "source_id": "186a569d87e8026fb84d73da86ae0e48",
        "target_id": "e2ab0c2d3e22334998c8a725311b351b",
        "types": [
          "Regulates"
        ],
        "strength": 0.8,
        "description": "The DEA regulates Marijuana Extract as a Schedule I substance.",
        "chunk_refs": [
          "6c1404cec40df041e6f0fddc750238ff"
        ]
      },
      {
        "id": "7ed3f78ad7c2939c48f0ca908761f3f2",
        "source_id": "96b499466313455f28c5c9c71a44b513",
        "target_id": "186a569d87e8026fb84d73da86ae0e48",
        "types": [
          "Oversees"
        ],
        "strength": 0.7,
        "description": "The Ninth Circuit Court has jurisdiction over appeals related to DEA decisions.",
        "chunk_refs": [
          "6c1404cec40df041e6f0fddc750238ff"
        ]
      },
      {
        "id": "7f5363cba6cc2a88312685a95e20b964",
        "source_id": "f49597595ce4c742f4f109345766de11",
        "target_id": "a4b1abd08bf61197cfe94a8ab12fb4ac",
        "types": [
          "Regulates"
        ],
        "strength": 0.6,
        "description": "The FDA regulates CBD as a food ingredient and potential therapeutic agent.",
        "chunk_refs": [
          "6c1404cec40df041e6f0fddc750238ff"
        ]
      },
      {
        "id": "c2f91b6b3122dd706287eceb01e4aac0",
        "source_id": "ec98402314d3b356d26f72674f728516",
        "target_id": "a4b1abd08bf61197cfe94a8ab12fb4ac",
        "types": [
          "Source"
        ],
        "strength": 0.9,
        "description": "Industrial hemp is a source of CBD.",
        "chunk_refs": [
          "6c1404cec40df041e6f0fddc750238ff"
        ]
      },
      {
        "id": "b3ca3c78136f4ef7b599c6a71a2ccf91",
        "source_id": "20ec01f1935a20f90f4b921c9a2c7bba",
        "target_id": "f49597595ce4c742f4f109345766de11",
        "types": [
          "Influences"
        ],
        "strength": 0.5,
        "description": "Cannabis Law influences FDA regulations on CBD and other cannabis-derived products.",
        "chunk_refs": [
          "6c1404cec40df041e6f0fddc750238ff"
        ]
      },
      {
        "id": "e42171c2749070f207065c18c782a5c2",
        "source_id": "8cffefdfcd28ebd6b421f89fa72173ca",
        "target_id": "acd26fe9826ed6981fda4cc7092a43f6",
        "types": [
          "inhibits"
        ],
        "strength": 0.8,
        "description": "Tetrahydrocannabinol inhibits macrophage nitric oxide production.",
        "chunk_refs": [
          "527c0f3809acba8d4d487efffcdd1079"
        ]
      },
      {
        "id": "3783a21a7b75d5115c2e17fe20913811",
        "source_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "target_id": "405fee22b47d100158d476964b7a710f",
        "types": [
          "treats"
        ],
        "strength": 0.9,
        "description": "Cannabidiol has anti-inflammatory properties, making it a potential therapeutic for inflammation.",
        "chunk_refs": [
          "527c0f3809acba8d4d487efffcdd1079"
        ]
      },
      {
        "id": "6ccdc5dbd71886012621e7dea31b1079",
        "source_id": "b2368990b635d8f104b95e8235fbe86f",
        "target_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "types": [
          "contains"
        ],
        "strength": 0.7,
        "description": "Cannabis sativa contains Cannabidiol, a non-psychoactive compound with therapeutic effects.",
        "chunk_refs": [
          "527c0f3809acba8d4d487efffcdd1079"
        ]
      },
      {
        "id": "703eb3f53419abe8176be28e25a4597c",
        "source_id": "acd26fe9826ed6981fda4cc7092a43f6",
        "target_id": "36a592f8ccc903653d49cab513b354f9",
        "types": [
          "produces"
        ],
        "strength": 0.6,
        "description": "Macrophages produce nitric oxide in response to stimuli.",
        "chunk_refs": [
          "527c0f3809acba8d4d487efffcdd1079"
        ]
      },
      {
        "id": "edb134761f7942e12b7246bf4d62564a",
        "source_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "target_id": "47d608461357e567dcb0cee49e279b79",
        "types": [
          "constituent_of"
        ],
        "strength": 0.8,
        "description": "Cannabidiol is a non-psychoactive constituent of cannabis.",
        "chunk_refs": [
          "1716edf8e0575017a4b1228820b78beb",
          "337a320bea52098f16b9783800ca95c9",
          "ddd9357949ed40371465425bececbc1c"
        ]
      },
      {
        "id": "133630c2826b4fbf374ab4ec4f1ce1de",
        "source_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "target_id": "16cef93096e44b1ef3747b3dc672a8cb",
        "types": [
          "treats"
        ],
        "strength": 0.7,
        "description": "Cannabidiol lowers the incidence of diabetes in non-obese diabetic mice.",
        "chunk_refs": [
          "1716edf8e0575017a4b1228820b78beb"
        ]
      },
      {
        "id": "922d374413133d74862dacf373a356fc",
        "source_id": "c277d8749c5c8d89f6db8e4e92dc428b",
        "target_id": "cfaf1255abe5cf40ce5e545bb4b116c4",
        "types": [
          "inhibitor"
        ],
        "strength": 0.8,
        "description": "cAMP inhibits the NF-kappa B pathway.",
        "chunk_refs": [
          "5ced33b136bf979de23a9f198f5d171d"
        ]
      },
      {
        "id": "826a69c15245b07ed7cd68013218354b",
        "source_id": "a53ba12ca4a28da5a67fad18d439bff5",
        "target_id": "cfaf1255abe5cf40ce5e545bb4b116c4",
        "types": [
          "regulator"
        ],
        "strength": 0.7,
        "description": "A2A adenosine receptor regulates the NF-kappa B pathway.",
        "chunk_refs": [
          "5ced33b136bf979de23a9f198f5d171d"
        ]
      },
      {
        "id": "7c697d04144cc12c0391cb8902019969",
        "source_id": "36c0b95679ae555a5ba50224e36f0289",
        "target_id": "405fee22b47d100158d476964b7a710f",
        "types": [
          "anti-inflammatory"
        ],
        "strength": 0.9,
        "description": "Glycine has anti-inflammatory effects.",
        "chunk_refs": [
          "5ced33b136bf979de23a9f198f5d171d"
        ]
      },
      {
        "id": "4f0ce5486421b892b35be0960db97f57",
        "source_id": "be5e5f1173c01ce1bffdf2280d8ebdd5",
        "target_id": "405fee22b47d100158d476964b7a710f",
        "types": [
          "pro-inflammatory"
        ],
        "strength": 0.6,
        "description": "TRPV1 deletion enhances local inflammation.",
        "chunk_refs": [
          "5ced33b136bf979de23a9f198f5d171d"
        ]
      },
      {
        "id": "b1999a5fb8b3aef2d508072bc394c697",
        "source_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "target_id": "b4802a7447acd2093133f67ff8e0a312",
        "types": [
          "TREATS"
        ],
        "strength": 0.8,
        "description": "Cannabidiol reverses MK-801-induced deficits in social interaction.",
        "chunk_refs": [
          "a3fe9298a663e7d36c66f6fd6e8350a8"
        ]
      },
      {
        "id": "b1eacee08b7682d8089c6a6bf73de249",
        "source_id": "2b0e05bf8d4e36249615a04cec9d8dc4",
        "target_id": "b4802a7447acd2093133f67ff8e0a312",
        "types": [
          "TREATS"
        ],
        "strength": 0.8,
        "description": "Clozapine reverses MK-801-induced deficits in social interaction.",
        "chunk_refs": [
          "a3fe9298a663e7d36c66f6fd6e8350a8"
        ]
      },
      {
        "id": "7251f62d7e05c29cb9310191ed492668",
        "source_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "target_id": "0f36a7fc0c4a8847a915e51ae6b4aacf",
        "types": [
          "TREATS"
        ],
        "strength": 0.8,
        "description": "Cannabidiol reverses MK-801-induced deficits in hyperactivity.",
        "chunk_refs": [
          "a3fe9298a663e7d36c66f6fd6e8350a8"
        ]
      },
      {
        "id": "994e9e33e90aaf1da131714e819535ae",
        "source_id": "2b0e05bf8d4e36249615a04cec9d8dc4",
        "target_id": "0f36a7fc0c4a8847a915e51ae6b4aacf",
        "types": [
          "TREATS"
        ],
        "strength": 0.8,
        "description": "Clozapine reverses MK-801-induced deficits in hyperactivity.",
        "chunk_refs": [
          "a3fe9298a663e7d36c66f6fd6e8350a8"
        ]
      },
      {
        "id": "bda2b50feb9666af1cf60923db724e5d",
        "source_id": "405fee22b47d100158d476964b7a710f",
        "target_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "types": [
          "IS_TREATED_BY"
        ],
        "strength": 0.6,
        "description": "Cannabidiol has anti-inflammatory properties.",
        "chunk_refs": [
          "a3fe9298a663e7d36c66f6fd6e8350a8"
        ]
      },
      {
        "id": "915dfb36bdeec23e01c307c5f1d6528f",
        "source_id": "1c3942fd4afbe352f0e33a9fb05ab1e2",
        "target_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "types": [
          "MODEL_FOR"
        ],
        "strength": 0.7,
        "description": "Sprague-Dawley Rats are used as a model to study the effects of Cannabidiol on social interaction and hyperactivity.",
        "chunk_refs": [
          "a3fe9298a663e7d36c66f6fd6e8350a8"
        ]
      },
      {
        "id": "8cb1e0e943f2f7293cb452bafe5df7ed",
        "source_id": "0aeb6d004aac3b76529a3ae49354d63f",
        "target_id": "e788087fa6f1797953fb00affacbcefc",
        "types": [
          "TREATS"
        ],
        "strength": 0.8,
        "description": "Vagus nerve stimulation has been shown to attenuate the systemic inflammatory response to endotoxin.",
        "chunk_refs": [
          "14a605842b2ab436fa7988e3eb1296ee"
        ]
      },
      {
        "id": "fd6643ccb7467fa466b3f8b237b8ffa1",
        "source_id": "445c719cf6f8c694768393a6f84d52c9",
        "target_id": "e788087fa6f1797953fb00affacbcefc",
        "types": [
          "TREATS"
        ],
        "strength": 0.7,
        "description": "Cannabinoids have been shown to have anti-inflammatory effects.",
        "chunk_refs": [
          "14a605842b2ab436fa7988e3eb1296ee"
        ]
      },
      {
        "id": "a517b61dc984404aacccd24542f32e02",
        "source_id": "8b3092cce15866ed52d248d10f238c55",
        "target_id": "44a42552a75a5823d14a85f507ef05c3",
        "types": [
          "TREATS"
        ],
        "strength": 0.6,
        "description": "The endocannabinoid hydrolysis inhibitor SA-57 has been shown to attenuate heroin seeking behavior in mice.",
        "chunk_refs": [
          "14a605842b2ab436fa7988e3eb1296ee"
        ]
      },
      {
        "id": "0670e3ee96c77b916836bb9b80dbc59e",
        "source_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "target_id": "f69c8b8cd2e1b654312b9bcf8eb83652",
        "types": [
          "Interacts With"
        ],
        "strength": 0.8,
        "description": "Cannabidiol influences the effects of delta-9-tetrahydrocannabinol.",
        "chunk_refs": [
          "d8e7370962a1001898cf1e1cd9d2294e"
        ]
      },
      {
        "id": "ffd7bf4443cfc2a144b0b6533b1207b6",
        "source_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "target_id": "d2778d127147de95c2dc48d46076edf1",
        "types": [
          "Acts On"
        ],
        "strength": 0.9,
        "description": "Cannabidiol has direct actions on GABAA receptors.",
        "chunk_refs": [
          "d8e7370962a1001898cf1e1cd9d2294e"
        ]
      },
      {
        "id": "e28fe64f0a8eb7b319667540076350a5",
        "source_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "target_id": "bd09c70169651b00b1ae3ac5594569a2",
        "types": [
          "Regulates"
        ],
        "strength": 0.7,
        "description": "Cannabidiol regulates emotion and emotional memory processing.",
        "chunk_refs": [
          "d8e7370962a1001898cf1e1cd9d2294e"
        ]
      },
      {
        "id": "ea1a2834ba62ef5d1685fd309980b767",
        "source_id": "9dfc4c123fa9f4780df1c31ad4362ec3",
        "target_id": "cf0690b2a63f3aa2a2bd9123757800fe",
        "types": [
          "Treats"
        ],
        "strength": 0.8,
        "description": "Cannabidiol has potential therapeutic effects in treating anxiety-related disorders.",
        "chunk_refs": [
          "d8e7370962a1001898cf1e1cd9d2294e"
        ]
      },
      {
        "id": "c3e13bf018026cacc2968cd6ba7a6040",
        "source_id": "63112860ce850633ea103649df228c9c",
        "target_id": "23e64780cba821c6279a8e4726189f71",
        "types": [
          "uses"
        ],
        "strength": 0.9,
        "description": "Medical cannabis users consume cannabis for therapeutic purposes.",
        "chunk_refs": [
          "337a320bea52098f16b9783800ca95c9"
        ]
      },
      {
        "id": "f042222f8b182dfab73a0bf11e064a73",
        "source_id": "cdf1a90bf727b190bac99c9e4093851b",
        "target_id": "560f041fe68c7e6f724f5e36134dd95f",
        "types": [
          "conducted_by"
        ],
        "strength": 0.9,
        "description": "The National Survey on Drug Use and Health is conducted by the Center for Behavioral Health Statistics and Quality.",
        "chunk_refs": [
          "337a320bea52098f16b9783800ca95c9"
        ]
      },
      {
        "id": "e27c6c53cfe8b760a34e2fcff3e18574",
        "source_id": "ad215225995a4d154c7c36039e7de554",
        "target_id": "ebe7d213a70e825d079ed976b8c5f0a3",
        "types": [
          "author of"
        ],
        "strength": 0.9,
        "description": "Corroon J is an author of a study published in Cannabinoid Research.",
        "chunk_refs": [
          "ddd9357949ed40371465425bececbc1c"
        ]
      },
      {
        "id": "fe7ba3ed2c846afdda8e0a5809e93aab",
        "source_id": "8a8ab60aebbca9151db7e09e7cde1274",
        "target_id": "ebe7d213a70e825d079ed976b8c5f0a3",
        "types": [
          "author of"
        ],
        "strength": 0.9,
        "description": "Phillips JA is an author of a study published in Cannabinoid Research.",
        "chunk_refs": [
          "ddd9357949ed40371465425bececbc1c"
        ]
      },
      {
        "id": "7471dce0ec9e86a198ade920229ff123",
        "source_id": "a4b1abd08bf61197cfe94a8ab12fb4ac",
        "target_id": "f49597595ce4c742f4f109345766de11",
        "types": [
          "regulated by"
        ],
        "strength": 0.7,
        "description": "The FDA regulates cannabidiol products.",
        "chunk_refs": [
          "ddd9357949ed40371465425bececbc1c"
        ]
      }
    ]
  }

    # Create and visualize the knowledge graph
    kg = NxKG()
    kg.load_from_json(sample_data)
    kg.visualize()