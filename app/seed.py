"""Pacientes fictícios para a demonstração: python -m app.seed."""

from sqlalchemy.orm import Session

from .database import Base, engine, SessionLocal
from .models import Paciente


PACIENTES_DEMONSTRACAO = (
    {"nome": "Raimundo Nonato", "email": "raimundo@example.com", "idade": 65,
     "condicao_cronica": "Cardiopatia e hipertensão"},
    {"nome": "Juscélio", "email": "juscelio@example.com"},
)


def popular_pacientes(db: Session) -> int:
    """Insere apenas pacientes ausentes, sem sobrescrever cadastros existentes."""
    inseridos = 0
    try:
        for dados in PACIENTES_DEMONSTRACAO:
            if db.query(Paciente).filter(Paciente.email == dados["email"]).first() is None:
                db.add(Paciente(**dados))
                inseridos += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    return inseridos


def main():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        inseridos = popular_pacientes(db)
    print(f"Seed concluído: {inseridos} paciente(s) inserido(s).")


if __name__ == "__main__":
    main()
