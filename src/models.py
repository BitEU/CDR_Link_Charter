# models.py
"""
Data models for the CDR Visualizer
"""

class PhoneNode:
    """
    Represents a phone number node in the CDR network
    """
    def __init__(self, phone_number, alias=""):
        self.phone_number = phone_number
        self.alias = alias  # Optional friendly name for the phone
        self.x = 0
        self.y = 0
        self.color = 0  # Index into CARD_COLORS array
        self.total_calls = 0  # Total calls made/received
        self.total_duration = 0  # Total duration in seconds
    
    def __repr__(self):
        return f"PhoneNode(number='{self.phone_number}', alias='{self.alias}')"
    
    def get_display_name(self):
        """Get display name - alias if available, otherwise phone number"""
        if self.alias:
            return f"{self.alias}\n{self.phone_number}"
        return self.phone_number
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            'phone_number': self.phone_number,
            'alias': self.alias,
            'x': self.x,
            'y': self.y,
            'color': self.color,
            'total_calls': self.total_calls,
            'total_duration': self.total_duration
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create PhoneNode from dictionary"""
        node = cls(
            phone_number=data.get('phone_number', ''),
            alias=data.get('alias', '')
        )
        node.x = data.get('x', 0)
        node.y = data.get('y', 0)
        node.color = data.get('color', 0)
        node.total_calls = data.get('total_calls', 0)
        node.total_duration = data.get('total_duration', 0)
        return node


class CallRecord:
    """
    Represents a single call record between two phones
    """
    def __init__(self, date, start_time, end_time, duration, direction):
        self.date = date
        self.start_time = start_time
        self.end_time = end_time
        self.duration = duration  # in seconds
        self.direction = direction  # 'Inbound' or 'Outbound'
    
    def to_dict(self):
        return {
            'date': self.date,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'direction': self.direction
        }