"""
filter_minsa.py
Filtros específicos para detectar normas del MINSA
(Resoluciones Ministeriales y Normas Técnicas de Salud).
"""

from typing import List, Dict
import re
import logging

logger = logging.getLogger(__name__)

# Palabras clave principales para MINSA
KEYWORDS_MINSA = [
    "MINSA",
    "MINISTERIO DE SALUD",
    "NTS",
    "NORMA TÉCNICA DE SALUD",
    "NORMA TECNICA DE SALUD",
    "RESOLUCIÓN MINISTERIAL",
    "RESOLUCION MINISTERIAL",
    "RM N",
    "R.M.",
]

# Patrones para extraer números de norma
PATRON_RM = re.compile(
    r"(?:RM|R\.M\.|RESOLUCI[ÓO]N MINISTERIAL)\s*(?:N[°º.]?\s*)?(\d{1,4}[-/]\d{4})",
    re.IGNORECASE,
)

PATRON_NTS = re.compile(
    r"(?:NTS|NORMA T[ÉE]CNICA DE SALUD)\s*(?:N[°º.]?\s*)?(\d{1,3}[-/]?[A-Z0-9\-/]*)",
    re.IGNORECASE,
)


def es_norma_minsa(dispositivo: Dict) -> bool:
    """
    Determina si un dispositivo pertenece al MINSA.
    
    Args:
        dispositivo: Diccionario con al menos la clave 'titulo'.
        
    Returns:
        True si es una norma del MINSA, False en caso contrario.
    """
    titulo = (dispositivo.get("titulo") or "").upper()
    
    for keyword in KEYWORDS_MINSA:
        if keyword.upper() in titulo:
            return True
            
    return False


def filtrar_minsa(dispositivos: List[Dict]) -> List[Dict]:
    """
    Filtra una lista de dispositivos y devuelve solo los del MINSA.
    
    Args:
        dispositivos: Lista de dispositivos extraídos por el scraper.
        
    Returns:
        Lista filtrada solo con normas del MINSA.
    """
    filtrados = []
    
    for disp in dispositivos:
        if es_norma_minsa(disp):
            # Enriquecer con número de RM o NTS si se puede extraer
            disp = enriquecer_norma(disp)
            filtrados.append(disp)
            
    logger.info(f"Filtro MINSA: {len(filtrados)} de {len(dispositivos)} dispositivos")
    return filtrados


def enriquecer_norma(dispositivo: Dict) -> Dict:
    """
    Intenta extraer el número de RM y/o NTS del título
    y los agrega como campos adicionales.
    """
    titulo = dispositivo.get("titulo") or ""
    
    # Buscar número de Resolución Ministerial
    match_rm = PATRON_RM.search(titulo)
    if match_rm:
        dispositivo["numero_rm"] = match_rm.group(1)
    
    # Buscar número de NTS
    match_nts = PATRON_NTS.search(titulo)
    if match_nts:
        dispositivo["numero_nts"] = match_nts.group(1)
    
    # Marcar origen
    dispositivo["ministerio"] = "MINSA"
    
    return dispositivo


def filtrar_por_tipo(dispositivos: List[Dict], tipo: str = "todos") -> List[Dict]:
    """
    Filtra por tipo de norma.
    
    Args:
        dispositivos: Lista ya filtrada de MINSA.
        tipo: "rm", "nts" o "todos".
    """
    if tipo == "todos":
        return dispositivos
        
    resultado = []
    for d in dispositivos:
        if tipo == "rm" and d.get("numero_rm"):
            resultado.append(d)
        elif tipo == "nts" and d.get("numero_nts"):
            resultado.append(d)
            
    return resultado
