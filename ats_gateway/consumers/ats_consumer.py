import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.http import parse_cookie
from ..utils.jwt_utils import decode_slt, decode_websocket_token
from ..utils.group_utils import (
    get_group_name, 
    increment_group_subscription, 
    decrement_group_subscription,
    cleanup_group_subscription
)
from ats_gateway.utils.logger import log

class ATSConsumer(AsyncWebsocketConsumer):
    """
    Professional WebSocket Consumer for ATS Real-Time Communication
    
    This consumer implements industry-standard WebSocket authentication using the 
    Sec-WebSocket-Protocol header approach (same pattern used by Kubernetes and Jupyter).
    
    Authentication Flow:
    1. Client sends SLT token via WebSocket subprotocol during handshake
    2. Server extracts and validates token from subprotocol
    3. Falls back to cookie authentication for backward compatibility
    4. Accepts connection only if authentication succeeds
    
    Features:
    - Scanner subscription management
    - Real-time trade updates
    - Group-based message routing
    - Automatic cleanup on disconnect
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subscribed_groups = set()  # Track groups this connection is subscribed to
        self.user_data = None
    
    async def connect(self):
        """Handle WebSocket connection with professional subprotocol authentication"""
        log(f"WebSocket connection attempt from {self.channel_name}", level="info")
        
        # Authenticate user using professional subprotocol method
        user_data = await self.authenticate_user()
        if not user_data:
            log(f"Authentication failed for {self.channel_name}", level="warning")
            await self.close(code=4001)  # Custom close code for auth failure
            return
        
        self.user_data = user_data
        log(f"User authenticated: {user_data.get('username')} on channel {self.channel_name}", level="info")
        
        # Accept connection with base protocol (Kubernetes/Jupyter pattern)
        await self.accept(subprotocol='ats.token.v1')
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'WebSocket connection established successfully',
            'user': user_data.get('username'),
            'channel_name': self.channel_name,
            'authentication_method': 'subprotocol'
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection and cleanup"""
        log(f"WebSocket disconnecting: {self.channel_name}, close_code: {close_code}", level="info")
        
        # Unsubscribe from all groups and decrement counters
        for group_name in self.subscribed_groups.copy():
            await self.leave_group(group_name)
        
        username = self.user_data.get('username') if self.user_data else 'unknown'
        log(f"User {username} disconnected successfully", level="info")

    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            log(f"Received action '{action}' from {self.channel_name}", level="info")
            
            if action == 'subscribe_scanner':
                await self.handle_subscribe_scanner(data)
            elif action == 'unsubscribe_scanner':
                await self.handle_unsubscribe_scanner(data)
            else:
                await self.send_error(f"Unknown action: {action}")
        
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            log(f"Error processing message: {str(e)}", level="error")
            await self.send_error("Internal server error")

    async def handle_subscribe_scanner(self, data):
        """Handle scanner subscription request"""
        algorithm_name = data.get('algorithm_name') or data.get('algorithm_id')  # Support both for backward compatibility
        frequency = data.get('frequency')
        
        # Validate required fields
        if not algorithm_name or not frequency:
            await self.send_error("Missing algorithm_name or frequency")
            return
        
        # Generate group name using convention
        group_name = get_group_name(algorithm_name, frequency)
        
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
            
            log(f"User {self.user_data.get('username')} subscribed to {group_name}", level="info")
            
            # Send success response
            await self.send(text_data=json.dumps({
                'type': 'subscription_success',
                'action': 'subscribe_scanner',
                'group_name': group_name,
                'algorithm_name': algorithm_name,
                'frequency': frequency,
                'message': f'Successfully subscribed to {group_name}'
            }))
            
        except Exception as e:
            log(f"Error subscribing to {group_name}: {str(e)}", level="error")
            await self.send_error(f"Failed to subscribe to {group_name}")

    async def handle_unsubscribe_scanner(self, data):
        """Handle scanner unsubscription request"""
        algorithm_name = data.get('algorithm_name') or data.get('algorithm_id')  # Support both for backward compatibility
        frequency = data.get('frequency')
        
        # Validate required fields
        if not algorithm_name or not frequency:
            await self.send_error("Missing algorithm_name or frequency")
            return
        
        # Generate group name using convention
        group_name = get_group_name(algorithm_name, frequency)
        
        # Check if subscribed to this group
        if group_name not in self.subscribed_groups:
            await self.send_error(f"Not subscribed to {group_name}")
            return
        
        try:
            await self.leave_group(group_name)
            
            log(f"User {self.user_data.get('username')} unsubscribed from {group_name}", level="info")
            
            # Send success response
            await self.send(text_data=json.dumps({
                'type': 'unsubscription_success',
                'action': 'unsubscribe_scanner',
                'group_name': group_name,
                'algorithm_name': algorithm_name,
                'frequency': frequency,
                'message': f'Successfully unsubscribed from {group_name}'
            }))
            
        except Exception as e:
            log(f"Error unsubscribing from {group_name}: {str(e)}", level="error")
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
        """
        Professional WebSocket Authentication using Sec-WebSocket-Protocol Header
        
        This method implements the industry-standard approach used by Kubernetes and Jupyter:
        1. Primary: Extract WebSocket token from WebSocket subprotocol header (30-second expiration)
        2. Fallback: Extract SLT token from WebSocket subprotocol header (15-minute expiration)
        3. Legacy: Extract SLT token from httpOnly cookies (backward compatibility)
        4. Validate token using appropriate JWT utilities
        
        Returns:
            dict: User data if authentication succeeds, None otherwise
        """
        try:
            token = None
            token_type = None
            
            # Method 1: Professional Sec-WebSocket-Protocol authentication (Primary)
            subprotocols = self.scope.get('subprotocols', [])
            
            for protocol in subprotocols:
                if protocol.startswith('ats.token.v1.'):
                    # Extract token from subprotocol: 'ats.token.v1.{token}'
                    token = protocol[len('ats.token.v1.'):]
                    log("Token found in subprotocol (professional method)", level="info")
                    break
            
            # Method 2: Cookie authentication (Fallback for backward compatibility)
            if not token:
                cookies = {}
                for header_name, header_value in self.scope.get('headers', []):
                    if header_name == b'cookie':
                        cookies = parse_cookie(header_value.decode())
                        break
                
                token = cookies.get('slt')
                if token:
                    log("Token found in cookies (fallback method)", level="info")
            
            if not token:
                log("No token found in subprotocols or cookies", level="warning")
                return None
            
            # Try to validate as WebSocket token first (preferred for security)
            payload = decode_websocket_token(token)
            if payload:
                log(f"WebSocket token authenticated successfully: {payload.get('username')} (30-second expiration, dedicated secret key)", level="info")
                return payload
            
            # Fallback to regular SLT token validation
            payload = decode_slt(token)
            if payload:
                log(f"SLT token authenticated successfully: {payload.get('username')} (15-minute expiration)", level="info")
                return payload
            
            log("Invalid token provided - neither WebSocket nor SLT token", level="warning")
            return None
            
        except Exception as e:
            log(f"Authentication error: {str(e)}", level="error")
            return None