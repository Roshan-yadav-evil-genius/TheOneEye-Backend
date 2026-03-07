from abc import ABC, abstractmethod
from playwright.async_api import Page



class BaseAction:
    def __init__(self, page: Page):
        self.page = page
        self._accomplished = False
    
    @property
    def accomplished(self) -> bool:
        return self._accomplished

    
    @abstractmethod
    async def perform_action(self):
        pass

    @abstractmethod
    async def verify_action(self)->bool:
        pass

    async def accomplish(self):
        await self.perform_action()
        self._accomplished = await self.verify_action()  
        return self
