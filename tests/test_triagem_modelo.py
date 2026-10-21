import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Paciente, Triagem
from app.schemas import TriagemEntrada, ResultadoClassificacao, TriagemResposta


@pytest.fixture
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'teste_triagem.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session
    engine.dispose()


def test_criar_triagem_e_relacionamento_com_paciente(db):
    paciente = Paciente(nome="Raimundo Nonato", email="raimundo@example.com", idade=65)
    db.add(paciente)
    db.commit()

    triagem = Triagem(
        paciente_id=paciente.id,
        texto_sintomas="Dor no peito e falta de ar há 30 minutos",
        urgencia="emergencia",
        especialidade="cardiologia",
        justificativa="Sintomas compatíveis com emergência cardiológica",
    )
    db.add(triagem)
    db.commit()
    db.refresh(paciente)

    assert triagem.id is not None
    assert triagem.criado_em is not None
    assert len(paciente.triagens) == 1
    assert paciente.triagens[0].urgencia == "emergencia"
    assert paciente.triagens[0].especialidade == "cardiologia"


def test_valores_padrao_da_triagem_no_banco(db):
    paciente = Paciente(nome="Ana Beatriz", email="ana@example.com")
    db.add(paciente)
    db.commit()

    triagem = Triagem(paciente_id=paciente.id, texto_sintomas="Dúvida sobre exame de rotina")
    db.add(triagem)
    db.commit()
    db.refresh(triagem)

    assert triagem.urgencia == "baixa"
    assert triagem.especialidade == "clinica_geral"
    assert triagem.justificativa is None


def test_exclusao_paciente_remove_triagens_em_cascata(db):
    paciente = Paciente(nome="Juscélio", email="juscelio@example.com")
    db.add(paciente)
    db.commit()

    triagem = Triagem(paciente_id=paciente.id, texto_sintomas="Coceira e olho seco")
    db.add(triagem)
    db.commit()

    assert db.query(Triagem).count() == 1
    db.delete(paciente)
    db.commit()
    assert db.query(Triagem).count() == 0


def test_validacao_schema_triagem_entrada():
    entrada = TriagemEntrada(paciente_id=1, texto_sintomas="  Dor de cabeça forte  ")
    assert entrada.paciente_id == 1
    assert entrada.texto_sintomas == "Dor de cabeça forte"

    with pytest.raises(ValidationError):
        TriagemEntrada(paciente_id=1, texto_sintomas="   ")

    with pytest.raises(ValidationError):
        TriagemEntrada(paciente_id=0, texto_sintomas="Febre alta")


def test_serializacao_schemas_saida_triagem(db):
    paciente = Paciente(nome="Raimundo Nonato", email="raimundo@example.com")
    db.add(paciente)
    db.commit()

    triagem = Triagem(
        paciente_id=paciente.id,
        texto_sintomas="Falta de ar súbita",
        urgencia="emergencia",
        especialidade="cardiologia",
        justificativa="Risco cardíaco elevado",
    )
    db.add(triagem)
    db.commit()
    db.refresh(triagem)

    resultado = ResultadoClassificacao.model_validate(triagem, from_attributes=True)
    assert resultado.urgencia == "emergencia"
    assert resultado.especialidade == "cardiologia"

    resposta = TriagemResposta.model_validate(triagem)
    dados = resposta.model_dump()
    assert dados["id"] == triagem.id
    assert dados["paciente_id"] == paciente.id
    assert dados["texto_sintomas"] == "Falta de ar súbita"
    assert dados["urgencia"] == "emergencia"
    assert dados["especialidade"] == "cardiologia"
    assert dados["justificativa"] == "Risco cardíaco elevado"
    assert dados["criado_em"] is not None