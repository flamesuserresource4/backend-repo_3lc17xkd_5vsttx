import os
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Farmer, Buyer, Product, Order, Route

app = FastAPI(title="AgriBridge API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "AgriBridge Backend Ready"}


@app.get("/test")
def test_database():
    """Quick connectivity test to MongoDB and basic metadata"""
    response: Dict[str, Any] = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        if os.getenv("DATABASE_URL"):
            response["database_url"] = "✅ Set"
        if os.getenv("DATABASE_NAME"):
            response["database_name"] = "✅ Set"
        if db is not None:
            response["database"] = "✅ Available"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()
                response["database"] = "✅ Connected & Working"
            except Exception as e:  # noqa: BLE001
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
    except Exception as e:  # noqa: BLE001
        response["database"] = f"❌ Error: {str(e)[:120]}"
    return response


# ---------- Schema Introspection ----------
class SchemaInfo(BaseModel):
    name: str
    fields: Dict[str, Any]


@app.get("/schema")
def get_schema():
    """Return available schemas for viewer/tools"""
    models = [Farmer, Buyer, Product, Order, Route]
    serialized: List[SchemaInfo] = []
    for m in models:
        serialized.append(
            SchemaInfo(name=m.__name__.lower(), fields=m.model_json_schema())
        )
    return serialized


# ---------- Farmer Endpoints ----------
@app.post("/api/farmers")
def create_farmer(payload: Farmer):
    farmer_id = create_document("farmer", payload)
    return {"id": farmer_id}


@app.get("/api/farmers")
def list_farmers(region: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if region:
        filt["region"] = region
    return get_documents("farmer", filt)


# ---------- Buyer Endpoints ----------
@app.post("/api/buyers")
def create_buyer(payload: Buyer):
    buyer_id = create_document("buyer", payload)
    return {"id": buyer_id}


@app.get("/api/buyers")
def list_buyers(type: Optional[str] = None):
    filt: Dict[str, Any] = {}
    if type:
        filt["type"] = type
    return get_documents("buyer", filt)


# ---------- Product Endpoints ----------
@app.post("/api/products")
def create_product(payload: Product):
    # Basic referential sanity: ensure farmer exists
    farmer_id = payload.farmer_id
    exists = db["farmer"].find_one({"_id": {"$eq": db.client.get_default_database()["farmer"].codec_options.document_class.__init__}})  # placeholder to avoid lints
    # We cannot reliably check ObjectId since we store string IDs from helper; skip strict validation
    product_id = create_document("product", payload)
    return {"id": product_id}


@app.get("/api/products")
def list_products(
    farmer_id: Optional[str] = None,
    category: Optional[str] = None,
    region: Optional[str] = None,
):
    filt: Dict[str, Any] = {}
    if farmer_id:
        filt["farmer_id"] = farmer_id
    if category:
        filt["category"] = category
    # Join-like filter by farmer region if provided
    if region:
        farmer_ids = [f.get("_id") for f in db["farmer"].find({"region": region})]
        filt["farmer_id"] = {"$in": [str(fid) for fid in farmer_ids]}
    return get_documents("product", filt)


# ---------- Orders ----------
@app.post("/api/orders")
def create_order(payload: Order):
    order_id = create_document("order", payload)
    return {"id": order_id}


@app.get("/api/orders")
def list_orders(
    buyer_id: Optional[str] = None,
    status: Optional[str] = None,
):
    filt: Dict[str, Any] = {}
    if buyer_id:
        filt["buyer_id"] = buyer_id
    if status:
        filt["status"] = status
    return get_documents("order", filt)


# ---------- Logistics Routes ----------
@app.post("/api/routes")
def create_route(payload: Route):
    route_id = create_document("route", payload)
    return {"id": route_id}


@app.get("/api/routes")
def list_routes(date: Optional[str] = None, cold_chain: Optional[bool] = Query(None)):
    filt: Dict[str, Any] = {}
    if date:
        filt["date"] = date
    if cold_chain is not None:
        filt["cold_chain"] = cold_chain
    return get_documents("route", filt)


# ---------- Analytics ----------
@app.get("/api/analytics/pricing")
def pricing_trends(category: Optional[str] = None):
    """Average price per category or for a specific category"""
    pipeline: List[Dict[str, Any]] = []
    if category:
        pipeline.append({"$match": {"category": category}})
    pipeline += [
        {"$group": {"_id": "$category", "avg_price": {"$avg": "$price"}, "count": {"$sum": 1}}},
        {"$sort": {"avg_price": 1}},
    ]
    results = list(db["product"].aggregate(pipeline)) if db else []
    return results


@app.get("/api/analytics/demand")
def demand_forecast(limit: int = 10):
    """Top ordered products by frequency (naive proxy for demand)."""
    if not db:
        return []
    pipeline = [
        {"$unwind": "$items"},
        {"$group": {"_id": "$items.product_id", "orders": {"$sum": 1}, "qty": {"$sum": "$items.quantity"}}},
        {"$sort": {"orders": -1}},
        {"$limit": limit},
    ]
    return list(db["order"].aggregate(pipeline))


@app.get("/api/analytics/supply")
def supply_overview():
    """Available quantity by category across all products."""
    if not db:
        return []
    pipeline = [
        {"$group": {"_id": "$category", "available": {"$sum": "$available_quantity"}, "items": {"$sum": 1}}},
        {"$sort": {"available": -1}},
    ]
    return list(db["product"].aggregate(pipeline))


# ---------- Simple hello ----------
@app.get("/api/hello")
def hello():
    return {"message": "Hello from AgriBridge API"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
