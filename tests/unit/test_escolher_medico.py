"""Comportamentos de seleção do médico definidos antes da implementação (#41)."""
from dataclasses import dataclass

import pytest

from app.domain.queue.motor_priorizacao import MotorPriorizacao


@dataclass(frozen=True)
class MedicoTeste:
    id: int
    especialidade: str = "cardiologia"
    capacidade_simultanea: int = 3
    ativo: bool = True


def escolher(medicos, cargas):
    return MotorPriorizacao.escolher_medico("cardiologia", medicos, cargas)


def test_escolhe_ativo_da_especialidade():
    esperado = MedicoTeste(3)
    medicos = [MedicoTeste(1, ativo=False), MedicoTeste(2, "oftalmologia"), esperado]
    assert escolher(medicos, {1: 0, 2: 0, 3: 1}) is esperado


@pytest.mark.parametrize("carga", [3, 4])
def test_ignora_capacidade_atingida_ou_excedida(carga):
    esperado = MedicoTeste(2, capacidade_simultanea=10)
    assert escolher([MedicoTeste(1), esperado], {1: carga, 2: 5}) is esperado


def test_prioriza_menor_carga_absoluta():
    esperado = MedicoTeste(2, capacidade_simultanea=2)
    # A escolha usa quantidade atual, e não percentual de ocupação.
    assert escolher([MedicoTeste(1, capacidade_simultanea=10), esperado], {1: 2, 2: 1}) is esperado


def test_carga_ausente_e_zero():
    esperado = MedicoTeste(2)
    assert escolher([MedicoTeste(1), esperado], {1: 1, 99: 0}) is esperado


@pytest.mark.parametrize("ordem", [(2, 1), (1, 2)])
def test_empate_desempata_por_menor_id(ordem):
    medicos = [MedicoTeste(i) for i in ordem]
    assert escolher(medicos, {1: 1, 2: 1}).id == 1


@pytest.mark.parametrize("medicos,cargas", [
    ([], {}),
    ([MedicoTeste(1, ativo=False)], {}),
    ([MedicoTeste(1, "oftalmologia")], {}),
    ([MedicoTeste(1)], {1: 3}),
    ([MedicoTeste(1)], {1: 4}),
])
def test_sem_vaga_retorna_none(medicos, cargas):
    assert escolher(medicos, cargas) is None


def test_selecao_nao_modifica_entradas():
    medicos = [MedicoTeste(2), MedicoTeste(1)]
    cargas = {1: 1, 2: 2}
    escolher(medicos, cargas)
    assert [m.id for m in medicos] == [2, 1]
    assert cargas == {1: 1, 2: 2}


def test_aceita_modelo_sqlalchemy_sem_sessao():
    from app.database.models import Medico

    medico = Medico(id=1, nome="Helena", especialidade="cardiologia",
                    capacidade_simultanea=2, ativo=True)
    assert escolher([medico], {1: 1}) is medico


def test_estado_de_espera_documentado():
    from app.domain.queue.motor_priorizacao import AGUARDANDO_VAGA_NA_ESPECIALIDADE

    assert AGUARDANDO_VAGA_NA_ESPECIALIDADE == "Aguardando vaga na especialidade"
