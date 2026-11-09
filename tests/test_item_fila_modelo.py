from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.database.models import ItemFila, Medico, Paciente, Triagem
from app.api.schemas.item_fila import (
    ItemFilaCreate,
    ItemFilaEntrada,
    ItemFilaResponse,
    ItemFilaResposta,
)


@pytest.fixture
def db(tmp_path):
    """Fixture de banco SQLite isolado para testes do modelo ItemFila."""
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'teste_fila.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session
    engine.dispose()


def _criar_cenario_base(db):
    """Auxiliar para criar um paciente, uma triagem e um médico."""
    paciente = Paciente(nome="Maria de Sousa", email="maria@example.com", idade=58)
    db.add(paciente)
    db.commit()

    triagem = Triagem(
        paciente_id=paciente.id,
        texto_sintomas="Falta de ar moderada",
        urgencia="alta",
        especialidade="cardiologia",
    )
    db.add(triagem)

    medico = Medico(
        nome="Dr. Roberto Silva",
        especialidade="cardiologia",
        capacidade_simultanea=2,
        ativo=True,
    )
    db.add(medico)
    db.commit()
    db.refresh(paciente)
    db.refresh(triagem)
    db.refresh(medico)
    return paciente, triagem, medico


# ===========================================================================
# Testes de Criação no Banco
# ===========================================================================

def test_criar_item_fila_com_medico_alocado(db):
    """Cria item na fila associado a paciente, triagem e médico alocado."""
    paciente, triagem, medico = _criar_cenario_base(db)

    item = ItemFila(
        paciente_id=paciente.id,
        triagem_id=triagem.id,
        medico_id=medico.id,
        status="aguardando",
        score=55.0,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    assert item.id is not None
    assert item.paciente_id == paciente.id
    assert item.triagem_id == triagem.id
    assert item.medico_id == medico.id
    assert item.status == "aguardando"
    assert item.score == 55.0
    assert item.criado_em is not None

    # Vínculos ORM diretos
    assert item.paciente.nome == "Maria de Sousa"
    assert item.triagem.urgencia == "alta"
    assert item.medico.nome == "Dr. Roberto Silva"

    # Vínculos ORM reversos
    assert len(paciente.itens_fila) == 1
    assert paciente.itens_fila[0].id == item.id
    assert triagem.item_fila.id == item.id
    assert len(medico.itens_fila) == 1
    assert medico.itens_fila[0].id == item.id


def test_criar_item_fila_sem_medico_opcional(db):
    """Cria item na fila sem médico alocado (aguardando vaga)."""
    paciente, triagem, _ = _criar_cenario_base(db)

    item = ItemFila(
        paciente_id=paciente.id,
        triagem_id=triagem.id,
        medico_id=None,
        status="aguardando",
        score=30.0,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    assert item.id is not None
    assert item.medico_id is None
    assert item.medico is None
    assert item.paciente_id == paciente.id
    assert item.triagem_id == triagem.id


def test_valores_padrao_do_item_fila(db):
    """Verifica se status='aguardando' e score=0.0 são atribuídos por padrão."""
    paciente, triagem, _ = _criar_cenario_base(db)

    item = ItemFila(
        paciente_id=paciente.id,
        triagem_id=triagem.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    assert item.status == "aguardando"
    assert item.score == 0.0
    assert item.medico_id is None
    assert item.criado_em is not None
    assert isinstance(item.criado_em, datetime)


# ===========================================================================
# Testes de Consulta no Banco
# ===========================================================================

def test_consultar_item_fila_por_id(db):
    """Consulta item da fila pela chave primária."""
    paciente, triagem, medico = _criar_cenario_base(db)
    item = ItemFila(
        paciente_id=paciente.id,
        triagem_id=triagem.id,
        medico_id=medico.id,
        score=75.0,
    )
    db.add(item)
    db.commit()

    consultado = db.get(ItemFila, item.id)
    assert consultado is not None
    assert consultado.id == item.id
    assert consultado.paciente.email == "maria@example.com"
    assert consultado.medico.especialidade == "cardiologia"


def test_consultar_itens_fila_por_status(db):
    """Consulta itens filtrando por status (ex: aguardando vs em_atendimento)."""
    paciente, triagem, medico = _criar_cenario_base(db)

    item1 = ItemFila(
        paciente_id=paciente.id,
        triagem_id=triagem.id,
        medico_id=None,
        status="aguardando",
        score=10.0,
    )
    item2 = ItemFila(
        paciente_id=paciente.id,
        triagem_id=triagem.id,
        medico_id=medico.id,
        status="em_atendimento",
        score=50.0,
    )
    db.add_all([item1, item2])
    db.commit()

    aguardando = db.query(ItemFila).filter(ItemFila.status == "aguardando").all()
    assert len(aguardando) == 1
    assert aguardando[0].id == item1.id

    em_atendimento = db.query(ItemFila).filter(ItemFila.status == "em_atendimento").all()
    assert len(em_atendimento) == 1
    assert em_atendimento[0].id == item2.id


def test_consultar_itens_fila_sem_medico_alocado(db):
    """Consulta pacientes que aguardam alocação de médico."""
    paciente, triagem, medico = _criar_cenario_base(db)

    sem_medico = ItemFila(
        paciente_id=paciente.id,
        triagem_id=triagem.id,
        medico_id=None,
    )
    com_medico = ItemFila(
        paciente_id=paciente.id,
        triagem_id=triagem.id,
        medico_id=medico.id,
    )
    db.add_all([sem_medico, com_medico])
    db.commit()

    pendentes = db.query(ItemFila).filter(ItemFila.medico_id.is_(None)).all()
    assert len(pendentes) == 1
    assert pendentes[0].id == sem_medico.id

    alocados = db.query(ItemFila).filter(ItemFila.medico_id == medico.id).all()
    assert len(alocados) == 1
    assert alocados[0].id == com_medico.id


def test_consultar_ordenacao_da_fila_por_score_e_espera(db):
    """
    Testa a ordenação consistente da espera da fila:
    maior score primeiro (DESC); em caso de empate, quem chegou antes (criado_em ASC).
    """
    paciente, triagem, _ = _criar_cenario_base(db)
    agora = datetime.now(timezone.utc)

    # Três itens com diferentes prioridades e horários
    item_baixa_antigo = ItemFila(
        paciente_id=paciente.id,
        triagem_id=triagem.id,
        score=10.0,
        criado_em=agora - timedelta(minutes=40),
    )
    item_emergencia = ItemFila(
        paciente_id=paciente.id,
        triagem_id=triagem.id,
        score=100.0,
        criado_em=agora,
    )
    item_media_recente = ItemFila(
        paciente_id=paciente.id,
        triagem_id=triagem.id,
        score=30.0,
        criado_em=agora - timedelta(minutes=5),
    )
    item_media_antigo = ItemFila(
        paciente_id=paciente.id,
        triagem_id=triagem.id,
        score=30.0,
        criado_em=agora - timedelta(minutes=20),
    )

    db.add_all([item_baixa_antigo, item_emergencia, item_media_recente, item_media_antigo])
    db.commit()

    ordenados = (
        db.query(ItemFila)
        .order_by(ItemFila.score.desc(), ItemFila.criado_em.asc())
        .all()
    )

    ids_ordenados = [item.id for item in ordenados]
    esperado = [
        item_emergencia.id,       # score 100.0
        item_media_antigo.id,     # score 30.0 (chegou 20 min atrás)
        item_media_recente.id,    # score 30.0 (chegou 5 min atrás)
        item_baixa_antigo.id,     # score 10.0
    ]
    assert ids_ordenados == esperado


def test_atualizar_item_fila_alocando_medico(db):
    """Testa atualizar o status e alocar um médico a um item da fila."""
    paciente, triagem, medico = _criar_cenario_base(db)

    item = ItemFila(
        paciente_id=paciente.id,
        triagem_id=triagem.id,
        medico_id=None,
        status="aguardando",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    assert item.medico_id is None

    # Aloca médico e muda status
    item.medico_id = medico.id
    item.status = "em_atendimento"
    db.commit()
    db.refresh(item)

    assert item.medico_id == medico.id
    assert item.status == "em_atendimento"
    assert item.medico.nome == "Dr. Roberto Silva"


# ===========================================================================
# Testes de Deleção em Cascata
# ===========================================================================

def test_exclusao_paciente_remove_item_fila_em_cascata(db):
    """Excluir o paciente deve remover os seus itens da fila."""
    paciente, triagem, _ = _criar_cenario_base(db)
    item = ItemFila(paciente_id=paciente.id, triagem_id=triagem.id)
    db.add(item)
    db.commit()

    assert db.query(ItemFila).count() == 1
    db.delete(paciente)
    db.commit()
    assert db.query(ItemFila).count() == 0


def test_exclusao_triagem_remove_item_fila_em_cascata(db):
    """Excluir a triagem deve remover o item de fila correspondente."""
    paciente, triagem, _ = _criar_cenario_base(db)
    item = ItemFila(paciente_id=paciente.id, triagem_id=triagem.id)
    db.add(item)
    db.commit()

    assert db.query(ItemFila).count() == 1
    db.delete(triagem)
    db.commit()
    assert db.query(ItemFila).count() == 0


# ===========================================================================
# Testes dos Schemas Pydantic (Entrada e Saída)
# ===========================================================================

def test_schema_item_fila_create_valido_com_medico():
    """Valida ItemFilaCreate com médico preenchido."""
    dados = {
        "paciente_id": 1,
        "triagem_id": 2,
        "medico_id": 3,
        "status": "aguardando",
        "score": 85.5,
    }
    schema = ItemFilaCreate(**dados)
    assert schema.paciente_id == 1
    assert schema.triagem_id == 2
    assert schema.medico_id == 3
    assert schema.status == "aguardando"
    assert schema.score == 85.5


def test_schema_item_fila_create_sem_medico_opcional():
    """Valida ItemFilaCreate com médico omitido ou None."""
    schema = ItemFilaCreate(paciente_id=1, triagem_id=2)
    assert schema.paciente_id == 1
    assert schema.triagem_id == 2
    assert schema.medico_id is None
    assert schema.status == "aguardando"
    assert schema.score == 0.0

    schema_none = ItemFilaCreate(paciente_id=1, triagem_id=2, medico_id=None)
    assert schema_none.medico_id is None


def test_schema_item_fila_create_validacoes_de_erro():
    """Garante rejeição de valores inválidos no schema de entrada."""
    with pytest.raises(ValidationError):
        # paciente_id inválido
        ItemFilaCreate(paciente_id=0, triagem_id=1)

    with pytest.raises(ValidationError):
        # triagem_id inválido
        ItemFilaCreate(paciente_id=1, triagem_id=-1)

    with pytest.raises(ValidationError):
        # medico_id inválido (deve ser ge=1 se fornecido)
        ItemFilaCreate(paciente_id=1, triagem_id=1, medico_id=0)

    with pytest.raises(ValidationError):
        # score negativo
        ItemFilaCreate(paciente_id=1, triagem_id=1, score=-5.0)

    with pytest.raises(ValidationError):
        # status vazio
        ItemFilaCreate(paciente_id=1, triagem_id=1, status="   ")


def test_schema_item_fila_response_from_orm(db):
    """Valida serialização do schema de saída a partir de objeto ORM."""
    paciente, triagem, medico = _criar_cenario_base(db)
    item = ItemFila(
        paciente_id=paciente.id,
        triagem_id=triagem.id,
        medico_id=medico.id,
        status="aguardando",
        score=55.0,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    resposta = ItemFilaResponse.model_validate(item)
    dados = resposta.model_dump()

    assert dados["id"] == item.id
    assert dados["paciente_id"] == paciente.id
    assert dados["triagem_id"] == triagem.id
    assert dados["medico_id"] == medico.id
    assert dados["status"] == "aguardando"
    assert dados["score"] == 55.0
    assert dados["criado_em"] is not None
    assert dados["atualizado_em"] is None


def test_schema_item_fila_response_sem_medico(db):
    """Valida serialização do schema de saída quando não há médico alocado."""
    paciente, triagem, _ = _criar_cenario_base(db)
    item = ItemFila(
        paciente_id=paciente.id,
        triagem_id=triagem.id,
        medico_id=None,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    resposta = ItemFilaResponse.model_validate(item)
    assert resposta.medico_id is None
    assert resposta.id == item.id


def test_compatibilidade_aliases_em_portugues():
    """Garante que ItemFilaEntrada e ItemFilaResposta funcionam como aliases."""
    entrada = ItemFilaEntrada(paciente_id=10, triagem_id=20)
    assert isinstance(entrada, ItemFilaCreate)
    assert entrada.paciente_id == 10

    resposta = ItemFilaResposta(
        id=1,
        paciente_id=10,
        triagem_id=20,
        medico_id=None,
        status="aguardando",
        score=0.0,
        criado_em=datetime.now(timezone.utc),
    )
    assert isinstance(resposta, ItemFilaResponse)
    assert resposta.id == 1

