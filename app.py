"""Interface HTTP local da livraria de demonstração."""
import os
from functools import wraps

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

from livraria import Livraria, RegraInvalida


def create_app(db_path=None):
    app = Flask(__name__)
    app.secret_key = os.environ.get("LIVRARIA_SECRET", "chave-local-apenas-demonstracao")
    loja = Livraria(db_path or os.environ.get("LIVRARIA_DB", "livraria.db"))
    loja.init_db()

    @app.template_filter("reais")
    def reais(centavos):
        return f"R$ {centavos / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @app.errorhandler(RegraInvalida)
    def erro(exc):
        flash(str(exc), "erro")
        return redirect(request.referrer or url_for("catalogo"))

    def logado(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("cliente_id"):
                flash("Cadastre-se ou entre para continuar.", "erro")
                return redirect(url_for("area"))
            return fn(*args, **kwargs)
        return wrapper

    @app.context_processor
    def contexto():
        return {"cliente_atual": loja.cliente(session["cliente_id"]) if session.get("cliente_id") else None}

    @app.get("/")
    def catalogo():
        return render_template("index.html", pagina="catalogo", livros=loja.buscar_livros(
            request.args.get("titulo", ""), request.args.get("autor", ""), request.args.get("genero", "")))

    @app.get("/livro/<int:livro_id>")
    def livro(livro_id):
        return render_template("index.html", pagina="livro", livro=loja.detalhes_livro(livro_id))

    @app.get("/lojas")
    def lojas():
        return render_template("index.html", pagina="lojas", lojas=loja.listar_lojas(request.args.get("bairro", "")))

    @app.get("/cliente")
    def area():
        if not session.get("cliente_id"):
            return render_template("index.html", pagina="entrada")
        cliente_id = session["cliente_id"]
        return render_template("index.html", pagina="cliente", historico=loja.historico(cliente_id),
                               favoritos=loja.favoritos(cliente_id), recomendacoes=loja.recomendacoes(cliente_id),
                               notificacoes=loja.notificacoes(cliente_id))

    @app.post("/cadastro")
    def cadastro():
        session["cliente_id"] = loja.cadastrar(request.form.get("nome", ""), request.form.get("email", ""),
                                              request.form.get("bairro", ""), request.form.get("interesses", ""))
        flash("Cadastro concluído. Esta é uma sessão local de demonstração.")
        return redirect(url_for("area"))

    @app.post("/entrar")
    def entrar():
        session["cliente_id"] = loja.cliente_por_email(request.form.get("email", ""))["id"]
        return redirect(url_for("area"))

    @app.post("/sair")
    def sair():
        session.clear()
        return redirect(url_for("catalogo"))

    @app.post("/favorito/<int:livro_id>/<acao>")
    @logado
    def favorito(livro_id, acao):
        if acao not in ("adicionar", "remover"):
            abort(404)
        loja.favorito(session["cliente_id"], livro_id, acao == "adicionar")
        return redirect(url_for("livro", livro_id=livro_id) if acao == "adicionar" else url_for("area"))

    @app.post("/reservar")
    @logado
    def reservar():
        reserva = loja.reservar(session["cliente_id"], int(request.form["edicao_id"]), int(request.form["loja_id"]))
        flash(f"Reserva confirmada: {reserva['codigo']}. Retire na unidade selecionada; pagamento simulado apenas na retirada.")
        return redirect(url_for("area"))

    @app.post("/comprar")
    @logado
    def comprar():
        compra = loja.comprar(session["cliente_id"], int(request.form["edicao_id"]), int(request.form["loja_id"]))
        flash(f"Compra presencial simulada registrada: #{compra['id']} (sem cobrança real).")
        return redirect(url_for("area"))

    @app.post("/reserva/<codigo>/<acao>")
    @logado
    def reserva_acao(codigo, acao):
        if acao == "retirar":
            loja.retirar(session["cliente_id"], codigo)
            flash(f"Retirada de {codigo} concluída; compra simulada registrada.")
        elif acao == "cancelar":
            loja.cancelar(session["cliente_id"], codigo)
            flash(f"Reserva {codigo} cancelada; estoque devolvido.")
        else:
            abort(404)
        return redirect(url_for("area"))

    @app.post("/alertar")
    @logado
    def alertar():
        loja.alertar(session["cliente_id"], int(request.form["edicao_id"]), int(request.form["loja_id"]))
        flash("Alerta local registrado; consulte sua área após simular reposição.")
        return redirect(request.referrer or url_for("catalogo"))

    @app.post("/repor")
    def repor():
        edicao_id, loja_id = int(request.form["edicao_id"]), int(request.form["loja_id"])
        loja.repor(edicao_id, loja_id)
        flash("Reposição simulada: uma unidade adicionada e notificações locais geradas.")
        return redirect(request.referrer or url_for("catalogo"))

    return app


if __name__ == "__main__":
    create_app().run(debug=False)
