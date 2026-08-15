from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import asyncio
import datetime
from decimal import Decimal
from typing import Optional

from db import engine, get_db, Base
import models
import schemas
import auth

# Initialize the database tables on startup
try:
    Base.metadata.create_all(bind=engine)
    print("MySQL database tables initialized successfully.")
except Exception as e:
    print(f"Warning: Could not create tables on startup. Ensure XAMPP MySQL server is running! Error: {e}")

app = FastAPI(title="ThreadCraft API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper function to seed realistic data for a beautiful initial dashboard experience
def seed_user_data(db: Session, user_id: int):
    # 1. Create premium default measurements
    meas = models.Measurement(
        user_id=user_id,
        bust=86.0,
        waist=70.0,
        hip=92.0,
        shoulder=38.0,
        sleeve=56.0,
        total_length=110.0,
        chest=84.0,
        inseam=72.0
    )
    db.add(meas)

    # 2. Create mock historical orders matching the premium portal mockup
    order1 = models.Order(
        order_number="TC-2026-00142",
        user_id=user_id,
        cloth_type="Midi Dress",
        material="Silk",
        fit="Slim fit",
        price=Decimal("9110.00"),
        status="Stitching",
        created_at=datetime.datetime.utcnow() - datetime.timedelta(days=4)
    )
    order2 = models.Order(
        order_number="TC-2026-00129",
        user_id=user_id,
        cloth_type="Saree Blouse",
        material="Cotton",
        fit="Fitted",
        price=Decimal("3820.00"),
        status="Dispatched",
        created_at=datetime.datetime.utcnow() - datetime.timedelta(days=19)
    )
    order3 = models.Order(
        order_number="TC-2026-00114",
        user_id=user_id,
        cloth_type="Kurta",
        material="Linen",
        fit="Regular fit",
        price=Decimal("5460.00"),
        status="Dispatched",
        created_at=datetime.datetime.utcnow() - datetime.timedelta(days=31)
    )
    db.add_all([order1, order2, order3])

    # 3. Create mock saved designs matching the premium portal mockup
    design1 = models.SavedDesign(
        user_id=user_id,
        name="Midi Dress",
        material="Chiffon",
        color="Burgundy",
        details="Draft saved for checkout",
        created_at=datetime.datetime.utcnow() - datetime.timedelta(days=7)
    )
    design2 = models.SavedDesign(
        user_id=user_id,
        name="Salwar Kameez",
        material="Silk",
        color="Deep Blue",
        details="Draft saved for checkout",
        created_at=datetime.datetime.utcnow() - datetime.timedelta(days=11)
    )
    db.add_all([design1, design2])
    db.commit()

@app.get("/")
def read_root():
    return {"message": "ThreadCraft API is running."}

# Auth Endpoints
@app.post("/api/auth/register", response_model=schemas.Token)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    # Create new user
    hashed_password = auth.get_password_hash(user_in.password)
    new_user = models.User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        email=user_in.email,
        password_hash=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Seed initial mock data for dashboard visuals
    try:
        seed_user_data(db, new_user.id)
    except Exception as e:
        print(f"Error seeding user data: {e}")

    # Generate token
    token = auth.create_access_token(data={"sub": new_user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "first_name": new_user.first_name,
            "last_name": new_user.last_name,
            "email": new_user.email
        }
    }

@app.post("/api/auth/login", response_model=schemas.Token)
def login(user_in: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if not user or not auth.verify_password(user_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email address or password."
        )

    token = auth.create_access_token(data={"sub": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email
        }
    }

# Dashboard Portal Endpoints
@app.get("/api/dashboard", response_model=schemas.DashboardData)
def get_dashboard(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    # Calculate stats
    total_orders = db.query(models.Order).filter(models.Order.user_id == current_user.id).count()
    active_orders_count = db.query(models.Order).filter(
        models.Order.user_id == current_user.id,
        models.Order.status.in_(["Received", "Stitching"])
    ).count()

    measurements_saved = current_user.measurements is not None
    
    # Grab detailed list of records
    recent_orders = db.query(models.Order).filter(
        models.Order.user_id == current_user.id
    ).order_by(models.Order.created_at.desc()).all()

    saved_designs = db.query(models.SavedDesign).filter(
        models.SavedDesign.user_id == current_user.id
    ).order_by(models.SavedDesign.created_at.desc()).all()

    return {
        "user": {
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "email": current_user.email,
            "created_at": current_user.created_at.strftime("Member since %b %Y")
        },
        "total_orders": total_orders,
        "active_orders_count": active_orders_count,
        "measurements_saved": measurements_saved,
        "measurements": current_user.measurements,
        "recent_orders": recent_orders,
        "saved_designs": saved_designs
    }

@app.put("/api/measurements", response_model=schemas.MeasurementOut)
def update_measurements(
    meas_in: schemas.MeasurementUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    meas = db.query(models.Measurement).filter(models.Measurement.user_id == current_user.id).first()
    if not meas:
        meas = models.Measurement(user_id=current_user.id)
        db.add(meas)
        
    for key, value in meas_in.dict().items():
        setattr(meas, key, value)
        
    db.commit()
    db.refresh(meas)
    return meas

# Order Endpoints (Supports guest orders and logged-in user database records)
@app.post("/api/orders")
async def create_order(
    order: schemas.OrderCreate, 
    authorization: Optional[str] = Header(None), 
    db: Session = Depends(get_db)
):
    # Check if this order is placed by an authenticated user
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
            email = payload.get("sub")
            if email:
                user = db.query(models.User).filter(models.User.email == email).first()
                if user:
                    user_id = user.id
        except Exception:
            pass # Fallback to guest order if token is expired or invalid

    # Calculate a randomized order number
    import random
    order_num = f"TC-2026-{random.randint(10000, 99999)}"
    
    # Calculate order price based on cloth type if not supplied
    price = order.price or 5000.0
    if not order.price:
        cloth_pricing = {
            "t-shirt": 2500.0,
            "shirt": 4500.0,
            "dress": 8500.0,
            "trousers": 6500.0,
            "kurta": 5500.0,
            "saree blouse": 3800.0,
            "salwar kameez": 7500.0,
            "skirt": 4000.0
        }
        price = cloth_pricing.get(order.clothType.lower(), 5000.0)

    # Save to database if user is logged in
    if user_id:
        new_order = models.Order(
            order_number=order_num,
            user_id=user_id,
            cloth_type=order.clothType,
            material=order.material,
            fit=order.fit,
            price=Decimal(str(price)),
            status="Received"
        )
        db.add(new_order)
        db.commit()

    return {
        "status": "success", 
        "order_id": order_num, 
        "message": "Order confirmed"
    }

@app.post("/api/mockup")
async def generate_mockup():
    # Simulate a delay for AI generation
    await asyncio.sleep(2)
    return {"status": "success", "mockup_url": "mockup_generated"}

@app.post("/api/designs", response_model=schemas.SavedDesignOut)
def save_design(
    design_in: schemas.SavedDesignCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    new_design = models.SavedDesign(
        user_id=current_user.id,
        name=design_in.name,
        material=design_in.material,
        color=design_in.color,
        details=design_in.details
    )
    db.add(new_design)
    db.commit()
    db.refresh(new_design)
    return new_design

@app.get("/api/designs")
def get_saved_designs(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    designs = db.query(models.SavedDesign).filter(models.SavedDesign.user_id == current_user.id).all()
    return designs
