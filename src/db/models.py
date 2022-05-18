from sqlalchemy import Column, String, Integer, Boolean, Float, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base


async def wrapped_models(Base: declarative_base):
    class Transactions(Base):
        __tablename__ = 'transactions'

        id = Column(Integer, primary_key=True, autoincrement=True)
        timestamp = Column(Integer)
        tx = Column(String)
        block = Column(Integer)
        contract = Column(String)
        gas = Column(Integer)
        gas_price = Column(Integer)
        priority_fee = Column(Integer)

    class Blocks(Base):
        __tablename__ = 'blocks'

        id = Column(Integer, primary_key=True, autoincrement=True)
        block = Column(Integer)
        block_hash = Column(String)
        gas_used_total = Column(Integer)
        gas_limit_total = Column(Integer)
        base_fee = Column(Integer)

    class Future(Base):
        __tablename__ = 'future'
        id = Column(Integer, primary_key=True, autoincrement=True)
        contract = Column(String)
        timestamp = Column(Integer)
        priority_fee = Column(Integer)
        priority_fee_lower = Column(Integer)
        priority_fee_upper = Column(Integer)

    return Transactions, Blocks, Future
