"""Pacientes e médicos fictícios para a demonstração: python -m app.seed."""

from sqlalchemy.orm import Session

from .database import Base, engine, SessionLocal
from .database.models import Medico, Paciente


PACIENTES_DEMONSTRACAO = (
    {"nome": "Raimundo Nonato", "email": "raimundo@example.com", "idade": 65,
     "condicao_cronica": "Cardiopatia e hipertensão"},
    {"nome": "Juscélio", "email": "juscelio@example.com"},
)

# Nomes e registros fictícios, exclusivamente para a demonstração.
MEDICOS_DEMONSTRACAO = (
    {"nome": "Helena", "crm": "000001-PI", "especialidade": "cardiologia"},
    {"nome": "Ana", "crm": "000002-PI", "especialidade": "oftalmologia"},
    {"nome": "Carlos", "crm": "000003-PI", "especialidade": "clinica_geral"},
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


def popular_medicos(db: Session) -> int:
    """Insere médicos ausentes por CRM, preservando os cadastros existentes."""
    inseridos = 0
    try:
        for dados in MEDICOS_DEMONSTRACAO:
            if db.query(Medico).filter(Medico.crm == dados["crm"]).first() is None:
                db.add(Medico(**dados))
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
        medicos_inseridos = popular_medicos(db)
    print(f"Seed concluído: {inseridos} paciente(s) e {medicos_inseridos} médico(s) inserido(s).")


if __name__ == "__main__":
    main()
