from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session

class PolicyRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    policy_id: Optional[int] = Field(default=None) # Smart Contract Policy ID
    flight_number: str
    coverage_amount: float
    customer_id: str
    phone_number: str
    customer_address: str
    status: str = Field(default="Satin Alindi - Bekliyor")

sqlite_file_name = "insurance_database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=False)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
