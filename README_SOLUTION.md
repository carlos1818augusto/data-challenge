# Looqbox Data Challenge - Solução

Esta solução contém as respostas em SQL, código Python reutilizável e artefatos gerados para o desafio técnico da Looqbox.

## Arquivos

- `sql/answers.sql`: consultas SQL das três perguntas.
- `src/db.py`: configuração do banco e criação da engine SQLAlchemy.
- `src/data_access.py`: função reutilizável `retrieve_data(product_code, store_code, date)`.
- `src/generate_outputs.py`: executa as respostas SQL, a transformação do caso 2, o gráfico IMDB e a geração do PDF.
- `output/`: CSVs gerados, gráfico PNG e PDF final.

## Como executar

Crie um arquivo `.env` a partir de `.env.example` e preencha `DB_PASSWORD`.

```powershell
py -m pip install -r requirements.txt
py src\generate_outputs.py
```

O schema do banco se chama `looqbox-challenge`, com hífen. O código Python conecta diretamente nesse schema; os arquivos SQL usam crase quando necessário.

## Observações

- O caso 1 usa SQL parametrizado e valida as datas antes da consulta.
- O caso 2 mantem as duas consultas do cliente inalteradas e aplica o filtro de datas solicitado no pandas.
- O caso 3 expande os gêneros da tabela IMDB separados por vírgula e compara os principais gêneros por receita média.
