# Livraria — Exercício 6, Lab 05 (SDD)

Demonstração local de uma livraria com regras especificadas **antes** dos testes e da implementação. A fonte de verdade é [docs/specs/livraria.md](docs/specs/livraria.md); o acompanhamento verificável está em [docs/specs/tasks.md](docs/specs/tasks.md). Histórico Git: especificação → testes falhando → implementação → validação/ajustes.

## Instalar e executar

Requer Python **3.10+** e pip. Na pasta deste projeto:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -v
.venv/bin/python app.py
```

Abra **http://127.0.0.1:5000/**. Na primeira execução, `livraria.db` é criado e preenchido automaticamente. O catálogo contém 2 livros, 3 edições e 2 unidades de exemplo; executar novamente preserva cadastros e movimentações. Para recomeçar, remova `livraria.db` **com o servidor parado**, ou use outro banco: `LIVRARIA_DB=/caminho/novo.db .venv/bin/python app.py`. Testes usam SQLite temporário e não alteram o banco da aplicação. `LIVRARIA_SECRET` pode definir a chave de sessão para uma demonstração compartilhada.

## Percurso da interface

1. No catálogo, pesquise por título/autor/gênero e abra **A Casa das Marés**. Compare as edições, preços, avaliação, promoção e estoque por loja e seção.
2. Abra **Lojas** e filtre por bairro para consultar unidades, serviços, pagamentos, café e eventos de exemplo.
3. Em **Cadastro / entrada**, cadastre nome, email, bairro e interesse `Ficção`. Na área do cliente aparecem recomendação e aviso de promoção locais.
4. Volte ao livro e use **Reservar para retirada** em uma loja com estoque. A confirmação exibe o código `RES-...`, preço, seção e unidade; a unidade fica indisponível se era o último exemplar.
5. Em **Minha área**, use **Agilizar compra: retirar com código**; observe compra, histórico e pontos. Alternativamente, cancele uma reserva para devolver estoque ou compre diretamente da unidade.
6. Para uma edição esgotada, solicite aviso de reposição, clique **Simular +1 no estoque**, e consulte a notificação em **Minha área**. Salve/remova favoritos no detalhe/área.

## Simulações e limites

- SQLite é o único serviço exigido (integrado ao Python). Busca por bairro usa texto local, **não GPS** nem cálculo de distância.
- Pagamentos, compras e retirada são registros locais; **não há cobrança real**, integração com adquirentes, expiração automática de reservas ou autenticação de produção. Sessão é identificada pelo email cadastrado, sem senha.
- Reposição é acionada manualmente na interface; avisos de reposição e promoção aparecem apenas no banco/área do cliente, **sem email, push ou SMS**. Recomendações são calculadas por gênero de interesse; promoções e avaliações são dados fictícios locais.
- Valores monetários são guardados em centavos; fidelidade concede um ponto por real inteiro por compra concluída. Esta aplicação foi feita para execução demonstrativa local.

## Rastreabilidade e testes

`test_livraria.py` cobre **C01–C07** (incluindo filtros combinados, busca vazia, estoque independente, último exemplar, cadastro inválido e transições vedadas). `test_app.py` cobre **C08** via requisições HTTP à aplicação Flask. Execute com `.venv/bin/python -m unittest discover -v`.
