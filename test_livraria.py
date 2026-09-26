"""Critérios C01–C07 de docs/specs/livraria.md; escritos antes do domínio."""
import tempfile
import unittest
from pathlib import Path

from livraria import Livraria, RegraInvalida


class LivrariaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / "teste.db")
        self.loja = Livraria(self.db)
        self.loja.init_db()

    def cliente(self, email="ana@example.com"):
        return self.loja.cadastrar("Ana", email, "Centro", "Ficção")

    def test_c01_busca_por_campos_combinados_e_sem_resultados(self):
        self.assertEqual(len(self.loja.buscar_livros()), 2)
        self.assertEqual([b["id"] for b in self.loja.buscar_livros(titulo="mares", autor="ANDRADE", genero="ficcao")], [1])
        self.assertEqual(self.loja.buscar_livros(titulo="inexistente"), [])

    def test_c02_detalhes_edicoes_avaliacoes_e_preco_promocional(self):
        livro = self.loja.detalhes_livro(1)
        self.assertTrue(livro["sinopse"])
        self.assertEqual(len(livro["edicoes"]), 2)
        self.assertTrue(livro["avaliacoes"])
        self.assertEqual(livro["edicoes"][0]["preco_centavos"], 5000)
        self.assertEqual(livro["edicoes"][0]["preco_final_centavos"], 4000)
        self.assertEqual({s["loja_id"]: s["quantidade"] for s in livro["edicoes"][0]["estoques"]}, {1: 1, 2: 2})
        with self.assertRaises(RegraInvalida):
            self.loja.detalhes_livro(999)

    def test_c03_lojas_bairro_dados_e_secao(self):
        lojas = self.loja.listar_lojas("CENTRO")
        self.assertEqual(len(lojas), 1)
        for campo in ("endereco", "horario", "pagamentos", "servicos", "cafe", "eventos"):
            self.assertIn(campo, lojas[0])
        self.assertEqual(self.loja.estoque(1, 1)["secao"], "Literatura")
        self.assertEqual(self.loja.estoque(1, 2)["quantidade"], 2)

    def test_c04_cadastro_favoritos_recomendacoes_e_invalidos(self):
        for nome, email, bairro in (("", "ok@example.com", "Centro"), ("Ana", "ruim", "Centro"), ("Ana", "ok@example.com", "")):
            with self.assertRaises(RegraInvalida):
                self.loja.cadastrar(nome, email, bairro, "Ficção")
        cliente = self.cliente()
        with self.assertRaises(RegraInvalida):
            self.cliente("ANA@example.com")
        self.assertEqual([b["id"] for b in self.loja.recomendacoes(cliente)], [1])
        self.loja.favorito(cliente, 1, True)
        self.loja.favorito(cliente, 1, True)
        self.assertEqual(len(self.loja.favoritos(cliente)), 1)
        self.assertEqual(self.loja.recomendacoes(cliente), [])
        self.loja.favorito(cliente, 1, False)
        self.assertEqual(self.loja.favoritos(cliente), [])
        self.assertTrue(any(n["tipo"] == "promocao" for n in self.loja.notificacoes(cliente)))

    def test_c05_reserva_ultimo_exemplar_sem_estoque_e_cancelamento(self):
        cliente = self.cliente()
        reserva = self.loja.reservar(cliente, 1, 1)
        self.assertEqual(reserva["codigo"], "RES-000001")
        self.assertEqual(reserva["estado"], "confirmada")
        self.assertEqual(reserva["preco_centavos"], 4000)
        self.assertEqual(self.loja.estoque(1, 1)["quantidade"], 0)
        self.assertEqual(self.loja.estoque(1, 2)["quantidade"], 2)
        with self.assertRaises(RegraInvalida):
            self.loja.reservar(cliente, 1, 1)
        self.assertEqual(len(self.loja.historico(cliente)["reservas"]), 1)
        self.loja.cancelar(cliente, reserva["codigo"])
        self.assertEqual(self.loja.estoque(1, 1)["quantidade"], 1)
        with self.assertRaises(RegraInvalida):
            self.loja.cancelar(cliente, reserva["codigo"])

    def test_c06_retirada_compra_direta_pontos_e_transicoes_invalidas(self):
        cliente = self.cliente()
        outro = self.cliente("bia@example.com")
        reserva = self.loja.reservar(cliente, 1, 1)
        with self.assertRaises(RegraInvalida):
            self.loja.retirar(outro, reserva["codigo"])
        self.loja.retirar(cliente, reserva["codigo"])
        with self.assertRaises(RegraInvalida):
            self.loja.retirar(cliente, reserva["codigo"])
        with self.assertRaises(RegraInvalida):
            self.loja.cancelar(cliente, reserva["codigo"])
        self.assertEqual(self.loja.estoque(1, 1)["quantidade"], 0)
        compra = self.loja.comprar(cliente, 1, 2)
        self.assertEqual(compra["preco_centavos"], 4000)
        self.assertEqual(self.loja.estoque(1, 2)["quantidade"], 1)
        self.assertEqual(self.loja.historico(cliente)["pontos"], 80)
        with self.assertRaises(RegraInvalida):
            self.loja.comprar(cliente, 2, 1)
        self.assertEqual(len(self.loja.historico(cliente)["compras"]), 2)

    def test_c07_alerta_reposicao_local_e_persistencia(self):
        cliente = self.cliente()
        self.loja.alertar(cliente, 2, 1)
        self.loja.alertar(cliente, 2, 1)
        self.loja.repor(2, 1)
        self.assertEqual(self.loja.estoque(2, 1)["quantidade"], 1)
        self.assertEqual(sum(n["tipo"] == "reposicao" for n in self.loja.notificacoes(cliente)), 1)
        self.assertEqual(Livraria(self.db).estoque(2, 1)["quantidade"], 1)

    def test_c03_inicializacao_repetida_preserva_dados(self):
        cliente = self.cliente()
        self.loja.reservar(cliente, 1, 1)
        self.loja.init_db()
        self.assertEqual(self.loja.estoque(1, 1)["quantidade"], 0)
        self.assertEqual(len(self.loja.buscar_livros()), 2)
        self.assertEqual(len(self.loja.historico(cliente)["reservas"]), 1)


if __name__ == "__main__":
    unittest.main()
