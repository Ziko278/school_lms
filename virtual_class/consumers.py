import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


class LiveSessionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'live_session_{self.session_id}'

        # Get user from scope
        self.user = self.scope.get('user', AnonymousUser())

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Notify others that someone joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user': self.user.get_full_name() if self.user.is_authenticated else 'Anonymous',
            }
        )

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # Notify others that someone left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user': self.user.get_full_name() if self.user.is_authenticated else 'Anonymous',
            }
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        # Handle different message types
        if message_type == 'whiteboard_update':
            # Broadcast whiteboard changes to everyone else
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'whiteboard_update',
                    'content': data.get('content'),
                    'user': self.user.get_full_name() if self.user.is_authenticated else 'Anonymous',
                }
            )
        elif message_type == 'chat_message':
            # Broadcast chat messages
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': data.get('message'),
                    'user': self.user.get_full_name() if self.user.is_authenticated else 'Anonymous',
                }
            )

    # Handler for whiteboard updates
    async def whiteboard_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'whiteboard_update',
            'content': event['content'],
            'user': event['user'],
        }))

    # Handler for chat messages
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'user': event['user'],
        }))

    # Handler for user joined
    async def user_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'user': event['user'],
        }))

    # Handler for user left
    async def user_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user': event['user'],
        }))