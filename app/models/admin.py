from db.session import Base
from sqlalchemy import Column, Integer, String, Boolean,ForeignKey,Text,LargeBinary
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy import text
from sqlalchemy.orm import relationship

class Admin(Base):
    __tablename__="admin"
    id=Column(Integer,primary_key=True,nullable=False)
    email=Column(String,nullable=False,unique=True)
    password=Column(String,nullable=False)
    created_at=Column(TIMESTAMP(timezone=True),nullable=False,server_default=text('CURRENT_TIMESTAMP'))
