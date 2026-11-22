"""Executa JavaScript real via Node, integrado à descoberta do pytest/CI."""
from pathlib import Path
import shutil
import subprocess


def test_fluxos_de_sessao_e_isolamento_no_javascript():
    node = shutil.which('node')
    assert node, 'Node.js é necessário para executar os testes de frontend.'
    resultado = subprocess.run(
        [node, '--test', 'tests/frontend/auth.test.cjs'],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
        encoding='utf-8', timeout=30,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
