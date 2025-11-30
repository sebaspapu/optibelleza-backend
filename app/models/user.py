from db.session import Base
from sqlalchemy import Column, Integer, String, Boolean,ForeignKey,Text,LargeBinary
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy import text
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, nullable=False)
    user_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    login_status = Column(Boolean, nullable=False, server_default=text('0'))
    online_status = Column(Boolean, nullable=False, server_default=text('0'))
    total_quantity = Column(Integer, nullable=False, server_default=text('0'))
    total_purchase = Column(Integer, nullable=False, server_default=text('0'))
    user_address = Column(String, nullable=False, server_default=text("'None'"))  # Added single quotes around 'None'
    user_phone_no = Column(String, nullable=False, server_default=text("''"))  # Set default to empty string
    payment_status = Column(String, nullable=False, server_default=text("'pending'"))
    payment_id = Column(String, nullable=True)
    stripe_session_id = Column(String, nullable=True)
    product_id = Column(Integer, ForeignKey("shoes.id", ondelete="SET NULL"), nullable=True)