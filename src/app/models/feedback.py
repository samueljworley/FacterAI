from dataclasses import dataclass, asdict
from typing import List, Dict
from datetime import datetime
import uuid

@dataclass
class Metrics:
    clarity: int
    interpretation: int
    relevance: int
    depth: int
    citations_quality: int
    reasoning: int

@dataclass
class Feedback:
    user_query: str
    ai_response: str
    metrics: Metrics
    question_type: str
    topics: List[str]
    strength_tags: List[str]
    weakness_tags: List[str]
    feedback_id: str = None
    timestamp: str = None

    def __post_init__(self):
        if not self.feedback_id:
            self.feedback_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Convert feedback to dictionary for DynamoDB"""
        data = asdict(self)
        data['metrics'] = asdict(self.metrics)
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'Feedback':
        """Create Feedback instance from dictionary"""
        metrics = Metrics(**data.pop('metrics'))
        return cls(metrics=metrics, **data) 