"""
geometry.py
Utility classes for geometry operations

author: jahyun koo (jhkoo77@gmail.com)
date: 2026
license: MIT License
copyright: (c) 2026 jhkoo77@gmail.com
"""


# point class for coordinate
class Point:
    """
    Point class for representing 2D coordinates.
    
    Attributes:
        x (float): X coordinate
        y (float): Y coordinate
    """
    
    def __init__(self, x: float, y: float):
        """
        Initialize point with coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
        """
        self.x = x
        self.y = y

    def dist(self, dest: 'Point') -> float:
        """
        Calculate Euclidean distance to another point.
        
        Note: If this point is at origin (0, 0), it will be updated to dest's position.
        This is a side effect for handling uninitialized points.
        
        Args:
            dest: Destination point
            
        Returns:
            Distance between this point and destination point
        """
        if self.x == 0 and self.y == 0:
            self.x = dest.x
            self.y = dest.y

        return ((self.x - dest.x) ** 2 + (self.y - dest.y) ** 2) ** 0.5

    def __str__(self) -> str:
        """String representation of the point."""
        return f'x = {self.x}, y = {self.y}'
    
    def __repr__(self) -> str:
        """Official string representation of the point."""
        return f'Point({self.x}, {self.y})'


# rectangle class for bounding box
class Rect:
    """
    Rectangle class for representing bounding boxes.
    
    Attributes:
        x1 (float): Left x coordinate
        y1 (float): Top y coordinate
        x2 (float): Right x coordinate
        y2 (float): Bottom y coordinate
    """
    
    def __init__(self, x1: float, y1: float, x2: float, y2: float):
        """Initialize rectangle with coordinates."""
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    @classmethod
    def from_point(cls, point: 'Point', expand: float) -> 'Rect':
        """
        Create a rectangle centered at a point with expansion.
        
        Args:
            point: Center point
            expand: Expansion distance in all directions
            
        Returns:
            New Rect instance
        """
        return cls(
            point.x - expand,
            point.y - expand,
            point.x + expand,
            point.y + expand
        )

    def union(self, target: 'Rect') -> 'Rect':
        """
        Create a union rectangle that contains both rectangles.
        
        Args:
            target: Another rectangle to union with
            
        Returns:
            New Rect instance containing both rectangles
        """
        return Rect(
            min(self.x1, target.x1),
            min(self.y1, target.y1),
            max(self.x2, target.x2),
            max(self.y2, target.y2)
        )

    def to_tuple(self) -> tuple:
        """
        Convert rectangle to tuple format (x1, y1, x2, y2).
        
        Returns:
            Tuple of coordinates
        """
        return (self.x1, self.y1, self.x2, self.y2)

    def list(self) -> tuple:
        """
        Alias for to_tuple() for backward compatibility.
        
        Returns:
            Tuple of coordinates
        """
        return self.to_tuple()

    def width(self) -> float:
        """Get rectangle width."""
        return self.x2 - self.x1

    def height(self) -> float:
        """Get rectangle height."""
        return self.y2 - self.y1

    def is_empty(self) -> bool:
        """Check if rectangle is empty (all coordinates are zero)."""
        return self.x1 == 0 and self.y1 == 0 and self.x2 == 0 and self.y2 == 0

    def center(self) -> 'Point':
        """
        Get the center point of the rectangle.
        
        Returns:
            Point at the center of the rectangle
        """
        if self.is_empty():
            return Point(0, 0)

        x = self.x1 + self.width() / 2
        y = self.y1 + self.height() / 2
        return Point(x, y)

    def __str__(self) -> str:
        """String representation of the rectangle."""
        return f'x1 = {self.x1}, y1 = {self.y1}, x2 = {self.x2}, y2 = {self.y2}'

