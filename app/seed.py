"""Pacientes e médicos fictícios para a demonstração: python -m app.seed."""

from sqlalchemy.orm import Session

from .database import Base, engine, SessionLocal
from .database.models import Medico, Paciente


PACIENTES_DEMONSTRACAO = (
    {"nome": "Raimundo Nonato", "email": "raimundo@example.com", "idade": 65,
     "condicao_cronica": "Cardiopatia e hipertensão", "gestante": False},
    {"nome": "Juscélio", "email": "juscelio@example.com", "gestante": False},
)

# Nomes fictícios com divisão explícita entre Urgência e Consultas Agendadas.
MEDICOS_DEMONSTRACAO = (
    # Médicos exclusivos de Urgência
    {
        "nome": "Helena",
        "especialidade": "cardiologia",
        "capacidade_simultanea": 2,
        "tipo_atendimento": "urgencia",
        "ativo": True,
    },
    {
        "nome": "Carlos",
        "especialidade": "clinica_geral",
        "capacidade_simultanea": 3,
        "tipo_atendimento": "urgencia",
        "ativo": True,
    },
    {
        "nome": "Jurinaldo",
        "especialidade": "clinica_geral",
        "capacidade_simultanea": 3,
        "tipo_atendimento": "urgencia",
        "ativo": True,
    },
    # Médicos de Consultas Agendadas (com dias de atendimento e limite diário)
    {
        "nome": "Ana",
        "especialidade": "oftalmologia",
        "capacidade_simultanea": 1,
        "tipo_atendimento": "agendamento",
        "dias_atendimento": "segunda,quarta",
        "limite_diario": 3,
        "ativo": True,
    },
    {
        "nome": "Mariana",
        "especialidade": "clinica_geral",
        "capacidade_simultanea": 2,
        "tipo_atendimento": "agendamento",
        "dias_atendimento": "segunda,quarta,sexta",
        "limite_diario": 5,
        "ativo": True,
    },
    {
        "nome": "Roberto",
        "especialidade": "cardiologia",
        "capacidade_simultanea": 2,
        "tipo_atendimento": "agendamento",
        "dias_atendimento": "terca,quinta",
        "limite_diario": 4,
        "ativo": True,
    },
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
            else:
                # Atualiza campos novos caso já exista de execuções anteriores
                if "tipo_atendimento" in dados:
                    existente.tipo_atendimento = dados["tipo_atendimento"]
                if "dias_atendimento" in dados:
                    existente.dias_atendimento = dados.get("dias_atendimento")
                if "limite_diario" in dados:
                    existente.limite_diario = dados.get("limite_diario")
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
