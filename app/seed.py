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


def _popular_registros(
    db: Session, modelo, registros, campos_identificacao: tuple[str, ...],
    campos_atualizacao: tuple[str, ...] = (),
) -> int:
    """Insere ausentes e atualiza apenas campos autorizados presentes nos dados."""
    inseridos = 0
    try:
        for dados in registros:
            identificacao = {campo: dados[campo] for campo in campos_identificacao}
            existente = db.query(modelo).filter_by(**identificacao).first()
            if existente is None:
                db.add(modelo(**dados))
                inseridos += 1
            else:
                for campo in campos_atualizacao:
                    if campo in dados:
                        setattr(existente, campo, dados[campo])
        db.commit()
    except Exception:
        db.rollback()
        raise
    return inseridos


def popular_pacientes(db: Session) -> int:
    """Insere apenas pacientes ausentes, sem sobrescrever cadastros existentes."""
    return _popular_registros(db, Paciente, PACIENTES_DEMONSTRACAO, ("email",))


def popular_medicos(db: Session) -> int:
    """Preserva capacidade e ativo; sincroniza os campos de agenda definidos no seed."""
    return _popular_registros(
        db, Medico, MEDICOS_DEMONSTRACAO, ("nome", "especialidade"),
        campos_atualizacao=("tipo_atendimento", "dias_atendimento", "limite_diario"),
    )


def main():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        inseridos = popular_pacientes(db)
        medicos_inseridos = popular_medicos(db)
    print(f"Seed concluído: {inseridos} paciente(s) e {medicos_inseridos} médico(s) inserido(s).")


if __name__ == "__main__":
    main()
