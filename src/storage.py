"""
storage.py
Almacenamiento de normas detectadas.
Soporta JSON y SQLite para evitar duplicados y guardar historial.
"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
JSON_FILE = DATA_DIR / "normas_minsa.json"
DB_FILE = DATA_DIR / "historial.db"


class Storage:
    """Gestiona el almacenamiento de normas del MINSA."""

    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Crea la tabla de historial si no existe."""
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS normas (
                    op TEXT PRIMARY KEY,
                    titulo TEXT,
                    url TEXT,
                    numero_rm TEXT,
                    numero_nts TEXT,
                    ministerio TEXT,
                    fecha_deteccion TEXT,
                    notificado INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def ya_existe(self, op: str) -> bool:
        """Verifica si una norma ya fue registrada (por su número de orden)."""
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM normas WHERE op = ?", (op,)
            )
            return cursor.fetchone() is not None

    def guardar(self, dispositivos: List[Dict]) -> List[Dict]:
        """
        Guarda solo las normas nuevas.
        Devuelve la lista de normas que realmente se insertaron (nuevas).
        """
        nuevas = []

        with sqlite3.connect(DB_FILE) as conn:
            for d in dispositivos:
                op = d.get("op")
                if not op or self.ya_existe(op):
                    continue

                conn.execute(
                    """
                    INSERT INTO normas 
                    (op, titulo, url, numero_rm, numero_nts, ministerio, fecha_deteccion)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        op,
                        d.get("titulo"),
                        d.get("url"),
                        d.get("numero_rm"),
                        d.get("numero_nts"),
                        d.get("ministerio", "MINSA"),
                        datetime.now().isoformat(),
                    ),
                )
                nuevas.append(d)

            conn.commit()

        if nuevas:
            self._actualizar_json(nuevas)
            logger.info(f"Se guardaron {len(nuevas)} normas nuevas")
        else:
            logger.info("No hay normas nuevas para guardar")

        return nuevas

    def _actualizar_json(self, nuevas: List[Dict]):
        """Agrega las normas nuevas al archivo JSON de respaldo."""
        historial = []
        if JSON_FILE.exists():
            try:
                with open(JSON_FILE, "r", encoding="utf-8") as f:
                    historial = json.load(f)
            except (json.JSONDecodeError, IOError):
                historial = []

        historial.extend(nuevas)

        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(historial, f, ensure_ascii=False, indent=2)

    def marcar_notificado(self, op: str):
        """Marca una norma como ya notificada."""
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute(
                "UPDATE normas SET notificado = 1 WHERE op = ?", (op,)
            )
            conn.commit()

    def obtener_pendientes_notificacion(self) -> List[Dict]:
        """Devuelve las normas que aún no han sido notificadas."""
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM normas WHERE notificado = 0 ORDER BY fecha_deteccion DESC"
            )
            return [dict(row) for row in cursor.fetchall()]

    def obtener_ultimas(self, limite: int = 20) -> List[Dict]:
        """Devuelve las últimas normas registradas."""
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM normas ORDER BY fecha_deteccion DESC LIMIT ?",
                (limite,),
            )
            return [dict(row) for row in cursor.fetchall()]
