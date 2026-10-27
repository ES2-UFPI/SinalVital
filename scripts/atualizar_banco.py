"""Atualiza o SQLite legado sem remover dados: python -m scripts.atualizar_banco."""
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from sqlalchemy.engine import make_url

from app.database.database import DATABASE_URL


COLUNAS = {
    "estrategia": "VARCHAR(50) NOT NULL DEFAULT 'palavras_chave'",
    "classificacao": "VARCHAR(20) NOT NULL DEFAULT 'azul'",
    "prioridade": "INTEGER NOT NULL DEFAULT 5",
}


def atualizar_banco(caminho: Path) -> Path | None:
    """Faz backup consistente antes de adicionar as colunas ausentes."""
    caminho = caminho.resolve(strict=True)
    with sqlite3.connect(caminho) as db:
        existentes = {linha[1] for linha in db.execute('PRAGMA table_info(triagens)')}
        if not existentes:
            raise ValueError('Tabela triagens não encontrada. Execute o seed primeiro.')
        ausentes = [nome for nome in COLUNAS if nome not in existentes]
        if not ausentes:
            return None
        data = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup = caminho.with_name(f'{caminho.stem}.backup-{data}.db')
        with sqlite3.connect(backup) as copia:
            db.backup(copia)
        # SQLite garante rollback dos ALTER TABLE e UPDATE em caso de falha.
        db.execute('BEGIN IMMEDIATE')
        try:
            for nome in ausentes:
                db.execute(f'ALTER TABLE triagens ADD COLUMN {nome} {COLUNAS[nome]}')
            if 'classificacao' in ausentes:
                db.execute("""UPDATE triagens SET classificacao = CASE urgencia
                    WHEN 'emergencia' THEN 'vermelho'
                    WHEN 'alta' THEN 'laranja'
                    WHEN 'media' THEN 'amarelo'
                    WHEN 'baixa' THEN 'verde'
                    ELSE 'azul' END""")
            if 'prioridade' in ausentes:
                db.execute("""UPDATE triagens SET prioridade = CASE classificacao
                    WHEN 'vermelho' THEN 1 WHEN 'laranja' THEN 2
                    WHEN 'amarelo' THEN 3 WHEN 'verde' THEN 4 ELSE 5 END""")
            db.commit()
        except Exception:
            db.rollback()
            raise
        return backup


def main():
    url = make_url(DATABASE_URL)
    if url.get_backend_name() != 'sqlite' or not url.database or url.database == ':memory:':
        raise ValueError('Este script atualiza somente um arquivo SQLite local.')
    backup = atualizar_banco(Path(url.database))
    if backup:
        print(f'Banco atualizado sem remover registros. Backup: {backup}')
    else:
        print('Banco já atualizado; nenhuma alteração necessária.')


if __name__ == '__main__':
    main()
