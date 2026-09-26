"""Regras da demonstração, derivadas de docs/specs/livraria.md."""
import re
import sqlite3
import unicodedata
from contextlib import contextmanager


class RegraInvalida(ValueError):
    """Operação não permitida pela especificação."""


def normalizar(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", str(texto)).casefold()
                   if not unicodedata.combining(c))


def registro(row):
    return dict(row) if row else None


class Livraria:
    def __init__(self, caminho):
        self.caminho = str(caminho)

    @contextmanager
    def conexao(self):
        db = sqlite3.connect(self.caminho, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def init_db(self):
        with self.conexao() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS livros(id INTEGER PRIMARY KEY, titulo TEXT NOT NULL, autor TEXT NOT NULL, genero TEXT NOT NULL, sinopse TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS edicoes(id INTEGER PRIMARY KEY, livro_id INTEGER NOT NULL REFERENCES livros, nome TEXT NOT NULL, ano INTEGER NOT NULL, preco_centavos INTEGER NOT NULL CHECK(preco_centavos>=0));
                CREATE TABLE IF NOT EXISTS lojas(id INTEGER PRIMARY KEY, nome TEXT NOT NULL, bairro TEXT NOT NULL, endereco TEXT NOT NULL, horario TEXT NOT NULL, pagamentos TEXT NOT NULL, servicos TEXT NOT NULL, cafe INTEGER NOT NULL, eventos TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS estoques(edicao_id INTEGER NOT NULL REFERENCES edicoes, loja_id INTEGER NOT NULL REFERENCES lojas, quantidade INTEGER NOT NULL CHECK(quantidade>=0), secao TEXT NOT NULL, PRIMARY KEY(edicao_id,loja_id));
                CREATE TABLE IF NOT EXISTS avaliacoes(id INTEGER PRIMARY KEY, livro_id INTEGER NOT NULL REFERENCES livros, nota INTEGER NOT NULL CHECK(nota BETWEEN 1 AND 5), texto TEXT NOT NULL, autor TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS promocoes(id INTEGER PRIMARY KEY, edicao_id INTEGER NOT NULL REFERENCES edicoes, descricao TEXT NOT NULL, desconto_centavos INTEGER NOT NULL CHECK(desconto_centavos>=0), ativa INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS clientes(id INTEGER PRIMARY KEY, nome TEXT NOT NULL, email TEXT NOT NULL UNIQUE COLLATE NOCASE, bairro TEXT NOT NULL, interesses TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS favoritos(cliente_id INTEGER NOT NULL REFERENCES clientes, livro_id INTEGER NOT NULL REFERENCES livros, PRIMARY KEY(cliente_id,livro_id));
                CREATE TABLE IF NOT EXISTS reservas(id INTEGER PRIMARY KEY, cliente_id INTEGER NOT NULL REFERENCES clientes, edicao_id INTEGER NOT NULL REFERENCES edicoes, loja_id INTEGER NOT NULL REFERENCES lojas, codigo TEXT UNIQUE, estado TEXT NOT NULL CHECK(estado IN ('confirmada','retirada','cancelada')), preco_centavos INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS compras(id INTEGER PRIMARY KEY, cliente_id INTEGER NOT NULL REFERENCES clientes, edicao_id INTEGER NOT NULL REFERENCES edicoes, loja_id INTEGER NOT NULL REFERENCES lojas, preco_centavos INTEGER NOT NULL, reserva_id INTEGER UNIQUE REFERENCES reservas);
                CREATE TABLE IF NOT EXISTS alertas(cliente_id INTEGER NOT NULL REFERENCES clientes, edicao_id INTEGER NOT NULL REFERENCES edicoes, loja_id INTEGER NOT NULL REFERENCES lojas, PRIMARY KEY(cliente_id,edicao_id,loja_id));
                CREATE TABLE IF NOT EXISTS notificacoes(id INTEGER PRIMARY KEY, cliente_id INTEGER NOT NULL REFERENCES clientes, tipo TEXT NOT NULL, mensagem TEXT NOT NULL);
            """)
            if db.execute("SELECT 1 FROM livros LIMIT 1").fetchone():
                return
            db.executemany("INSERT INTO livros VALUES (?,?,?,?,?)", [
                (1, "A Casa das Marés", "L. Andrade", "Ficção", "Uma viagem às memórias de uma cidade costeira."),
                (2, "Python para Todos", "Ana Ribeiro", "Tecnologia", "Introdução prática à programação."),
            ])
            db.executemany("INSERT INTO edicoes VALUES (?,?,?,?,?)", [
                (1, 1, "Brochura", 2024, 5000), (2, 1, "Capa dura", 2025, 7500),
                (3, 2, "Brochura", 2024, 8000),
            ])
            db.executemany("INSERT INTO lojas VALUES (?,?,?,?,?,?,?,?,?)", [
                (1, "Unidade Centro", "Centro", "Rua das Flores, 10", "Seg–Sáb 9h–18h", "Pix, cartão (simulados)", "Retirada, acessibilidade", 1, "Clube do livro aos sábados"),
                (2, "Unidade Jardim", "Jardim", "Av. Verde, 22", "Seg–Sáb 10h–19h", "Pix, cartão (simulados)", "Retirada", 0, "Oficina de leitura mensal"),
            ])
            db.executemany("INSERT INTO estoques VALUES (?,?,?,?)", [
                (1, 1, 1, "Literatura"), (1, 2, 2, "Ficção"), (2, 1, 0, "Literatura"),
                (2, 2, 1, "Ficção"), (3, 1, 2, "Tecnologia"), (3, 2, 0, "Tecnologia"),
            ])
            db.execute("INSERT INTO avaliacoes VALUES (1,1,5,'Envolvente','Leitora demo')")
            db.execute("INSERT INTO promocoes VALUES (1,1,'Oferta de demonstração',1000,1)")

    def _cliente(self, db, cliente_id):
        cliente = db.execute("SELECT * FROM clientes WHERE id=?", (cliente_id,)).fetchone()
        if not cliente:
            raise RegraInvalida("Cliente inválido; cadastre-se primeiro.")
        return cliente

    def buscar_livros(self, titulo="", autor="", genero=""):
        with self.conexao() as db:
            livros = [registro(r) for r in db.execute("SELECT * FROM livros ORDER BY id")]
        return [b for b in livros if all(normalizar(termo) in normalizar(b[campo])
                for campo, termo in (("titulo", titulo), ("autor", autor), ("genero", genero)) if termo)]

    def detalhes_livro(self, livro_id):
        with self.conexao() as db:
            livro = registro(db.execute("SELECT * FROM livros WHERE id=?", (livro_id,)).fetchone())
            if not livro:
                raise RegraInvalida("Livro não encontrado.")
            livro["avaliacoes"] = [registro(r) for r in db.execute("SELECT * FROM avaliacoes WHERE livro_id=? ORDER BY id", (livro_id,))]
            livro["edicoes"] = []
            for row in db.execute("SELECT * FROM edicoes WHERE livro_id=? ORDER BY id", (livro_id,)).fetchall():
                ed = registro(row)
                ed["promocoes"] = [registro(r) for r in db.execute("SELECT * FROM promocoes WHERE edicao_id=? AND ativa=1", (ed["id"],))]
                ed["preco_final_centavos"] = max(0, ed["preco_centavos"] - sum(p["desconto_centavos"] for p in ed["promocoes"]))
                ed["estoques"] = [registro(r) for r in db.execute("SELECT e.*, l.nome AS loja_nome FROM estoques e JOIN lojas l ON l.id=e.loja_id WHERE e.edicao_id=? ORDER BY e.loja_id", (ed["id"],))]
                livro["edicoes"].append(ed)
            return livro

    def listar_lojas(self, bairro=""):
        with self.conexao() as db:
            return [registro(r) for r in db.execute("SELECT * FROM lojas ORDER BY id") if normalizar(bairro) in normalizar(r["bairro"])]

    def estoque(self, edicao_id, loja_id):
        with self.conexao() as db:
            item = registro(db.execute("SELECT * FROM estoques WHERE edicao_id=? AND loja_id=?", (edicao_id, loja_id)).fetchone())
            if not item:
                raise RegraInvalida("Edição ou loja inválida.")
            return item

    def _preco(self, db, edicao_id):
        row = db.execute("SELECT preco_centavos FROM edicoes WHERE id=?", (edicao_id,)).fetchone()
        if not row:
            raise RegraInvalida("Edição inválida.")
        desconto = db.execute("SELECT COALESCE(SUM(desconto_centavos),0) FROM promocoes WHERE edicao_id=? AND ativa=1", (edicao_id,)).fetchone()[0]
        return max(0, row[0] - desconto)

    def cadastrar(self, nome, email, bairro, interesses=""):
        nome, email, bairro = nome.strip(), email.strip().lower(), bairro.strip()
        if not nome or not bairro or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise RegraInvalida("Informe nome, email válido e bairro.")
        interesses = ",".join(p.strip() for p in interesses.split(",") if p.strip())
        with self.conexao() as db:
            try:
                cliente = db.execute("INSERT INTO clientes(nome,email,bairro,interesses) VALUES (?,?,?,?)", (nome, email, bairro, interesses)).lastrowid
            except sqlite3.IntegrityError as exc:
                raise RegraInvalida("Email já cadastrado.") from exc
            for p in db.execute("SELECT p.descricao, b.genero FROM promocoes p JOIN edicoes e ON e.id=p.edicao_id JOIN livros b ON b.id=e.livro_id WHERE p.ativa=1"):
                if normalizar(p["genero"]) in [normalizar(x) for x in interesses.split(",")]:
                    db.execute("INSERT INTO notificacoes(cliente_id,tipo,mensagem) VALUES (?,'promocao',?)", (cliente, p["descricao"]))
            return cliente

    def cliente_por_email(self, email):
        with self.conexao() as db:
            row = db.execute("SELECT * FROM clientes WHERE email=? COLLATE NOCASE", (email.strip(),)).fetchone()
            if not row:
                raise RegraInvalida("Email não cadastrado.")
            return registro(row)

    def cliente(self, cliente_id):
        with self.conexao() as db:
            return registro(self._cliente(db, cliente_id))

    def favorito(self, cliente_id, livro_id, adicionar=True):
        with self.conexao() as db:
            self._cliente(db, cliente_id)
            if not db.execute("SELECT 1 FROM livros WHERE id=?", (livro_id,)).fetchone():
                raise RegraInvalida("Livro inválido.")
            if adicionar:
                db.execute("INSERT OR IGNORE INTO favoritos VALUES (?,?)", (cliente_id, livro_id))
            else:
                db.execute("DELETE FROM favoritos WHERE cliente_id=? AND livro_id=?", (cliente_id, livro_id))

    def favoritos(self, cliente_id):
        with self.conexao() as db:
            self._cliente(db, cliente_id)
            return [registro(r) for r in db.execute("SELECT b.* FROM livros b JOIN favoritos f ON b.id=f.livro_id WHERE f.cliente_id=? ORDER BY b.id", (cliente_id,))]

    def recomendacoes(self, cliente_id):
        with self.conexao() as db:
            cliente = self._cliente(db, cliente_id)
            interesses = [normalizar(x.strip()) for x in cliente["interesses"].split(",") if x.strip()]
            return [registro(r) for r in db.execute("SELECT * FROM livros b WHERE NOT EXISTS (SELECT 1 FROM favoritos f WHERE f.livro_id=b.id AND f.cliente_id=?) ORDER BY id", (cliente_id,)) if normalizar(r["genero"]) in interesses]

    def notificacoes(self, cliente_id):
        with self.conexao() as db:
            self._cliente(db, cliente_id)
            return [registro(r) for r in db.execute("SELECT * FROM notificacoes WHERE cliente_id=? ORDER BY id DESC", (cliente_id,))]

    def _debitar(self, db, edicao_id, loja_id):
        cursor = db.execute("UPDATE estoques SET quantidade=quantidade-1 WHERE edicao_id=? AND loja_id=? AND quantidade>0", (edicao_id, loja_id))
        if cursor.rowcount != 1:
            raise RegraInvalida("Sem estoque nesta unidade/edição.")

    def reservar(self, cliente_id, edicao_id, loja_id):
        with self.conexao() as db:
            db.execute("BEGIN IMMEDIATE")
            self._cliente(db, cliente_id)
            preco = self._preco(db, edicao_id)
            self._debitar(db, edicao_id, loja_id)
            identificador = db.execute("INSERT INTO reservas(cliente_id,edicao_id,loja_id,estado,preco_centavos) VALUES (?,?,?,'confirmada',?)", (cliente_id, edicao_id, loja_id, preco)).lastrowid
            codigo = f"RES-{identificador:06d}"
            db.execute("UPDATE reservas SET codigo=? WHERE id=?", (codigo, identificador))
            return registro(db.execute("SELECT * FROM reservas WHERE id=?", (identificador,)).fetchone())

    def _reserva_confirmada(self, db, cliente_id, codigo):
        self._cliente(db, cliente_id)
        row = db.execute("SELECT * FROM reservas WHERE codigo=? AND cliente_id=? AND estado='confirmada'", (codigo, cliente_id)).fetchone()
        if not row:
            raise RegraInvalida("Reserva inexistente, de outro cliente ou já finalizada.")
        return row

    def cancelar(self, cliente_id, codigo):
        with self.conexao() as db:
            db.execute("BEGIN IMMEDIATE")
            reserva = self._reserva_confirmada(db, cliente_id, codigo)
            db.execute("UPDATE reservas SET estado='cancelada' WHERE id=?", (reserva["id"],))
            db.execute("UPDATE estoques SET quantidade=quantidade+1 WHERE edicao_id=? AND loja_id=?", (reserva["edicao_id"], reserva["loja_id"]))

    def retirar(self, cliente_id, codigo):
        with self.conexao() as db:
            db.execute("BEGIN IMMEDIATE")
            reserva = self._reserva_confirmada(db, cliente_id, codigo)
            db.execute("UPDATE reservas SET estado='retirada' WHERE id=?", (reserva["id"],))
            identificador = db.execute("INSERT INTO compras(cliente_id,edicao_id,loja_id,preco_centavos,reserva_id) VALUES (?,?,?,?,?)", (cliente_id, reserva["edicao_id"], reserva["loja_id"], reserva["preco_centavos"], reserva["id"])).lastrowid
            return registro(db.execute("SELECT * FROM compras WHERE id=?", (identificador,)).fetchone())

    def comprar(self, cliente_id, edicao_id, loja_id):
        with self.conexao() as db:
            db.execute("BEGIN IMMEDIATE")
            self._cliente(db, cliente_id)
            preco = self._preco(db, edicao_id)
            self._debitar(db, edicao_id, loja_id)
            identificador = db.execute("INSERT INTO compras(cliente_id,edicao_id,loja_id,preco_centavos) VALUES (?,?,?,?)", (cliente_id, edicao_id, loja_id, preco)).lastrowid
            return registro(db.execute("SELECT * FROM compras WHERE id=?", (identificador,)).fetchone())

    def historico(self, cliente_id):
        with self.conexao() as db:
            self._cliente(db, cliente_id)
            reservas = [registro(r) for r in db.execute("SELECT r.*, b.titulo, e.nome AS edicao, l.nome AS loja, s.secao FROM reservas r JOIN edicoes e ON e.id=r.edicao_id JOIN livros b ON b.id=e.livro_id JOIN lojas l ON l.id=r.loja_id JOIN estoques s ON s.edicao_id=r.edicao_id AND s.loja_id=r.loja_id WHERE r.cliente_id=? ORDER BY r.id DESC", (cliente_id,))]
            compras = [registro(r) for r in db.execute("SELECT c.*, b.titulo, e.nome AS edicao, l.nome AS loja FROM compras c JOIN edicoes e ON e.id=c.edicao_id JOIN livros b ON b.id=e.livro_id JOIN lojas l ON l.id=c.loja_id WHERE c.cliente_id=? ORDER BY c.id DESC", (cliente_id,))]
            return {"reservas": reservas, "compras": compras, "pontos": sum(c["preco_centavos"] // 100 for c in compras)}

    def alertar(self, cliente_id, edicao_id, loja_id):
        with self.conexao() as db:
            self._cliente(db, cliente_id)
            item = db.execute("SELECT quantidade FROM estoques WHERE edicao_id=? AND loja_id=?", (edicao_id, loja_id)).fetchone()
            if not item or item[0] != 0:
                raise RegraInvalida("Alerta permitido apenas para edição esgotada na unidade.")
            db.execute("INSERT OR IGNORE INTO alertas VALUES (?,?,?)", (cliente_id, edicao_id, loja_id))

    def repor(self, edicao_id, loja_id):
        with self.conexao() as db:
            db.execute("BEGIN IMMEDIATE")
            item = db.execute("SELECT b.titulo, l.nome FROM estoques s JOIN edicoes e ON e.id=s.edicao_id JOIN livros b ON b.id=e.livro_id JOIN lojas l ON l.id=s.loja_id WHERE s.edicao_id=? AND s.loja_id=?", (edicao_id, loja_id)).fetchone()
            if not item:
                raise RegraInvalida("Edição ou loja inválida.")
            db.execute("UPDATE estoques SET quantidade=quantidade+1 WHERE edicao_id=? AND loja_id=?", (edicao_id, loja_id))
            db.execute("INSERT INTO notificacoes(cliente_id,tipo,mensagem) SELECT cliente_id,'reposicao',? FROM alertas WHERE edicao_id=? AND loja_id=?", (f"Reposição simulada: {item[0]} em {item[1]}", edicao_id, loja_id))
            db.execute("DELETE FROM alertas WHERE edicao_id=? AND loja_id=?", (edicao_id, loja_id))
