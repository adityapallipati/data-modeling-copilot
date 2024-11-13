# src/indexing/entity_extractor.py

from pathlib import Path
from typing import Dict, List, Tuple
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import json
import re

class EntityExtractor:
    def __init__(self, model_path: str = '../../models/starcoderbase-1b'):
        self.model_path = Path(model_path)
        print(f"Initializing EntityExtractor with model from: {self.model_path.absolute()}")
        
        # Load model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
        self.model = AutoModelForCausalLM.from_pretrained(str(self.model_path))

        # Set padding token if it does not exist
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Move model to MPS if available
        if torch.backends.mps.is_available():
            self.model = self.model.to('mps')
            print("Model moved to MPS")
        else:
            self.model = self.model.to('cpu')
            print("Model moved to CPU")

    def extract(self, text: str) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """Extract entities and relationships from the provided text."""
        # Adjusted prompt to be more directive
        prompt = (
            "Extract entities and data types in JSON format based on this input text:\n\n"
            f"{text}\n\n"
            "Output only the result as a JSON object:\n"
            '{"entities": [{"name": "NUMBER(38,0)", "type": "DATA_TYPE", "description": "Surrogate key numeric type"}]}'
        )
        
        print("\nPrompt:")
        print(prompt)
        
        # Tokenize with explicit attention mask
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            padding="max_length",
            truncation=True,
            max_length=512
        )
        inputs['attention_mask'] = inputs['input_ids'] != self.tokenizer.pad_token_id
        
        # Move inputs to MPS if available
        if torch.backends.mps.is_available():
            inputs = {k: v.to('mps') for k, v in inputs.items()}
        
        # Generate output
        print("\nGenerating response...")
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=128,
                num_beams=1,
                do_sample=False
            )
        
        # Decode output
        raw_output = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        print("\nRaw model output:")
        print(raw_output)
        
        # Attempt to parse JSON from the model's output
        try:
            # Extract the JSON object using regex
            json_pattern = r'\{.*\}'
            json_match = re.search(json_pattern, raw_output, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                print("\nExtracted JSON string:")
                print(json_str)
                
                data = json.loads(json_str)
                entities = data.get('entities', [])
                relationships = data.get('relationships', [])
                
                return entities, relationships
            else:
                print("\nNo JSON found in output")
                return [], []
                
        except Exception as e:
            print(f"\nError parsing output: {e}")
            return [], []

def test_extractor():
    """Test the EntityExtractor with a simple example."""
    test_text = "NUMBER(38,0) is used for Surrogate Keys."
    
    print("Testing entity extraction...")
    extractor = EntityExtractor()
    
    print("\nProcessing test text:")
    print(test_text)
    
    entities, relationships = extractor.extract(test_text)
    
    print("\nResults:")
    print("Entities found:", len(entities))
    for e in entities:
        print(f"- {e['name']} ({e['type']}): {e['description']}")
        
    print("\nRelationships found:", len(relationships))
    for r in relationships:
        print(f"- {r['source']} -> {r['target']}: {r['description']}")

if __name__ == "__main__":
    test_extractor()
