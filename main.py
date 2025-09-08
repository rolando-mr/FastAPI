from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from typing import List
import uuid

# FastAPI app
app = FastAPI()

# SQLAlchemy setup
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./contacts.db"
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# SQLAlchemy model
class Base(DeclarativeBase):
    pass

class ContactDB(Base):
    __tablename__ = "contacts"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    nombres: Mapped[str] = mapped_column(String)
    telefono: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String)
    direccion: Mapped[str] = mapped_column(String)

# Create database tables
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Pydantic model for request/response
class Contact(BaseModel):
    id: str | None = None
    nombres: str
    telefono: str
    email: str
    direccion: str

# Create a new contact
@app.post("/contacts/", response_model=Contact)
async def create_contact(contact: Contact):
    async with Session(engine) as db:
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

# Read all contacts
@app.get("/contacts/", response_model=List[Contact])
async def get_contacts():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ContactDB))
        return result.scalars().all()

# Read a single contact by ID
@app.get("/contacts/{contact_id}", response_model=Contact)
async def get_contact(contact_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ContactDB).filter_by(id=contact_id))
        contact = result.scalars().first()
        if contact is None:
            raise HTTPException(status_code=404, detail="Contact not found")
        return contact

# Update a contact
@app.put("/contacts/{contact_id}", response_model=Contact)
async def update_contact(contact_id: str, updated_contact: Contact):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ContactDB).filter_by(id=contact_id))
        db_contact = result.scalars().first()
        if db_contact is None:
            raise HTTPException(status_code=404, detail="Contact not found")
        for key, value in updated_contact.dict(exclude_unset=True).items():
            setattr(db_contact, key, value)
        await db.commit()
        await db.refresh(db_contact)
        return db_contact

# Delete a contact
@app.delete("/contacts/{contact_id}")
async def delete_contact(contact_id: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(ContactDB).filter_by(id=contact_id))
        db_contact = result.scalars().first()
        if db_contact is None:
            raise HTTPException(status_code=404, detail="Contact not found")
        await db.delete(db_contact)
        await db.commit()
        return {"message": "Contact deleted successfully"}

# Run the application (for development)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)