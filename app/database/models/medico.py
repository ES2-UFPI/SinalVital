from sqlalchemy import Column, Integer, String

from app.database import Base


class Medico(Base):
    __tablename__ = "medicos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    # Identificador com UF (ex.: 000001-PI), evitando colisões entre estados.
    crm = Column(String(20), unique=True, nullable=False, index=True)
    especialidade = Column(String(100), nullable=False)
