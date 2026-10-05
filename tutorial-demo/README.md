# Projeto de demonstração dos tutoriais (SinalVital)

Projeto mínimo usado nos exemplos e vídeo-aulas da Wiki. Não é o backend completo do SinalVital.

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # Windows: copy .env.example .env
uvicorn app.main:app --reload
```

- Documentação interativa: http://127.0.0.1:8000/docs
- Painel web: http://127.0.0.1:8000/painel/
