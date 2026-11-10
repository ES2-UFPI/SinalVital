from sqlalchemy import Boolean, CheckConstraint, Column, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Medico(Base):
    __tablename__ = "medicos"
    __table_args__ = (
        CheckConstraint("capacidade_simultanea > 0", name="ck_medicos_capacidade_positiva"),
    )

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    especialidade = Column(String(100), nullable=False)
    capacidade_simultanea = Column(Integer, nullable=False, default=1)
    ativo = Column(Boolean, nullable=False, default=True)

    itens_fila = relationship("ItemFila", back_populates="medico")
