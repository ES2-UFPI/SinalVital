from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.database import Base


class Consulta(Base):
    __tablename__ = "consultas"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("pacientes.id"), index=True)
    medico_id: Mapped[int] = mapped_column(ForeignKey("medicos.id"), index = True)
    anamnese: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnostico: Mapped[str] = mapped_column(Text, nullable=False)
    conduta:  Mapped[str] = mapped_column(Text, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
        )