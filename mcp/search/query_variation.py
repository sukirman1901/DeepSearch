"""
Query variation generator for improved search coverage.
Inspired by Exa's dynamic query generation approach.
"""
import re
from typing import Optional


class QueryVariationGenerator:
    """Generate query variations for better search coverage"""
    
    # Synonym mappings for common terms
    SYNONYMS = {
        "company": ["startup", "firm", "business", "corporation", "enterprise"],
        "person": ["individual", "professional", "expert", "specialist"],
        "code": ["implementation", "example", "snippet", "sample"],
        "paper": ["article", "study", "research", "publication"],
        "bug": ["issue", "error", "problem", "defect"],
        "fix": ["solve", "resolve", "patch", "solution"],
        "learn": ["tutorial", "guide", "howto", "documentation"],
    }
    
    # Category-specific prefixes
    CATEGORY_PREFIXES = {
        "company": ["company profile", "about", "overview"],
        "people": ["profile", "background", "expertise"],
        "research_paper": ["research paper", "arXiv", "academic"],
        "financial_report": ["SEC filing", "annual report", "earnings"],
        "personal_site": ["personal blog", "portfolio", "homepage"],
        "news": ["latest news", "recent", "breaking"],
        "code": ["code example", "implementation", "tutorial"],
    }
    
    def generate_variations(self, query: str, category: str = "general", max_variations: int = 3) -> list[str]:
        """
        Generate query variations for better search coverage.
        
        Args:
            query: Original search query
            category: Category for context-aware variations
            max_variations: Maximum number of variations to generate
            
        Returns:
            List of query variations (including original)
        """
        variations = [query]
        
        # Add category prefix if not already present
        if category in self.CATEGORY_PREFIXES:
            prefix = self.CATEGORY_PREFIXES[category][0]
            if prefix.lower() not in query.lower():
                variations.append(f"{prefix} {query}")
        
        # Add synonym variations
        words = query.lower().split()
        for i, word in enumerate(words):
            if word in self.SYNONYMS:
                for synonym in self.SYNONYMS[word][:2]:  # Max 2 synonyms per word
                    new_words = words.copy()
                    new_words[i] = synonym
                    variations.append(" ".join(new_words))
                    if len(variations) >= max_variations + 1:  # +1 for original
                        break
        
        # Add question variations if query is short
        if len(words) <= 3:
            variations.append(f"what is {query}")
            variations.append(f"how to {query}")
        
        return variations[:max_variations + 1]  # Always include original
    
    def generate_domain_queries(self, query: str, domains: list[str]) -> list[str]:
        """Generate queries for specific domains"""
        return [f"site:{domain} {query}" for domain in domains]
    
    def generate_date_queries(self, query: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
        """Add date filtering to query"""
        date_filter = ""
        if start_date:
            date_filter += f" after:{start_date}"
        if end_date:
            date_filter += f" before:{end_date}"
        return f"{query}{date_filter}"
    
    def expand_acronyms(self, query: str) -> list[str]:
        """Expand common acronyms in query"""
        acronym_map = {
            "AI": ["artificial intelligence", "machine learning"],
            "ML": ["machine learning", "statistical learning"],
            "LLM": ["large language model", "language model"],
            "NLP": ["natural language processing"],
            "API": ["application programming interface"],
            "CEO": ["chief executive officer"],
            "CTO": ["chief technology officer"],
            "VC": ["venture capital", "investor"],
        }
        
        variations = [query]
        for acronym, expansions in acronym_map.items():
            if acronym.lower() in query.lower():
                for expansion in expansions[:1]:  # Just first expansion
                    variations.append(query.replace(acronym, expansion))
        
        return variations


def get_query_suggestions(query: str, category: str = "general") -> list[str]:
    """Get query suggestions based on input"""
    generator = QueryVariationGenerator()
    return generator.generate_variations(query, category)