"""WebSocket consumer for video streaming."""
import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from .managers import (
    BrowserManager,
    PageManager,
    NavigationManager,
    PageEventCoordinator,
    WebSocketMessageSender,
    MessageRouter,
    InteractionManager
)
from .config import StreamConfig
from .event_handlers.mouse_handler import MouseHandler
from .event_handlers.keyboard_handler import KeyboardHandler


class VideoStreamConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that coordinates video streaming via browser screenshots.
    
    Acts as a Facade that delegates to specialized managers:
    - WebSocketMessageSender: Message sending
    - PageManager: Page operations (switch, create, close)
    - NavigationManager: Browser navigation
    - PageEventCoordinator: Page lifecycle events
    """
    
    async def connect(self):
        """Handle WebSocket connection."""
        await self.accept()
        self.streaming = False
        self.browser_manager: BrowserManager = None
        self.streaming_task = None
        
        # Initialize WebSocket message sender
        self.message_sender = WebSocketMessageSender(self.send)
        
        # Initialize interaction manager (creates components internally)
        self.interaction_manager = InteractionManager()
        
        # Initialize managers (will be fully initialized after browser_manager is created)
        self.page_manager: PageManager = None
        self.navigation_manager: NavigationManager = None
        self.page_event_coordinator: PageEventCoordinator = None
        
        # Initialize message router with handlers from interaction manager
        self.message_router = MessageRouter(
            mouse_handler=MouseHandler(self.interaction_manager.mouse_controller),
            keyboard_handler=KeyboardHandler(self.interaction_manager.keyboard_controller),
            start_callback=None  # Already handled
        )

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        self.streaming = False
        if self.streaming_task:
            self.streaming_task.cancel()
            try:
                await self.streaming_task
            except asyncio.CancelledError:
                pass
        if self.interaction_manager:
            self.interaction_manager.stop_streaming()
        if self.browser_manager:
            await self.browser_manager.cleanup()

    async def _ensure_manager_initialized(self, manager, manager_name: str) -> bool:
        """
        Ensure a manager is initialized, send error if not.
        
        Args:
            manager: Manager instance to check
            manager_name: Name of the manager for error message
            
        Returns:
            True if initialized, False otherwise
        """
        if not manager:
            await self.message_sender.send_error(f'{manager_name} not initialized')
            return False
        return True
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages and delegate to appropriate managers."""
        print(f"Received message: {text_data}")
        
        # Let MessageRouter handle validation and routing for most messages
        # Only handle special cases that need consumer-level logic
        try:
            # Quick parse to check message type (MessageRouter will validate properly)
            data = json.loads(text_data)
            message_type = data.get('type')
            
            # Handle 'start' message - needs consumer state check
            if message_type == 'start' and not self.streaming:
                session_id = data.get('session_id')
                self.streaming_task = asyncio.create_task(self.start_streaming(session_id))
                return
            
            # Handle page management messages - need manager checks
            if message_type == 'page_switch':
                if not await self._ensure_manager_initialized(self.page_manager, 'Page manager'):
                    return
                if 'page_id' not in data:
                    await self.message_sender.send_error('page_switch message missing page_id')
                    return
                await self.page_manager.switch_active_page(data['page_id'])
                return
            
            if message_type == 'new_tab':
                if not await self._ensure_manager_initialized(self.page_manager, 'Page manager'):
                    return
                await self.page_manager.create_new_tab()
                return
            
            if message_type == 'close_tab':
                if not await self._ensure_manager_initialized(self.page_manager, 'Page manager'):
                    return
                if 'page_id' not in data:
                    await self.message_sender.send_error('close_tab message missing page_id')
                    return
                await self.page_manager.close_tab(data['page_id'])
                return
            
            # Handle navigation message
            if message_type == 'navigate':
                if not await self._ensure_manager_initialized(self.navigation_manager, 'Navigation manager'):
                    return
                await self.navigation_manager.handle_navigation(data)
                return
            
            # Route all other messages through MessageRouter (handles validation)
            if self.message_router:
                await self.message_router.route(text_data)
        except json.JSONDecodeError as e:
            print(f"Message error: {e}")
            await self.message_sender.send_error(f'Invalid JSON: {str(e)}')
        except Exception as e:
            print(f"Unexpected error in receive: {e}")
            await self.message_sender.send_error(f'Error processing message: {str(e)}')


    async def start_streaming(self, session_id: str = None):
        """Start browser and begin streaming screenshots.
        
        Args:
            session_id: Optional session ID to use for persistent browser context storage
        """
        if self.streaming:
            return
        
        self.streaming = True
        
        try:
            # Initialize browser manager first (without callbacks yet)
            self.browser_manager = BrowserManager(
                viewport_width=StreamConfig.CANVAS_WIDTH,
                viewport_height=StreamConfig.CANVAS_HEIGHT
            )
            
            # Initialize managers that depend on browser_manager
            self.page_manager = PageManager(
                browser_manager=self.browser_manager,
                interaction_manager=self.interaction_manager,
                message_sender=self.message_sender
            )
            
            self.navigation_manager = NavigationManager(
                browser_manager=self.browser_manager,
                message_sender=self.message_sender
            )
            
            self.page_event_coordinator = PageEventCoordinator(
                page_manager=self.page_manager,
                message_sender=self.message_sender
            )
            
            # Set up callbacks for page events
            page_added_callback = self.page_event_coordinator.create_page_added_callback()
            page_removed_callback = self.page_event_coordinator.create_page_removed_callback()
            
            # Update browser manager with callbacks
            self.browser_manager.page_added_callback = page_added_callback
            self.browser_manager.page_removed_callback = page_removed_callback
            
            # Launch browser - use first testing URL if testing mode, otherwise use HOMEPAGE_URL
            launch_url = StreamConfig.TESTING_URLS[0] if StreamConfig.TESTING else StreamConfig.HOMEPAGE_URL
            await self.browser_manager.launch(
                url=launch_url,
                headless=StreamConfig.HEADLESS,
                session_id=session_id
            )
            
            # Open all remaining testing URLs in new tabs (only if testing mode is enabled)
            if StreamConfig.TESTING:
                for url in StreamConfig.TESTING_URLS[1:]:
                    if self.browser_manager.context:
                        new_page = await self.browser_manager.context.new_page()
                        await new_page.goto(url, wait_until='commit')
                        # Page will be automatically registered via context.on('page') listener
            
            # Send initial page list sync after browser launch if same 
            # browser was streamed from multiple clients then if user join 
            # late he gets all list of pages
            page_ids = self.browser_manager.get_all_page_ids()
            await self.message_sender.send_pages_sync(page_ids)
            
            # Start streaming - streamer will wait for page to be set via switch_active_page
            await self.interaction_manager.screenshot_streamer.stream(
                send_callback=self.message_sender.send_frame
            )
            
        except Exception as e:
            print(f"Error in streaming: {e}")
            await self.message_sender.send_error(f'Streaming error: {str(e)}')
        finally:
            self.streaming = False
            if self.browser_manager:
                await self.browser_manager.cleanup()

