import logging
from abc import ABC, abstractmethod
from playwright.async_api import Page

from linkedin.actions.utils import human_wait

logger = logging.getLogger(__name__)



class AtomicAction:
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

class MoleculerAction(AtomicAction):
    def __init__(self, page: Page):
        super().__init__(page)
        self.chain_of_actions = []
    
    async def execute_chain_of_actions(self):
        for action in self.chain_of_actions:
            logger.debug("Executing action: %s", action.__class__.__name__)
            action = await action.accomplish()
            if not action.accomplished:
                logger.error("Action %s failed", action.__class__.__name__)
                return False
            await human_wait(self.page,500,1000)
        return True
    
    async def perform_action(self):
        self._accomplished = await self.execute_chain_of_actions()
    
    async def verify_action(self)->bool:
        return self._accomplished


class PageAction(ABC):
    def __init__(self, page: Page):
        self.page = page
    
    @abstractmethod
    def is_valid_page(self)->bool:
        pass