from agora_token_builder import RtcTokenBuilder
import time
from django.conf import settings

# Get these from Agora.io Console (https://console.agora.io/)
# For now, using placeholder - you'll replace these
AGORA_APP_ID = getattr(settings, 'AGORA_APP_ID', 'your_app_id_here')
AGORA_APP_CERTIFICATE = getattr(settings, 'AGORA_APP_CERTIFICATE', 'your_app_certificate_here')


def generate_agora_token(channel_name, uid=0, role='publisher', expiration_seconds=3600):
    """
    Generate Agora RTC token for video/audio

    Args:
        channel_name: Unique channel identifier
        uid: User ID (0 means Agora will assign)
        role: 'publisher' (can publish) or 'subscriber' (view only)
        expiration_seconds: Token validity duration

    Returns:
        token string
    """

    # Role mapping
    role_map = {
        'publisher': 1,  # ROLE_PUBLISHER
        'subscriber': 2,  # ROLE_SUBSCRIBER
    }

    privilege_expired_ts = int(time.time()) + expiration_seconds

    try:
        token = RtcTokenBuilder.buildTokenWithUid(
            AGORA_APP_ID,
            AGORA_APP_CERTIFICATE,
            channel_name,
            uid,
            role_map.get(role, 1),
            privilege_expired_ts
        )
        return token
    except Exception as e:
        print(f"Error generating Agora token: {e}")
        return None


def get_agora_credentials(channel_name, user_type='publisher'):
    """
    Get complete Agora credentials for frontend

    Args:
        channel_name: Channel to join
        user_type: 'publisher' (lecturer) or 'subscriber' (student)

    Returns:
        dict with app_id, channel, token
    """

    token = generate_agora_token(channel_name, role=user_type)

    return {
        'app_id': AGORA_APP_ID,
        'channel': channel_name,
        'token': token,
    }