import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import String, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# -----------------------
# CONFIGURACIÓN DE BASE DE DATOS
# -----------------------

DATABASE_URL = "postgresql+asyncpg://contactosbd_user:HHlbXUNn3NFtG78NkcUR0a4HTbnGVmYp@dpg-da7kqnu7bikc73dnidig-a/contactosbd"

engine = create_async_engine(DATABASE_URL, echo=True)

# Uso moderno de async_sessionmaker en lugar de sessionmaker estándar
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

class ContactDB(Base):
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    nombres: Mapped[str] = mapped_column(String)
    telefono: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    direccion: Mapped[str] = mapped_column(String)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Dependencia para inyectar la sesión de DB en los endpoints
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

# -----------------------
# LIFESPAN (Manejador de ciclo de vida del App)
# -----------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código que corre al iniciar la app (Reemplaza a @app.on_event)
    await init_db()
    yield
    # Código que corre al apagar la app (si fuera necesario)

# Inicializar FastAPI con el lifespan
app = FastAPI(lifespan=lifespan)

# -----------------------
# MODELOS PYDANTIC (V2)
# -----------------------

class Contact(BaseModel):
    id: str | None = None
    nombres: str
    telefono: str
    email: str
    direccion: str

    # Configuración moderna de Pydantic V2
    model_config = ConfigDict(from_attributes=True)

# -----------------------
# CRUD ENDPOINTS
# -----------------------

@app.post("/contacts/", response_model=Contact)
async def create_contact(contact: Contact, db: AsyncSession = Depends(get_db)):
    db_contact = ContactDB(
        id=str(uuid.uuid4()),
        nombres=contact.nombres,
        telefono=contact.telefono,
        email=contact.email,
        direccion=contact.direccion
    )
    db.add(db_contact)
    await db.commit()
    await db.refresh(db_contact)
    return db_contact

@app.get("/contacts/", response_model=List[Contact])
async def get_contacts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContactDB))
    return result.scalars().all()

@app.get("/contacts/{contact_id}", response_model=Contact)
async def get_contact(contact_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContactDB).filter_by(id=contact_id))
    contact = result.scalars().first()

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    return contact

@app.put("/contacts/{contact_id}", response_model=Contact)
async def update_contact(
    contact_id: str, 
    updated_contact: Contact, 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ContactDB).filter_by(id=contact_id))
    db_contact = result.scalars().first()

    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    # model_dump ya estaba bien implementado, se mantiene igual
    for key, value in updated_contact.model_dump(exclude_unset=True).items():
        if key != "id":
            setattr(db_contact, key, value)

    await db.commit()
    await db.refresh(db_contact)
    return db_contact

@app.delete("/contacts/{contact_id}")
async def delete_contact(contact_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContactDB).filter_by(id=contact_id))
    db_contact = result.scalars().first()

    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    await db.delete(db_contact)
    await db.commit()
    return {"message": "Contact deleted successfully"}

@app.get("/")
def root():
    return {"message": "API running"}

