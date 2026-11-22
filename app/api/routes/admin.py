"""Operações administrativas do protótipo, com senha verificada no servidor."""
import os
import secrets
from typing import Literal
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.database.models import Medico
from app.api.schemas.admin import MedicoAdminEntrada, MedicoAdminResposta, PacienteAdminResposta
from app.services.admin_service import listar_pacientes_atendimentos


def exigir_administrador(response: Response, x_admin_password: str | None = Header(default=None)):
    response.headers['Cache-Control'] = 'no-store'
    configurada = os.getenv('ADMIN_PASSWORD', '')
    if not configurada.strip():
        raise HTTPException(status_code=503, detail='Acesso administrativo não configurado no servidor.')
    if not x_admin_password or not secrets.compare_digest(x_admin_password.encode(), configurada.encode()):
        raise HTTPException(status_code=401, detail='Senha administrativa inválida.')


router = APIRouter(prefix='/admin', tags=['administracao'], dependencies=[Depends(exigir_administrador)])


@router.get('/medicos', response_model=list[MedicoAdminResposta])
def listar_medicos(db: Session = Depends(get_db)):
    return db.query(Medico).order_by(Medico.nome, Medico.id).all()


@router.post('/medicos', response_model=MedicoAdminResposta, status_code=201)
def cadastrar_medico(dados: MedicoAdminEntrada, db: Session = Depends(get_db)):
    existente = db.query(Medico).filter(
        func.lower(Medico.nome) == dados.nome.lower(), Medico.especialidade == dados.especialidade,
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail='Já existe um médico com esse nome e especialidade.')
    medico = Medico(**dados.model_dump())
    db.add(medico)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(medico)
    return medico


@router.get('/pacientes', response_model=list[PacienteAdminResposta])
def listar_pacientes(
    nome: str = Query(default='', max_length=120),
    etapa: Literal['todos', 'sem_atendimento', 'triagem', 'aguardando', 'em_atendimento',
                   'agendado', 'atendido', 'cancelado'] = 'todos',
    db: Session = Depends(get_db),
):
    return listar_pacientes_atendimentos(db, nome.strip(), etapa)
