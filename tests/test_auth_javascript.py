"""Executa JavaScript real via Node, integrado à descoberta do pytest/CI."""
from pathlib import Path
import shutil
import subprocess
import pytest


@pytest.mark.parametrize('script', ['auth.test.cjs', 'admin-api.test.cjs', 'admin-refresh.test.cjs'])
def test_fluxos_de_sessao_e_isolamento_no_javascript(script):
    node = shutil.which('node')
    assert node, 'Node.js é necessário para executar os testes de frontend.'
    resultado = subprocess.run(
        [node, '--test', f'tests/frontend/{script}'],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
        encoding='utf-8', timeout=30,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
