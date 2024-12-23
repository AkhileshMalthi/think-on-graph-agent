import os
import json
import logging
from typing import List, Dict, Any

import PyPDF2
from groq_extractor import KnowledgeGraphExtractor

class PDFKnowledgeGraphProcessor:
    def __init__(self, 
                 chunk_size: int = 1000, 
                 chunk_overlap: int = 200,
                 max_pdfs: int = 10):
        """
        Initialize PDF Knowledge Graph Processor
        
        :param chunk_size: Size of text chunks
        :param chunk_overlap: Overlap between chunks
        :param max_pdfs: Maximum number of PDFs to process
        """
        # Logging configuration
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Processing parameters
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_pdfs = max_pdfs
        
        # Initialize Knowledge Graph Extractor
        self.kg_extractor = KnowledgeGraphExtractor()

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from a single PDF file
        
        :param pdf_path: Path to PDF file
        :return: Extracted text
        """
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            self.logger.error(f"Error extracting text from {pdf_path}: {e}")
            return ""

    def chunk_text(self, text: str) -> List[str]:
        """
        Chunk text into smaller pieces
        
        :param text: Input text
        :return: List of text chunks
        """
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk = " ".join(words[i:i + self.chunk_size])
            chunks.append(chunk)
        
        return chunks

    def process_pdfs(self, pdf_directory: str) -> Dict[str, Any]:
        """
        Process PDFs and extract knowledge graph
        
        :param pdf_directory: Path to directory containing PDFs
        :return: Comprehensive knowledge graph
        """
        # Collect all chunks from PDFs
        all_chunks = []
        
        # Find PDF files
        pdf_files = [f for f in os.listdir(pdf_directory) if f.endswith('.pdf')]
        
        # Limit to max_pdfs
        pdf_files = pdf_files[:self.max_pdfs]
        
        # Process each PDF
        for pdf_file in pdf_files:
            full_path = os.path.join(pdf_directory, pdf_file)
            
            # Extract text
            text = self.extract_text_from_pdf(full_path)
            
            if text:
                # Chunk the text
                chunks = self.chunk_text(text)
                all_chunks.extend(chunks)
                
                self.logger.info(f"Processed PDF: {pdf_file}")
        
        # Extract knowledge graph from chunks
        knowledge_graph = self.kg_extractor.extract_knowledge_graph(all_chunks)
        
        return knowledge_graph

def main():
    # Create processor
    processor = PDFKnowledgeGraphProcessor(
        chunk_size=1000,  # Adjust as needed
        chunk_overlap=200  # Adjust as needed
    )
    
    # Specify PDF directory
    pdf_directory = 'KGBuilder/extractors/'

    # Process PDFs and extract knowledge graph
    kg = processor.process_pdfs(pdf_directory)
    
    # Save knowledge graph to JSON file
    output_file = 'knowledge_graph.json'
    with open(output_file, 'w') as f:
        json.dump(kg, f, indent=2)
    
    # Print summary
    print(f"Knowledge Graph Extracted:")
    print(f"Total Entities: {len(kg.get('entities', []))}")
    print(f"Total Relationships: {len(kg.get('relationships', []))}")
    print(f"Saved to: {output_file}")

if __name__ == "__main__":
    main()