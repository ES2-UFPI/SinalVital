"""Pacientes e médicos fictícios para a demonstração: python -m app.seed."""

from sqlalchemy.orm import Session

from .database import Base, engine, SessionLocal
from .database.models import Medico, Paciente


PACIENTES_DEMONSTRACAO = (
    {"nome": "Raimundo Nonato", "email": "raimundo@example.com", "idade": 65,
     "condicao_cronica": "Cardiopatia e hipertensão"},
    {"nome": "Juscélio", "email": "juscelio@example.com"},
)

# Nomes fictícios, exclusivamente para a demonstração.
MEDICOS_DEMONSTRACAO = (
    {"nome": "Helena", "especialidade": "cardiologia", "capacidade_simultanea": 2, "ativo": True},
    {"nome": "Ana", "especialidade": "oftalmologia", "capacidade_simultanea": 1, "ativo": True},
    {"nome": "Carlos", "especialidade": "clinica_geral", "capacidade_simultanea": 3, "ativo": True},
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
    """Identifica médicos da demo por nome e especialidade, preservando alterações."""
    inseridos = 0
    try:
        for dados in MEDICOS_DEMONSTRACAO:
            existente = db.query(Medico).filter_by(
                nome=dados["nome"], especialidade=dados["especialidade"]
            ).first()
            if existente is None:
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
