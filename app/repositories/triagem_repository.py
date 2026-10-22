from sqlalchemy.orm import Session

from app.database.models.paciente import Paciente
from app.database.models.triagem import Triagem


class TriagemRepository:
    def __init__(self, db: Session):
        self.db = db

    def paciente_existe(self, paciente_id: int) -> bool:
        return self.db.get(Paciente, paciente_id) is not None

    def salvar(self, triagem: Triagem) -> Triagem:
        self.db.add(triagem)
        self.db.commit()
        self.db.refresh(triagem)
        return triagem