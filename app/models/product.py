from db.session import Base
from sqlalchemy import Column, Integer, String, Boolean,ForeignKey,Text,LargeBinary
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy import text
from sqlalchemy.orm import relationship

class Product(Base):
    __tablename__="shoes"
    id=Column(Integer,primary_key=True,nullable=False)
    name=Column(String,nullable=False)
    price=Column(Integer,nullable=False)
    product_mounts_type=Column(String,nullable=False)
    product_image=Column(String,nullable=False)
    product_mounts_category=Column(String,nullable=False)
    product_mounts_stock=Column(Integer,server_default=text('0'))
    product_mounts_description=Column(String,server_default=text("''"))
    created_at=Column(TIMESTAMP(timezone=True),nullable=False,server_default=text('CURRENT_TIMESTAMP'))
    
