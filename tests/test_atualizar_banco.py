import sqlite3

from scripts.atualizar_banco import atualizar_banco


def test_migracao_preserva_dados_backup_e_permite_nova_triagem(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.database.models.triagem import Triagem

    caminho = tmp_path / 'legado.db'
    with sqlite3.connect(caminho) as db:
        db.execute('''CREATE TABLE triagens (
            id INTEGER PRIMARY KEY, paciente_id INTEGER NOT NULL,
            texto_sintomas TEXT NOT NULL, urgencia VARCHAR(30) NOT NULL,
            especialidade VARCHAR(100) NOT NULL, justificativa TEXT,
            criado_em DATETIME NOT NULL)''')
        db.execute("""INSERT INTO triagens VALUES
            (1, 1, 'Relato anterior', 'alta', 'clinica_geral', 'Registro antigo',
            '2026-10-01 10:00:00')""")
    backup = atualizar_banco(caminho)
    assert backup is not None and backup.exists()
    with sqlite3.connect(backup) as copia:
        assert len(copia.execute('PRAGMA table_info(triagens)').fetchall()) == 7
        assert copia.execute('SELECT texto_sintomas FROM triagens').fetchone()[0] == 'Relato anterior'
    with sqlite3.connect(caminho) as db:
        assert db.execute('SELECT texto_sintomas, classificacao, prioridade FROM triagens').fetchone() == (
            'Relato anterior', 'laranja', 2)
    engine = create_engine(f'sqlite:///{caminho}')
    try:
        with Session(engine) as session:
            session.add(Triagem(paciente_id=1, relato='Tosse desde ontem',
                                classificacao='verde', prioridade=4,
                                justificativa='Termos identificados: tosse'))
            session.commit()
            assert session.query(Triagem).count() == 2
    finally:
        engine.dispose()
    assert atualizar_banco(caminho) is None
    assert len(list(tmp_path.glob('*.backup-*.db'))) == 1
