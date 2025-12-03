from abc import ABC, abstractmethod
from typing import Dict

# 모든 LLM 서비스는 generate_report 메서드를 반드시 가져야 함
class BaseLLMService(ABC):
    @abstractmethod
    async def generate_report(
        self, 
        transcript:str, 
        bert_analysis:Dict):
        
        pass