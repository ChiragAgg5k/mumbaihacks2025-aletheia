import os
import re
from typing import Dict
import torch
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification


class NewsClassifier:
    """
    Binary News Classifier using DistilBERT
    
    Classifies text as either:
    - News (0): Legitimate news content
    - Not News (1): Social media/informal content
    """
    
    def __init__(self, model_path: str = "./news_classifier_model"):
        """
        Initialize the classifier
        
        Args:
            model_path: Path to the saved model directory
        """
        self.model_path = model_path
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """Load the trained model and tokenizer"""
        try:
            if not os.path.exists(self.model_path):
                print(f"Warning: Model not found at {self.model_path}")
                print("Please train the model first using train_news_classifier.ipynb")
                return
            
            print(f"Loading model from {self.model_path}...")
            self.tokenizer = DistilBertTokenizer.from_pretrained(self.model_path)
            self.model = DistilBertForSequenceClassification.from_pretrained(self.model_path)
            self.model.to(self.device)
            self.model.eval()
            print(f"Model loaded successfully on {self.device}")
            
        except Exception as e:
            print(f"Error loading model: {e}")
            self.model = None
            self.tokenizer = None
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        
        # Remove mentions and hashtags
        text = re.sub(r'@\w+', '', text)
        text = re.sub(r'#(\w+)', r'\1', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def predict(self, text: str) -> Dict[str, any]:
        """
        Classify text as news or not news
        
        Args:
            text: Text to classify
            
        Returns:
            Dictionary with:
            - is_news: Boolean indicating if text is news
            - label: String label ('News' or 'Not News')
            - confidence: Confidence score (0-1)
            - model_loaded: Whether model is available
        """
        # If model not loaded, return fallback
        if self.model is None or self.tokenizer is None:
            return {
                "is_news": None,
                "label": "Unknown",
                "confidence": 0.0,
                "model_loaded": False,
                "error": "Model not loaded. Please train the model first."
            }
        
        try:
            # Clean text
            cleaned_text = self.clean_text(text)
            
            if not cleaned_text:
                return {
                    "is_news": False,
                    "label": "Not News",
                    "confidence": 0.0,
                    "model_loaded": True,
                    "error": "Empty text after cleaning"
                }
            
            # Tokenize
            inputs = self.tokenizer(
                cleaned_text,
                padding='max_length',
                truncation=True,
                max_length=128,
                return_tensors='pt'
            )
            
            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Predict
            with torch.no_grad():
                outputs = self.model(**inputs)
                probabilities = torch.softmax(outputs.logits, dim=1)
                prediction = torch.argmax(probabilities, dim=1).item()
                confidence = probabilities[0][prediction].item()
            
            is_news = prediction == 0
            label = 'News' if is_news else 'Not News'
            
            return {
                "is_news": is_news,
                "label": label,
                "confidence": float(confidence),
                "model_loaded": True,
                "probabilities": {
                    "news": float(probabilities[0][0]),
                    "not_news": float(probabilities[0][1])
                }
            }
            
        except Exception as e:
            return {
                "is_news": None,
                "label": "Error",
                "confidence": 0.0,
                "model_loaded": True,
                "error": str(e)
            }


# Global classifier instance
_classifier = None


def get_classifier() -> NewsClassifier:
    """Get or create global classifier instance"""
    global _classifier
    if _classifier is None:
        _classifier = NewsClassifier()
    return _classifier


def classify_news(text: str) -> Dict[str, any]:
    """
    Classify text as news or not news using DistilBERT
    
    Args:
        text: Text to classify
        
    Returns:
        Dictionary containing classification result and confidence score
    """
    classifier = get_classifier()
    return classifier.predict(text)


# Backward compatibility alias
def classify_misinformation(text: str) -> Dict[str, any]:
    """
    Legacy function name - now calls classify_news
    
    Note: This now classifies as News vs Not News, not misinformation detection
    """
    result = classify_news(text)
    
    # Convert to old format for backward compatibility
    return {
        "is_misinformation": not result.get("is_news", False) if result.get("is_news") is not None else None,
        "confidence": result.get("confidence", 0.0),
        "label": result.get("label", "Unknown"),
        "model_loaded": result.get("model_loaded", False)
    }
