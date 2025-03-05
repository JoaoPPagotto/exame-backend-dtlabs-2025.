
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import models, schemas
from database import SessionLocal, engine
import secrets

app = FastAPI()

models.Base.metadata.create_all(bind=engine)


SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# Funções auxiliares
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@app.post("/auth/register")
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User created successfully"}


@app.post("/auth/login")
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token({"sub": user.username},
                                       expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/data")
def register_sensor_data(data: schemas.SensorDataCreate, db: Session = Depends(get_db)):
    if not any([data.temperature, data.humidity, data.voltage, data.current]):
        raise HTTPException(status_code=400, detail="At least one sensor value must be provided")

    server_exists = db.query(models.SensorData).filter(models.SensorData.server_ulid == data.server_ulid).first()
    if not server_exists:
        raise HTTPException(status_code=404, detail="Server ULID not found")

    db_data = models.SensorData(**data.dict())
    db.add(db_data)
    db.commit()
    db.refresh(db_data)
    return {"message": "Sensor data registered successfully"}


@app.get("/data")
def get_sensor_data(
        server_ulid: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        sensor_type: str | None = None,
        aggregation: str | None = Query(None, regex="^(minute|hour|day)$"),
        db: Session = Depends(get_db),
        token: str = Depends(oauth2_scheme)
):
    query = db.query(models.SensorData)

    if server_ulid:
        query = query.filter(models.SensorData.server_ulid == server_ulid)
    if start_time and end_time:
        query = query.filter(models.SensorData.timestamp.between(start_time, end_time))

    if aggregation:
        time_trunc = func.date_trunc(aggregation, models.SensorData.timestamp)
        query = query.group_by(time_trunc).with_entities(
            time_trunc.label("timestamp"),
            func.avg(getattr(models.SensorData, sensor_type)).label(sensor_type)
        )
    else:
        query = query.with_entities(models.SensorData.timestamp, getattr(models.SensorData, sensor_type))

    results = query.all()
    return results


@app.get("/health/{server_id}")
def check_server_health(server_id: str, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    last_data = db.query(models.SensorData).filter(models.SensorData.server_ulid == server_id).order_by(
        models.SensorData.timestamp.desc()).first()
    if not last_data:
        raise HTTPException(status_code=404, detail="Server not found")

    time_diff = datetime.utcnow() - last_data.timestamp
    status = "online" if time_diff.total_seconds() <= 10 else "offline"

    return {
        "server_ulid": server_id,
        "status": status,
        "server_name": last_data.server_name
    }


@app.get("/health/all")
def list_all_servers_health(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    servers = db.query(models.SensorData.server_ulid, models.SensorData.server_name,
                       func.max(models.SensorData.timestamp).label("last_timestamp")).group_by(
        models.SensorData.server_ulid, models.SensorData.server_name).all()

    server_health = []
    for server in servers:
        time_diff = datetime.utcnow() - server.last_timestamp
        status = "online" if time_diff.total_seconds() <= 10 else "offline"
        server_health.append({
            "server_ulid": server.server_ulid,
            "status": status,
            "server_name": server.server_name
        })

    return server_health


@app.get("/")
def read_root():
    return {"message": "API is running!"}