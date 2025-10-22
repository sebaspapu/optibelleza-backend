from pydantic import BaseModel, EmailStr
from datetime import datetime
from fastapi import UploadFile,File,Form
from typing import Optional,List

#class ShoesCreate(BaseModel):
class ProductMountsCreate(BaseModel):
    
    name:str
    price:int
    product_image:str
    product_mounts_category:str
    product_mounts_type:str
    product_mounts_stock:int
    product_mounts_description:str

#class ShoesUpdate(BaseModel):
class ProductMountsUpdate(BaseModel):
    
    name:str
    price:int
    
    product_mounts_category:str
    product_mounts_type:str
    product_mounts_stock:int
    product_mounts_description:str

class ProductSize(BaseModel):
    product_name:str
    size:int

#class Shoes(BaseModel):
class ProductMounts(BaseModel):
    name:str
    price:int
    product_image: str
    product_mounts_type:str
    product_mounts_category:str
    id:int
    product_mounts_stock:int
    product_mounts_description:str
    