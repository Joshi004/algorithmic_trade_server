import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.http import parse_cookie
from ..utils.jwt_utils import decode_slt
from ..utils.group_utils import (
    get_group_name, 
    increment_group_subscription, 
    decrement_group_subscription
)

# Get logger
logger = logging.getLogger(__name__)

class ATSConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for ATS application real-time communication
    Supports scanner subscriptions and other app-wide functionality
    Uses JWT authentication from cookies
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subscribed_groups = set()  # Track groups this connection is subscribed to
        self.user_data = None
    
    async def connect(self):
        """Handle WebSocket connection"""
        logger.info(f"WebSocket connection attempt from {self.channel_name}")
        
        # Authenticate user using JWT from cookies
        user_data = await self.authenticate_user()
        if not user_data:
            logger.warning(f"Authentication failed for {self.channel_name}")
            await self.close(code=4001)  # Custom close code for auth failure
            return
        
        self.user_data = user_data
        logger.info(f"User authenticated: {user_data.get('username')} on channel {self.channel_name}")
        
        # Accept the WebSocket connection
        await self.accept()
        
        # Send connection success message with user info
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected successfully',
            'user': user_data.get('username'),
            'channel_name': self.channel_name
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        logger.info(f"WebSocket disconnecting: {self.channel_name}, close_code: {close_code}")
        
        # Unsubscribe from all groups and decrement counters
        for group_name in self.subscribed_groups.copy():
            await self.leave_group(group_name)
        
        logger.info(f"User {self.user_data.get('username') if self.user_data else 'unknown'} disconnected")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            logger.info(f"Received action '{action}' from {self.channel_name}")
            
            if action == 'subscribe_scanner':
                await self.handle_subscribe_scanner(data)
            elif action == 'unsubscribe_scanner':
                await self.handle_unsubscribe_scanner(data)
            else:
                await self.send_error(f"Unknown action: {action}")
        
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            await self.send_error("Internal server error")
    
    async def handle_subscribe_scanner(self, data):
        """Handle scanner subscription request"""
        algorithm_id = data.get('algorithm_id')
        frequency = data.get('frequency')
        
        # Validate required fields
        if not algorithm_id or not frequency:
            await self.send_error("Missing algorithm_id or frequency")
            return
        
        # Generate group name using convention
        group_name = get_group_name(algorithm_id, frequency)
        
        # Check if already subscribed to this group
        if group_name in self.subscribed_groups:
            await self.send_error(f"Already subscribed to {group_name}")
            return
        
        try:
            # Join the channel group
            await self.channel_layer.group_add(group_name, self.channel_name)
            
            # Increment subscription count in Redis
            await database_sync_to_async(increment_group_subscription)(group_name)
            
            # Track the subscription locally
            self.subscribed_groups.add(group_name)
            
            logger.info(f"User {self.user_data.get('username')} subscribed to {group_name}")
            
            # Send success response with group name for UI storage
            await self.send(text_data=json.dumps({
                'type': 'subscription_success',
                'action': 'subscribe_scanner',
                'group_name': group_name,
                'algorithm_id': algorithm_id,
                'frequency': frequency,
                'message': f'Successfully subscribed to {group_name}'
            }))
            
        except Exception as e:
            logger.error(f"Error subscribing to {group_name}: {str(e)}")
            await self.send_error(f"Failed to subscribe to {group_name}")
    
    async def handle_unsubscribe_scanner(self, data):
        """Handle scanner unsubscription request"""
        algorithm_id = data.get('algorithm_id')
        frequency = data.get('frequency')
        
        # Validate required fields
        if not algorithm_id or not frequency:
            await self.send_error("Missing algorithm_id or frequency")
            return
        
        # Generate group name using convention
        group_name = get_group_name(algorithm_id, frequency)
        
        # Check if subscribed to this group
        if group_name not in self.subscribed_groups:
            await self.send_error(f"Not subscribed to {group_name}")
            return
        
        try:
            await self.leave_group(group_name)
            
            logger.info(f"User {self.user_data.get('username')} unsubscribed from {group_name}")
            
            # Send success response
            await self.send(text_data=json.dumps({
                'type': 'unsubscription_success',
                'action': 'unsubscribe_scanner',
                'group_name': group_name,
                'algorithm_id': algorithm_id,
                'frequency': frequency,
                'message': f'Successfully unsubscribed from {group_name}'
            }))
            
        except Exception as e:
            logger.error(f"Error unsubscribing from {group_name}: {str(e)}")
            await self.send_error(f"Failed to unsubscribe from {group_name}")
    
    async def leave_group(self, group_name):
        """Leave a group and decrement subscription count"""
        # Leave the channel group
        await self.channel_layer.group_discard(group_name, self.channel_name)
        
        # Decrement subscription count in Redis
        await database_sync_to_async(decrement_group_subscription)(group_name)
        
        # Remove from local tracking
        self.subscribed_groups.discard(group_name)
    
    async def scanner_update(self, event):
        """Handle scanner update messages from the group"""
        # Forward the message as-is to the WebSocket client
        await self.send(text_data=json.dumps(event['data']))
    
    async def send_error(self, message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))
    
    @database_sync_to_async
    def authenticate_user(self):
        """Authenticate user using JWT from cookies"""
        try:
            # Parse cookies from the connection scope
            cookies = {}
            for header_name, header_value in self.scope.get('headers', []):
                if header_name == b'cookie':
                    cookies = parse_cookie(header_value.decode())
                    break
            
            # Extract SLT token from cookies
            slt_token = cookies.get('slt')
            if not slt_token:
                logger.warning("No SLT token found in cookies")
                return None
            
            # Decode and validate the token
            payload = decode_slt(slt_token)
            if not payload:
                logger.warning("Invalid SLT token")
                return None
            
            return payload
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return None 