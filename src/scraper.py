---

### 2. src/scraper.py

```python
"""
scraper.py
Consulta el buscador oficial de El Peruano (busquedas.elperuano.pe)
y extrae dispositivos de Normas Legales.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlencode

logger = logging.getLogger(__name__)

BASE_URL = "https://busquedas.elperuano.pe"
SEARCH_URL = f"{BASE_URL}/"


class ElPeruanoScraper:
    """Scraper para el Diario Oficial El Peruano."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (compatible; MinsaElPeruanoMonitor/1.0; "
                "+https://github.com/4-4-1941/Notificaciones-El-Peruano-Diario-)"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-PE,es;q=0.9",
        })

    def buscar_por_fecha(
        self,
        fecha: Optional[str] = None,
        palabras_clave: Optional[List[str]] = None,
        tipo_publicacion: str = "NL",
    ) -> List[Dict]:
        """
        Busca dispositivos publicados en una fecha específica.

        Args:
            fecha: Fecha en formato YYYY-MM-DD. Si es None, usa el día actual.
            palabras_clave: Lista de palabras para filtrar (ej: ["MINSA", "NTS"]).
            tipo_publicacion: "NL" = Normas Legales (por defecto).

        Returns:
            Lista de diccionarios con la información de cada dispositivo.
        """
        if fecha is None:
            fecha = datetime.now().strftime("%Y-%m-%d")

        logger.info(f"Buscando dispositivos del {fecha} (tipo: {tipo_publicacion})")

        params = {
            "fechaIni": fecha.replace("-", ""),
            "fechaFin": fecha.replace("-", ""),
            "tipoPublicacion": tipo_publicacion,
            "ci": "ONLY",
            "start": 0,
        }

        try:
            response = self.session.get(
                SEARCH_URL,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Error al consultar El Peruano: {e}")
            return []

        dispositivos = self._parsear_resultados(response.text, palabras_clave)
        logger.info(f"Se encontraron {len(dispositivos)} dispositivos relevantes")
        return dispositivos

    def buscar_rango(
        self,
        fecha_inicio: str,
        fecha_fin: str,
        palabras_clave: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Busca dispositivos en un rango de fechas."""
        resultados = []
        inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        fin = datetime.strptime(fecha_fin, "%Y-%m-%d")

        current = inicio
        while current <= fin:
            fecha_str = current.strftime("%Y-%m-%d")
            dispositivos = self.buscar_por_fecha(fecha_str, palabras_clave)
            resultados.extend(dispositivos)
            current += timedelta(days=1)

        return resultados

    def _parsear_resultados(
        self,
        html: str,
        palabras_clave: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Extrae la información de los dispositivos desde el HTML."""
        soup = BeautifulSoup(html, "html.parser")
        dispositivos = []

        # Nota: la estructura exacta de El Peruano puede cambiar.
        # Este parser es una base funcional que se ajustará según el HTML real.
        items = soup.select(".dispositivo, .resultado-item, article, .card")

        if not items:
            # Fallback: buscar enlaces a dispositivos
            items = soup.select('a[href*="/dispositivo/"]')

        for item in items:
            try:
                data = self._extraer_dispositivo(item)
                if data and self._es_relevante(data, palabras_clave):
                    dispositivos.append(data)
            except Exception as e:
                logger.warning(f"Error al parsear un ítem: {e}")
                continue

        return dispositivos

    def _extraer_dispositivo(self, element) -> Optional[Dict]:
        """Extrae los campos de un dispositivo individual."""
        # Intentar obtener el enlace
        link_tag = element if element.name == "a" else element.find("a", href=True)
        if not link_tag:
            return None

        href = link_tag.get("href", "")
        if "/dispositivo/" not in href:
            return None

        url = urljoin(BASE_URL, href)

        # Extraer número de orden (ej: 2562494-1)
        op = href.rstrip("/").split("/")[-1]

        # Título / sumilla
        titulo = link_tag.get_text(strip=True)
        if not titulo:
            titulo_tag = element.find(["h2", "h3", "h4", "strong", "p"])
            titulo = titulo_tag.get_text(strip=True) if titulo_tag else "Sin título"

        return {
            "op": op,
            "titulo": titulo,
            "url": url,
            "fecha_extraccion": datetime.now().isoformat(),
            "fuente": "elperuano",
        }

    def _es_relevante(
        self,
        dispositivo: Dict,
        palabras_clave: Optional[List[str]],
    ) -> bool:
        """Verifica si el dispositivo contiene alguna palabra clave."""
        if not palabras_clave:
            return True

        texto = (dispositivo.get("titulo") or "").upper()
        return any(palabra.upper() in texto for palabra in palabras_clave)

    def obtener_detalle(self, op: str) -> Optional[Dict]:
        """
        Obtiene el detalle de un dispositivo por su número de orden.
        Ejemplo: op = "2562494-1"
        """
        url = f"{BASE_URL}/dispositivo/NL/{op}"
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Extraer texto principal
            contenido = soup.select_one(".contenido, .texto, #visor, article")
            texto = contenido.get_text(separator="\n", strip=True) if contenido else ""

            return {
                "op": op,
                "url": url,
                "texto": texto[:5000],  # Limitar tamaño
                "fecha_extraccion": datetime.now().isoformat(),
            }
        except requests.RequestException as e:
            logger.error(f"Error al obtener detalle de {op}: {e}")
            return None


if __name__ == "__main__":
    # Prueba rápida
    logging.basicConfig(level=logging.INFO)
    scraper = ElPeruanoScraper()
    resultados = scraper.buscar_por_fecha(
        palabras_clave=["MINSA", "NTS", "Resolución Ministerial"]
    )
    for r in resultados:
        print(f"- {r['op']}: {r['titulo'][:80]}...")
