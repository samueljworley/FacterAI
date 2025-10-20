from abc import ABC, abstractmethod
from typing import List, Dict, Any

class ResearchClient(ABC):
    """Abstract base class for research paper clients."""
    
    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for papers matching the query."""
        pass
    
    @abstractmethod
    async def get_paper_details(self, paper_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific paper."""
        pass
    
    @abstractmethod
    def format_paper(self, paper_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format paper data into a standardized structure."""
        pass 