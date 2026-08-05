import uuid

class MockVideoAdapter:
    @staticmethod
    def generate_token(identity: str, room_name: str) -> str:
        # Simulate generating a Twilio/Daily.co JWT token
        return f"mock_token_for_{identity}_in_{room_name}_{uuid.uuid4().hex}"

    @staticmethod
    def create_room(room_name: str) -> str:
        # Simulate creating a room and returning a room SID
        return f"RM{uuid.uuid4().hex[:32]}"
