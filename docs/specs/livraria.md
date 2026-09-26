# Livraria — especificação da demonstração (fonte única de verdade)

## Escopo e dados

Aplicativo local Flask + SQLite. `init_db(caminho)` cria esquema e catálogo de demonstração idempotentemente. IDs inteiros; preços em centavos (inteiros, exibidos em reais); datas UTC ISO 8601. Dados iniciais: dois títulos (um com duas edições), dois autores/gêneros, duas lojas de bairros diferentes, estoques independentes, sinopses, avaliações, promoção, serviços e evento. Dados criados pelo usuário persistem no arquivo SQLite configurado em `LIVRARIA_DB` (padrão `livraria.db`). Testes usam bancos temporários. Nenhuma API externa é chamada.

Entidades: **Livro** (id, título, autor, gênero, sinopse); **Edição** (id, livro_id, nome, preço_centavos, ano); **Loja** (id, nome, bairro, endereço, horário, pagamentos, serviços, café booleano, eventos); **Estoque** (edicao_id, loja_id, quantidade >= 0, seção); **Avaliação** (livro_id, nota 1..5, texto, autor); **Promoção** (edicao_id, descrição, desconto_centavos, ativa); **Cliente** (id, nome, email único, bairro, interesses como gêneros); **Favorito** (cliente_id, livro_id); **Reserva** (id, cliente_id, edicao_id, loja_id, código único, estado `confirmada`/`retirada`/`cancelada`, preço_centavos); **Compra** (id, cliente_id, edicao_id, loja_id, preço_centavos, origem reserva opcional); **Alerta** (cliente_id, edicao_id, loja_id); **Notificação** (cliente_id, tipo, mensagem). Chaves estrangeiras e unicidade são aplicadas no SQLite.

## Regras e operações

R01. `buscar_livros(titulo, autor, genero)` aceita fragmentos sem diferenciar caixa/acentos, combina filtros com E, retorna títulos distintos em ordem de id; sem filtros retorna catálogo, sem resultado retorna lista vazia. `detalhes_livro` apresenta sinopse, avaliações, edições lado a lado (preço, ano), promoções ativas e estoque por loja com seção; edição inexistente ou IDs inválidos causam erro de domínio.

R02. Preço cobrado na reserva ou compra = preço da edição menos desconto ativo (nunca negativo); preço fica congelado no ato. Promoções não alteram quantidade; recomendações são outros livros cujo gênero está nos interesses do cliente, em ordem de id, sem favoritos já salvos. Favoritos são exclusivos por cliente/livro; adicionar/remover é idempotente.

R03. Lojas próximas são uma **simulação local**: informar bairro seleciona lojas cujo bairro contém o trecho (caixa/acentos ignorados); sem bairro mostra todas. Página mostra endereço, horários, formas de pagamento, serviços, café, eventos e seção do livro por unidade; não há GPS, distância ou geocodificação.

R04. Cadastro simples exige nome não vazio, email com formato simples `texto@dominio.sufixo` e único (sem diferenciar caixa), bairro não vazio; interesses são gêneros separados por vírgula. Sessão Flask guarda apenas o ID do cliente cadastrado/selecionado pelo email; não há senha nem autenticação de produção. Ações pessoais exigem cliente válido. Preferências geram recomendações locais; notificação de promoção é criada no cadastro para cada promoção ativa de gênero de interesse (uma por promoção nessa operação).

R05. Reserva para retirada exige estoque > 0 naquela loja/edição; transação atômica decrementa uma unidade imediatamente, gera código único `RES-<id com 6 dígitos>` e estado `confirmada`. Confirmar significa mostrar código, loja, seção, preço e estado; confirmação não é compra. Cancelar reserva confirmada repõe uma unidade e muda estado para `cancelada`; retirada de reserva confirmada muda estado para `retirada` e cria uma compra sem novo débito de estoque. Repetir retirada/cancelamento ou retirar reserva de outro cliente falha sem alterar estoque ou criar compra. Não há expiração automática. A compra presencial rápida permite retirar reserva mediante código (somente cliente dono) ou comprar diretamente da loja com estoque; compra direta decrementa uma unidade atomicamente. Histórico inclui compras e reservas, com valores e estados; pontos de fidelidade = soma de `preço_centavos // 100` por compra, sem pontos por reservas não retiradas. Pagamento é **simulação local**: nenhuma cobrança real, compra é registrada como paga na demonstração.

R06. Cliente pode solicitar alerta para edição esgotada em uma loja; alerta duplicado é ignorado. Botão de reposição **simulada** adiciona uma unidade à loja/edição e cria notificação local para assinantes, removendo alertas atendidos. Notificações ficam no banco e aparecem na área do cliente; nenhum email, push ou SMS é enviado. Promoções e recomendações são mostradas na interface, e notificações de promoção são geradas localmente no cadastro como em R04. Nenhuma origem externa de promoções ou avaliações: são dados de demonstração identificados como tais.

## Critérios de aceite (IDs usados nos testes)

**C01 — Busca e filtros (R01)**
- Dado o catálogo de exemplo, Quando busco por título, autor e gênero (inclusive combinados), Então recebo somente os títulos correspondentes sem diferenciar caixa/acentos.
- Dado um termo inexistente, Quando busco, Então recebo lista vazia.

**C02 — Detalhes e preços (R01,R02)**
- Dado um título com duas edições, Quando abro os detalhes, Então vejo sinopse, avaliações, preços/anos comparáveis, promoção e estoque/seção de cada loja.
- Dada uma promoção ativa, Quando reservo ou compro, Então o preço registrado é o preço da edição menos o desconto, sem valor negativo.

**C03 — Unidades (R03)**
- Dadas lojas em bairros diferentes, Quando filtro pelo bairro, Então vejo apenas unidades correspondentes com endereço, horário, pagamentos, serviços, café e eventos.
- Dado estoque de uma edição em lojas diferentes, Quando consulto disponibilidade, Então cada quantidade e seção pertence à loja correta.

**C04 — Cadastro e interesses (R04,R02)**
- Dado nome, email e bairro válidos, Quando cadastro cliente, Então seus interesses ficam registrados e posso salvar/remover favoritos e ver recomendações locais e avisos de promoção.
- Dados campos inválidos ou email repetido, Quando cadastro, Então recebo erro sem criar cliente.

**C05 — Reserva (R05)**
- Dado o último exemplar em uma loja, Quando reservo, Então recebo código/estado `confirmada` e o estoque dessa loja chega a zero sem afetar outras.
- Dado estoque zero, Quando tento reservar, Então a operação falha sem gerar reserva.
- Dada reserva confirmada, Quando cancelo, Então o estoque volta; Quando tento cancelar de novo, Então falha.

**C06 — Compra e fidelidade (R05)**
- Dada reserva confirmada, Quando retiro com código como cliente dono, Então ela passa a `retirada`, uma compra é registrada sem debitar novamente, e pontos aparecem no histórico.
- Dada reserva cancelada, retirada ou de outro cliente, Quando tento retirar, Então falha sem nova compra.
- Dado estoque disponível, Quando compro diretamente, Então há débito de uma unidade, histórico e pontos; com estoque zero, Então falha.

**C07 — Comunicação (R06)**
- Dado livro esgotado, Quando solicito alerta e simulo reposição, Então o estoque cresce, recebo notificação local e alerta é consumido.
- Dados interesses no cadastro, Quando consulto minha área, Então vejo recomendações e avisos de promoções relevantes, sem alegação de envio externo.

**C08 — Navegação (R01–R06)**
- Dado servidor Flask ativo, Quando navego por catálogo → detalhes → estoque por loja → reserva → confirmação, Então todas as ações funcionam via interface; lojas, cadastro, favoritos, compras, histórico, alertas e reposição também têm ações funcionais.
