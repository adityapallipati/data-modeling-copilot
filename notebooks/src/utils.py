# src/utils.py
from pathlib import Path
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from sentence_transformers import SentenceTransformer
import chromadb
import networkx as nx
import pickle
from typing import Dict, List, Tuple, Any, Optional

class ModelLoader:
    """Handles loading and management of ML models"""
    
    @staticmethod
    def load_flan_t5(model_path: str = '../models/flan-t5-base'):
        path = Path(model_path)
        tokenizer = AutoTokenizer.from_pretrained(str(path))
        model = AutoModelForSeq2SeqLM.from_pretrained(str(path))
        if torch.backends.mps.is_available():
            model = model.to('mps')
        return model, tokenizer
    
    @staticmethod
    def load_mpnet(model_path: str = '../models/all-mpnet-base-v2'):
        path = Path(model_path)
        return SentenceTransformer(str(path))

class VectorStoreManager:
    """Manages ChromaDB operations"""
    
    def __init__(self, persist_dir: str = '../data/vector_store'):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
    
    def get_or_create_collection(self, 
                               name: str, 
                               metadata: Dict[str, Any],
                               reset: bool = False) -> Any:
        """
        Get or create a ChromaDB collection.
        If reset=True, deletes existing collection before creating new one.
        """
        # First check if collection exists
        try:
            if reset:
                print(f"Attempting to delete collection '{name}'...")
                try:
                    existing_collections = self.client.list_collections()
                    if any(col.name == name for col in existing_collections):
                        self.client.delete_collection(name)
                        print(f"Collection '{name}' deleted successfully")
                except Exception as e:
                    print(f"Error during deletion: {e}")
            
            print(f"Creating new collection '{name}'...")
            return self.client.create_collection(name=name, metadata=metadata)
        
        except ValueError as e:
            print(f"Error creating collection: {e}")
            print("Attempting to get existing collection...")
            return self.client.get_collection(name)

class KnowledgeGraphManager:
    """Manages NetworkX knowledge graph operations"""
    
    def __init__(self, graph_path: str = '../data/graph_db/knowledge_graph.pickle'):
        self.graph_path = Path(graph_path)
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)
    
    def save_graph(self, G: nx.DiGraph):
        with open(self.graph_path, 'wb') as f:
            pickle.dump(G, f)
    
    def load_graph(self) -> Optional[nx.DiGraph]:
        if self.graph_path.exists():
            with open(self.graph_path, 'rb') as f:
                return pickle.load(f)
        return None
    
    @staticmethod
    def find_column_type(G: nx.DiGraph, column_name: str) -> Tuple[Optional[str], Optional[Dict]]:
        """Find data type for a column based on patterns"""
        import re
        matches = []
        
        for node, attrs in G.nodes(data=True):
            if attrs.get('pattern'):
                for pattern in attrs['pattern']:
                    if re.search(pattern, column_name.lower()):
                        matches.append((node, attrs))
        
        if matches:
            matches.sort(key=lambda x: max(len(p) for p in x[1]['pattern']), reverse=True)
            return matches[0]
        return None, None

class DataProcessor:
    """Handles data processing operations"""
    
    @staticmethod
    def chunk_guidelines(file_path: str, chunk_separator: str = '\n\n') -> List[str]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Guidelines file not found: {file_path}")
        
        with open(path, 'r') as f:
            guidelines = f.read().split(chunk_separator)
        return guidelines
    
    @staticmethod
    def process_csv_schema(file_path: str) -> List[str]:
        """Extract column names from CSV"""
        import pandas as pd
        df = pd.read_csv(file_path)
        return df.columns.tolist()