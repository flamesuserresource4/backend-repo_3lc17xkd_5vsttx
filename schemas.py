"""
Database Schemas for AgriBridge

Each Pydantic model represents a MongoDB collection. Collection name is the
lowercase class name (e.g., Farmer -> "farmer").

These schemas are used for validating incoming data before writing to the
database and for documenting your API.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Farmer(BaseModel):
    """
    Farmers collection schema
    Collection name: "farmer"
    """
    name: str = Field(..., description="Full name of the farmer")
    phone: str = Field(..., description="Contact phone number")
    region: str = Field(..., description="Region within Uzbekistan")
    farm_name: Optional[str] = Field(None, description="Farm or cooperative name")
    languages: List[str] = Field(default_factory=lambda: ["uz"], description="Preferred languages, e.g., ['uz','ru']")
    certifications: List[str] = Field(default_factory=list, description="List of certifications, e.g., GlobalGAP")
    bio: Optional[str] = Field(None, description="Short description or notes")


class Buyer(BaseModel):
    """
    Buyers collection schema
    Collection name: "buyer"
    """
    name: str = Field(..., description="Buyer name or contact person")
    type: str = Field(..., description="Type of buyer: consumer|restaurant|retailer|exporter")
    organization: Optional[str] = Field(None, description="Company/organization name if applicable")
    phone: str = Field(..., description="Contact phone number")
    region: Optional[str] = Field(None, description="Region/city")


class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product"
    """
    farmer_id: str = Field(..., description="ID of the farmer (string)")
    title: str = Field(..., description="Product name, e.g., 'Tomatoes'")
    category: str = Field(..., description="Category, e.g., 'Vegetables'")
    price: float = Field(..., ge=0, description="Unit price")
    unit: str = Field(..., description="Unit of measure, e.g., kg, box")
    available_quantity: float = Field(..., ge=0, description="Available quantity in unit")
    photos: List[str] = Field(default_factory=list, description="List of photo URLs")
    description: Optional[str] = Field(None, description="Product description")


class OrderItem(BaseModel):
    product_id: str = Field(..., description="Product ID (string)")
    quantity: float = Field(..., gt=0, description="Quantity ordered")
    price: float = Field(..., ge=0, description="Price per unit at time of order")


class Order(BaseModel):
    """
    Orders collection schema
    Collection name: "order"
    """
    buyer_id: str = Field(..., description="Buyer ID (string)")
    items: List[OrderItem] = Field(..., description="List of order items")
    status: str = Field("pending", description="Order status: pending|confirmed|in_transit|delivered|cancelled")
    delivery_method: str = Field("delivery", description="delivery|pickup")
    scheduled_date: Optional[str] = Field(None, description="ISO date for scheduled delivery/pickup")
    route_id: Optional[str] = Field(None, description="Assigned logistics route ID (string)")


class RouteStop(BaseModel):
    order_id: str = Field(..., description="Order ID served at this stop")
    location: Optional[str] = Field(None, description="Address or location description")
    eta: Optional[str] = Field(None, description="Estimated time of arrival (ISO datetime)")


class Route(BaseModel):
    """
    Logistics routes collection schema
    Collection name: "route"
    """
    date: str = Field(..., description="Route date (ISO date)")
    vehicle_type: Optional[str] = Field(None, description="Truck, van, etc.")
    cold_chain: bool = Field(False, description="Whether cold chain is required/available")
    stops: List[RouteStop] = Field(default_factory=list, description="List of stops on the route")
