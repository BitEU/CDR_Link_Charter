# models.py
"""
Data models for the People Connection Visualizer
"""

class Person:
    """
    Represents a person in the connection network
    """
    def __init__(self, name, dob="", alias="", address="", phone="", color=0):
        self.name = name
        self.dob = dob
        self.alias = alias
        self.address = address
        self.phone = phone
        self.x = 0
        self.y = 0
        self.color = color  # Index into CARD_COLORS array
        self.connections = {}  # {person_id: label}
        self.files = []  # List of attached file paths
    
    def __repr__(self):
        return f"Person(name='{self.name}', connections={len(self.connections)})"
    
    def add_connection(self, person_id, label):
        """Add a connection to another person"""
        self.connections[person_id] = label
    def remove_connection(self, person_id):
        """Remove a connection to another person"""
        if person_id in self.connections:
            del self.connections[person_id]
    
    def has_connection(self, person_id):
        """Check if connected to another person"""
        return person_id in self.connections
    
    def get_connection_label(self, person_id):
        """Get the label for a connection"""
        return self.connections.get(person_id, "")
    
    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'dob': self.dob,
            'alias': self.alias,
            'address': self.address,
            'phone': self.phone,
            'x': self.x,
            'y': self.y,
            'color': self.color,
            'connections': self.connections,
            'files': self.files
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create Person from dictionary"""
        person = cls(
            name=data.get('name', ''),
            dob=data.get('dob', ''),
            alias=data.get('alias', ''),
            address=data.get('address', ''),
            phone=data.get('phone', ''),
            color=data.get('color', 0)
        )
        person.x = data.get('x', 0)
        person.y = data.get('y', 0)
        person.connections = data.get('connections', {})
        person.files = data.get('files', [])
        return person