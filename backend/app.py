import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from .ai_engine import SemanticSearchEngine
from .compression import CompressionEngine
from .data_collection import (
    entries_from_historical_rows,
    fetch_dbpedia_summary,
    fetch_wikipedia_summary,
    simulate_seshat_rows,
)
from .database import LedgerDatabase
from .scoring import compute_weighted_score, learn_weights_from_examples


def create_app():
    load_dotenv()
    root = Path(__file__).resolve().parents[1]
    app = Flask(
        __name__,
        template_folder=str(root / "frontend" / "templates"),
        static_folder=str(root / "frontend" / "static"),
    )
    CORS(app)
    app.config["FLASK_HOST"] = os.getenv("FLASK_HOST", "127.0.0.1")
    app.config["FLASK_PORT"] = os.getenv("FLASK_PORT", "5000")

    db = LedgerDatabase(os.getenv("DATABASE_URL"), root / "data" / "ledger.sqlite3")
    db.initialize()
    semantic = SemanticSearchEngine()
    compression = CompressionEngine()

    def rebuild_engines():
        entries = db.list_ledger_entries()
        semantic.rebuild(entries)
        compression.rebuild(entries)

    rebuild_engines()

    @app.get("/")
    def dashboard():
        return render_template("dashboard.html")

    @app.get("/civilizations")
    def civilizations_page():
        return render_template("civilizations.html")

    @app.get("/ledger")
    def ledger_page():
        return render_template("ledger.html")

    @app.get("/search")
    def search_page():
        return render_template("search.html")

    @app.get("/compression")
    def compression_page():
        return render_template("compression.html")

    @app.get("/data")
    def data_page():
        return render_template("data.html")

    @app.post("/api/civilizations")
    def register_civilization():
        payload = request.get_json(force=True)
        civ_id = db.register_civilization(
            payload["name"],
            payload.get("region", ""),
            payload.get("start_year"),
            payload.get("end_year"),
            payload.get("notes", ""),
        )
        return jsonify({"id": civ_id, "status": "created"}), 201

    @app.get("/api/civilizations")
    def list_civilizations():
        return jsonify(db.list_civilizations())

    @app.post("/api/ledger")
    def add_ledger_entry():
        payload = request.get_json(force=True)
        entry_id = db.add_ledger_entry(
            payload["civilization_id"],
            payload["year"],
            payload["entry_type"],
            payload["domain"],
            float(payload["value"]),
            payload["description"],
            payload.get("source", "manual"),
        )
        rebuild_engines()
        return jsonify({"id": entry_id, "status": "created"}), 201

    @app.get("/api/ledger")
    def list_ledger():
        civ_id = request.args.get("civilization_id", type=int)
        return jsonify(db.list_ledger_entries(civ_id))

    @app.post("/api/import")
    def import_file():
        uploaded = request.files.get("file")
        if not uploaded:
            return jsonify({"error": "Upload a CSV or JSON file under the field named file."}), 400
        count = db.import_csv_or_json(uploaded.filename, uploaded.stream)
        rebuild_engines()
        return jsonify({"imported_entries": count})

    @app.post("/api/data/simulate-seshat")
    def simulate_seshat():
        civ_id = request.get_json(force=True).get("civilization_id")
        rows = simulate_seshat_rows()
        entries = entries_from_historical_rows(civ_id, rows, source="simulated_seshat")
        for entry in entries:
            db.add_ledger_entry(**entry)
        rebuild_engines()
        return jsonify({"imported_entries": len(entries)})

    @app.post("/api/data/wikipedia")
    def wikipedia_import():
        payload = request.get_json(force=True)
        summary = fetch_wikipedia_summary(payload["title"])
        civ_id = payload["civilization_id"]
        entry_id = db.add_ledger_entry(
            civ_id,
            payload.get("year", 0),
            payload.get("entry_type", "Asset"),
            payload.get("domain", "Scientific"),
            float(payload.get("value", 50)),
            summary,
            "wikipedia",
        )
        rebuild_engines()
        return jsonify({"id": entry_id, "summary": summary[:500]})

    @app.post("/api/data/dbpedia")
    def dbpedia_import():
        payload = request.get_json(force=True)
        summary = fetch_dbpedia_summary(payload["resource"])
        entry_id = db.add_ledger_entry(
            payload["civilization_id"],
            payload.get("year", 0),
            payload.get("entry_type", "Asset"),
            payload.get("domain", "Governance"),
            float(payload.get("value", 50)),
            summary,
            "dbpedia",
        )
        rebuild_engines()
        return jsonify({"id": entry_id, "summary": summary[:500]})

    @app.get("/api/search")
    def search():
        query = request.args.get("q", "")
        mode = request.args.get("mode", "semantic")
        civ_id = request.args.get("civilization_id", type=int)
        if mode == "exact":
            results = compression.search_pattern(query, civilization_id=civ_id)
        else:
            results = semantic.search(query, civilization_id=civ_id, limit=10)
        return jsonify(results)

    @app.get("/api/score/<int:civilization_id>")
    def compute_score(civilization_id):
        entries = db.list_ledger_entries(civilization_id)
        score = compute_weighted_score(entries)
        return jsonify(score)

    @app.post("/api/score/learn-weights")
    def learn_weights():
        payload = request.get_json(force=True)
        return jsonify(learn_weights_from_examples(payload.get("examples", [])))

    @app.get("/api/compression/stats")
    def compression_stats():
        return jsonify(compression.stats())

    @app.get("/api/compression/range")
    def compression_range_query():
        low = request.args.get("low", type=int, default=0)
        high = request.args.get("high", type=int, default=100)
        return jsonify(compression.value_range_query(low, high))

    return app
