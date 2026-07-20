"""
bracket_service.py
==================
Simula el bracket personal de un apostador para el Mundial 2026.

1. Calcula standings por grupo segun las apuestas del usuario.
2. Selecciona los 8 mejores terceros de los 12 grupos (criterio FIFA 2026).
3. Arma el bracket de Ronda de 32 usando la tabla de 495 combinaciones FIFA.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Tabla de 495 combinaciones FIFA 2026 — Anexo C del reglamento
# Key: frozenset de 8 letras de grupos que clasifican como terceros
# Value: (vs_1A, vs_1B, vs_1D, vs_1E, vs_1G, vs_1I, vs_1K, vs_1L)
# → corresponde a matches 79, 85, 81, 74, 82, 77, 87, 80 respectivamente
TERCEROS_COMBINACIONES: dict[frozenset, tuple] = {
    frozenset('EFGHIJKL'): ('E', 'J', 'I', 'F', 'H', 'G', 'L', 'K'),
    frozenset('DFGHIJKL'): ('H', 'G', 'I', 'D', 'J', 'F', 'L', 'K'),
    frozenset('DEGHIJKL'): ('E', 'J', 'I', 'D', 'H', 'G', 'L', 'K'),
    frozenset('DEFHIJKL'): ('E', 'J', 'I', 'D', 'H', 'F', 'L', 'K'),
    frozenset('DEFGIJKL'): ('E', 'G', 'I', 'D', 'J', 'F', 'L', 'K'),
    frozenset('DEFGHJKL'): ('E', 'G', 'J', 'D', 'H', 'F', 'L', 'K'),
    frozenset('DEFGHIKL'): ('E', 'G', 'I', 'D', 'H', 'F', 'L', 'K'),
    frozenset('DEFGHIJL'): ('E', 'G', 'J', 'D', 'H', 'F', 'L', 'I'),
    frozenset('DEFGHIJK'): ('E', 'G', 'J', 'D', 'H', 'F', 'I', 'K'),
    frozenset('CFGHIJKL'): ('H', 'G', 'I', 'C', 'J', 'F', 'L', 'K'),
    frozenset('CEGHIJKL'): ('E', 'J', 'I', 'C', 'H', 'G', 'L', 'K'),
    frozenset('CEFHIJKL'): ('E', 'J', 'I', 'C', 'H', 'F', 'L', 'K'),
    frozenset('CEFGIJKL'): ('E', 'G', 'I', 'C', 'J', 'F', 'L', 'K'),
    frozenset('CEFGHJKL'): ('E', 'G', 'J', 'C', 'H', 'F', 'L', 'K'),
    frozenset('CEFGHIKL'): ('E', 'G', 'I', 'C', 'H', 'F', 'L', 'K'),
    frozenset('CEFGHIJL'): ('E', 'G', 'J', 'C', 'H', 'F', 'L', 'I'),
    frozenset('CEFGHIJK'): ('E', 'G', 'J', 'C', 'H', 'F', 'I', 'K'),
    frozenset('CDGHIJKL'): ('H', 'G', 'I', 'C', 'J', 'D', 'L', 'K'),
    frozenset('CDFHIJKL'): ('C', 'J', 'I', 'D', 'H', 'F', 'L', 'K'),
    frozenset('CDFGIJKL'): ('C', 'G', 'I', 'D', 'J', 'F', 'L', 'K'),
    frozenset('CDFGHJKL'): ('C', 'G', 'J', 'D', 'H', 'F', 'L', 'K'),
    frozenset('CDFGHIKL'): ('C', 'G', 'I', 'D', 'H', 'F', 'L', 'K'),
    frozenset('CDFGHIJL'): ('C', 'G', 'J', 'D', 'H', 'F', 'L', 'I'),
    frozenset('CDFGHIJK'): ('C', 'G', 'J', 'D', 'H', 'F', 'I', 'K'),
    frozenset('CDEHIJKL'): ('E', 'J', 'I', 'C', 'H', 'D', 'L', 'K'),
    frozenset('CDEGIJKL'): ('E', 'G', 'I', 'C', 'J', 'D', 'L', 'K'),
    frozenset('CDEGHJKL'): ('E', 'G', 'J', 'C', 'H', 'D', 'L', 'K'),
    frozenset('CDEGHIKL'): ('E', 'G', 'I', 'C', 'H', 'D', 'L', 'K'),
    frozenset('CDEGHIJL'): ('E', 'G', 'J', 'C', 'H', 'D', 'L', 'I'),
    frozenset('CDEGHIJK'): ('E', 'G', 'J', 'C', 'H', 'D', 'I', 'K'),
    frozenset('CDEFIJKL'): ('C', 'J', 'E', 'D', 'I', 'F', 'L', 'K'),
    frozenset('CDEFHJKL'): ('C', 'J', 'E', 'D', 'H', 'F', 'L', 'K'),
    frozenset('CDEFHIKL'): ('C', 'E', 'I', 'D', 'H', 'F', 'L', 'K'),
    frozenset('CDEFHIJL'): ('C', 'J', 'E', 'D', 'H', 'F', 'L', 'I'),
    frozenset('CDEFHIJK'): ('C', 'J', 'E', 'D', 'H', 'F', 'I', 'K'),
    frozenset('CDEFGJKL'): ('C', 'G', 'E', 'D', 'J', 'F', 'L', 'K'),
    frozenset('CDEFGIKL'): ('C', 'G', 'E', 'D', 'I', 'F', 'L', 'K'),
    frozenset('CDEFGIJL'): ('C', 'G', 'E', 'D', 'J', 'F', 'L', 'I'),
    frozenset('CDEFGIJK'): ('C', 'G', 'E', 'D', 'J', 'F', 'I', 'K'),
    frozenset('CDEFGHKL'): ('C', 'G', 'E', 'D', 'H', 'F', 'L', 'K'),
    frozenset('CDEFGHJL'): ('C', 'G', 'J', 'D', 'H', 'F', 'L', 'E'),
    frozenset('CDEFGHJK'): ('C', 'G', 'J', 'D', 'H', 'F', 'E', 'K'),
    frozenset('CDEFGHIL'): ('C', 'G', 'E', 'D', 'H', 'F', 'L', 'I'),
    frozenset('CDEFGHIK'): ('C', 'G', 'E', 'D', 'H', 'F', 'I', 'K'),
    frozenset('CDEFGHIJ'): ('C', 'G', 'J', 'D', 'H', 'F', 'E', 'I'),
    frozenset('BFGHIJKL'): ('H', 'J', 'B', 'F', 'I', 'G', 'L', 'K'),
    frozenset('BEGHIJKL'): ('E', 'J', 'I', 'B', 'H', 'G', 'L', 'K'),
    frozenset('BEFHIJKL'): ('E', 'J', 'B', 'F', 'I', 'H', 'L', 'K'),
    frozenset('BEFGIJKL'): ('E', 'J', 'B', 'F', 'I', 'G', 'L', 'K'),
    frozenset('BEFGHJKL'): ('E', 'J', 'B', 'F', 'H', 'G', 'L', 'K'),
    frozenset('BEFGHIKL'): ('E', 'G', 'B', 'F', 'I', 'H', 'L', 'K'),
    frozenset('BEFGHIJL'): ('E', 'J', 'B', 'F', 'H', 'G', 'L', 'I'),
    frozenset('BEFGHIJK'): ('E', 'J', 'B', 'F', 'H', 'G', 'I', 'K'),
    frozenset('BDGHIJKL'): ('H', 'J', 'B', 'D', 'I', 'G', 'L', 'K'),
    frozenset('BDFHIJKL'): ('H', 'J', 'B', 'D', 'I', 'F', 'L', 'K'),
    frozenset('BDFGIJKL'): ('I', 'G', 'B', 'D', 'J', 'F', 'L', 'K'),
    frozenset('BDFGHJKL'): ('H', 'G', 'B', 'D', 'J', 'F', 'L', 'K'),
    frozenset('BDFGHIKL'): ('H', 'G', 'B', 'D', 'I', 'F', 'L', 'K'),
    frozenset('BDFGHIJL'): ('H', 'G', 'B', 'D', 'J', 'F', 'L', 'I'),
    frozenset('BDFGHIJK'): ('H', 'G', 'B', 'D', 'J', 'F', 'I', 'K'),
    frozenset('BDEHIJKL'): ('E', 'J', 'B', 'D', 'I', 'H', 'L', 'K'),
    frozenset('BDEGIJKL'): ('E', 'J', 'B', 'D', 'I', 'G', 'L', 'K'),
    frozenset('BDEGHJKL'): ('E', 'J', 'B', 'D', 'H', 'G', 'L', 'K'),
    frozenset('BDEGHIKL'): ('E', 'G', 'B', 'D', 'I', 'H', 'L', 'K'),
    frozenset('BDEGHIJL'): ('E', 'J', 'B', 'D', 'H', 'G', 'L', 'I'),
    frozenset('BDEGHIJK'): ('E', 'J', 'B', 'D', 'H', 'G', 'I', 'K'),
    frozenset('BDEFIJKL'): ('E', 'J', 'B', 'D', 'I', 'F', 'L', 'K'),
    frozenset('BDEFHJKL'): ('E', 'J', 'B', 'D', 'H', 'F', 'L', 'K'),
    frozenset('BDEFHIKL'): ('E', 'I', 'B', 'D', 'H', 'F', 'L', 'K'),
    frozenset('BDEFHIJL'): ('E', 'J', 'B', 'D', 'H', 'F', 'L', 'I'),
    frozenset('BDEFHIJK'): ('E', 'J', 'B', 'D', 'H', 'F', 'I', 'K'),
    frozenset('BDEFGJKL'): ('E', 'G', 'B', 'D', 'J', 'F', 'L', 'K'),
    frozenset('BDEFGIKL'): ('E', 'G', 'B', 'D', 'I', 'F', 'L', 'K'),
    frozenset('BDEFGIJL'): ('E', 'G', 'B', 'D', 'J', 'F', 'L', 'I'),
    frozenset('BDEFGIJK'): ('E', 'G', 'B', 'D', 'J', 'F', 'I', 'K'),
    frozenset('BDEFGHKL'): ('E', 'G', 'B', 'D', 'H', 'F', 'L', 'K'),
    frozenset('BDEFGHJL'): ('H', 'G', 'B', 'D', 'J', 'F', 'L', 'E'),
    frozenset('BDEFGHJK'): ('H', 'G', 'B', 'D', 'J', 'F', 'E', 'K'),
    frozenset('BDEFGHIL'): ('E', 'G', 'B', 'D', 'H', 'F', 'L', 'I'),
    frozenset('BDEFGHIK'): ('E', 'G', 'B', 'D', 'H', 'F', 'I', 'K'),
    frozenset('BDEFGHIJ'): ('H', 'G', 'B', 'D', 'J', 'F', 'E', 'I'),
    frozenset('BCGHIJKL'): ('H', 'J', 'B', 'C', 'I', 'G', 'L', 'K'),
    frozenset('BCFHIJKL'): ('H', 'J', 'B', 'C', 'I', 'F', 'L', 'K'),
    frozenset('BCFGIJKL'): ('I', 'G', 'B', 'C', 'J', 'F', 'L', 'K'),
    frozenset('BCFGHJKL'): ('H', 'G', 'B', 'C', 'J', 'F', 'L', 'K'),
    frozenset('BCFGHIKL'): ('H', 'G', 'B', 'C', 'I', 'F', 'L', 'K'),
    frozenset('BCFGHIJL'): ('H', 'G', 'B', 'C', 'J', 'F', 'L', 'I'),
    frozenset('BCFGHIJK'): ('H', 'G', 'B', 'C', 'J', 'F', 'I', 'K'),
    frozenset('BCEHIJKL'): ('E', 'J', 'B', 'C', 'I', 'H', 'L', 'K'),
    frozenset('BCEGIJKL'): ('E', 'J', 'B', 'C', 'I', 'G', 'L', 'K'),
    frozenset('BCEGHJKL'): ('E', 'J', 'B', 'C', 'H', 'G', 'L', 'K'),
    frozenset('BCEGHIKL'): ('E', 'G', 'B', 'C', 'I', 'H', 'L', 'K'),
    frozenset('BCEGHIJL'): ('E', 'J', 'B', 'C', 'H', 'G', 'L', 'I'),
    frozenset('BCEGHIJK'): ('E', 'J', 'B', 'C', 'H', 'G', 'I', 'K'),
    frozenset('BCEFIJKL'): ('E', 'J', 'B', 'C', 'I', 'F', 'L', 'K'),
    frozenset('BCEFHJKL'): ('E', 'J', 'B', 'C', 'H', 'F', 'L', 'K'),
    frozenset('BCEFHIKL'): ('E', 'I', 'B', 'C', 'H', 'F', 'L', 'K'),
    frozenset('BCEFHIJL'): ('E', 'J', 'B', 'C', 'H', 'F', 'L', 'I'),
    frozenset('BCEFHIJK'): ('E', 'J', 'B', 'C', 'H', 'F', 'I', 'K'),
    frozenset('BCEFGJKL'): ('E', 'G', 'B', 'C', 'J', 'F', 'L', 'K'),
    frozenset('BCEFGIKL'): ('E', 'G', 'B', 'C', 'I', 'F', 'L', 'K'),
    frozenset('BCEFGIJL'): ('E', 'G', 'B', 'C', 'J', 'F', 'L', 'I'),
    frozenset('BCEFGIJK'): ('E', 'G', 'B', 'C', 'J', 'F', 'I', 'K'),
    frozenset('BCEFGHKL'): ('E', 'G', 'B', 'C', 'H', 'F', 'L', 'K'),
    frozenset('BCEFGHJL'): ('H', 'G', 'B', 'C', 'J', 'F', 'L', 'E'),
    frozenset('BCEFGHJK'): ('H', 'G', 'B', 'C', 'J', 'F', 'E', 'K'),
    frozenset('BCEFGHIL'): ('E', 'G', 'B', 'C', 'H', 'F', 'L', 'I'),
    frozenset('BCEFGHIK'): ('E', 'G', 'B', 'C', 'H', 'F', 'I', 'K'),
    frozenset('BCEFGHIJ'): ('H', 'G', 'B', 'C', 'J', 'F', 'E', 'I'),
    frozenset('BCDHIJKL'): ('H', 'J', 'B', 'C', 'I', 'D', 'L', 'K'),
    frozenset('BCDGIJKL'): ('I', 'G', 'B', 'C', 'J', 'D', 'L', 'K'),
    frozenset('BCDGHJKL'): ('H', 'G', 'B', 'C', 'J', 'D', 'L', 'K'),
    frozenset('BCDGHIKL'): ('H', 'G', 'B', 'C', 'I', 'D', 'L', 'K'),
    frozenset('BCDGHIJL'): ('H', 'G', 'B', 'C', 'J', 'D', 'L', 'I'),
    frozenset('BCDGHIJK'): ('H', 'G', 'B', 'C', 'J', 'D', 'I', 'K'),
    frozenset('BCDFIJKL'): ('C', 'J', 'B', 'D', 'I', 'F', 'L', 'K'),
    frozenset('BCDFHJKL'): ('C', 'J', 'B', 'D', 'H', 'F', 'L', 'K'),
    frozenset('BCDFHIKL'): ('C', 'I', 'B', 'D', 'H', 'F', 'L', 'K'),
    frozenset('BCDFHIJL'): ('C', 'J', 'B', 'D', 'H', 'F', 'L', 'I'),
    frozenset('BCDFHIJK'): ('C', 'J', 'B', 'D', 'H', 'F', 'I', 'K'),
    frozenset('BCDFGJKL'): ('C', 'G', 'B', 'D', 'J', 'F', 'L', 'K'),
    frozenset('BCDFGIKL'): ('C', 'G', 'B', 'D', 'I', 'F', 'L', 'K'),
    frozenset('BCDFGIJL'): ('C', 'G', 'B', 'D', 'J', 'F', 'L', 'I'),
    frozenset('BCDFGIJK'): ('C', 'G', 'B', 'D', 'J', 'F', 'I', 'K'),
    frozenset('BCDFGHKL'): ('C', 'G', 'B', 'D', 'H', 'F', 'L', 'K'),
    frozenset('BCDFGHJL'): ('C', 'G', 'B', 'D', 'H', 'F', 'L', 'J'),
    frozenset('BCDFGHJK'): ('H', 'G', 'B', 'C', 'J', 'F', 'D', 'K'),
    frozenset('BCDFGHIL'): ('C', 'G', 'B', 'D', 'H', 'F', 'L', 'I'),
    frozenset('BCDFGHIK'): ('C', 'G', 'B', 'D', 'H', 'F', 'I', 'K'),
    frozenset('BCDFGHIJ'): ('H', 'G', 'B', 'C', 'J', 'F', 'D', 'I'),
    frozenset('BCDEIJKL'): ('E', 'J', 'B', 'C', 'I', 'D', 'L', 'K'),
    frozenset('BCDEHJKL'): ('E', 'J', 'B', 'C', 'H', 'D', 'L', 'K'),
    frozenset('BCDEHIKL'): ('E', 'I', 'B', 'C', 'H', 'D', 'L', 'K'),
    frozenset('BCDEHIJL'): ('E', 'J', 'B', 'C', 'H', 'D', 'L', 'I'),
    frozenset('BCDEHIJK'): ('E', 'J', 'B', 'C', 'H', 'D', 'I', 'K'),
    frozenset('BCDEGJKL'): ('E', 'G', 'B', 'C', 'J', 'D', 'L', 'K'),
    frozenset('BCDEGIKL'): ('E', 'G', 'B', 'C', 'I', 'D', 'L', 'K'),
    frozenset('BCDEGIJL'): ('E', 'G', 'B', 'C', 'J', 'D', 'L', 'I'),
    frozenset('BCDEGIJK'): ('E', 'G', 'B', 'C', 'J', 'D', 'I', 'K'),
    frozenset('BCDEGHKL'): ('E', 'G', 'B', 'C', 'H', 'D', 'L', 'K'),
    frozenset('BCDEGHJL'): ('H', 'G', 'B', 'C', 'J', 'D', 'L', 'E'),
    frozenset('BCDEGHJK'): ('H', 'G', 'B', 'C', 'J', 'D', 'E', 'K'),
    frozenset('BCDEGHIL'): ('E', 'G', 'B', 'C', 'H', 'D', 'L', 'I'),
    frozenset('BCDEGHIK'): ('E', 'G', 'B', 'C', 'H', 'D', 'I', 'K'),
    frozenset('BCDEGHIJ'): ('H', 'G', 'B', 'C', 'J', 'D', 'E', 'I'),
    frozenset('BCDEFJKL'): ('C', 'J', 'B', 'D', 'E', 'F', 'L', 'K'),
    frozenset('BCDEFIKL'): ('C', 'E', 'B', 'D', 'I', 'F', 'L', 'K'),
    frozenset('BCDEFIJL'): ('C', 'J', 'B', 'D', 'E', 'F', 'L', 'I'),
    frozenset('BCDEFIJK'): ('C', 'J', 'B', 'D', 'E', 'F', 'I', 'K'),
    frozenset('BCDEFHKL'): ('C', 'E', 'B', 'D', 'H', 'F', 'L', 'K'),
    frozenset('BCDEFHJL'): ('C', 'J', 'B', 'D', 'H', 'F', 'L', 'E'),
    frozenset('BCDEFHJK'): ('C', 'J', 'B', 'D', 'H', 'F', 'E', 'K'),
    frozenset('BCDEFHIL'): ('C', 'E', 'B', 'D', 'H', 'F', 'L', 'I'),
    frozenset('BCDEFHIK'): ('C', 'E', 'B', 'D', 'H', 'F', 'I', 'K'),
    frozenset('BCDEFHIJ'): ('C', 'J', 'B', 'D', 'H', 'F', 'E', 'I'),
    frozenset('BCDEFGKL'): ('C', 'G', 'B', 'D', 'E', 'F', 'L', 'K'),
    frozenset('BCDEFGJL'): ('C', 'G', 'B', 'D', 'J', 'F', 'L', 'E'),
    frozenset('BCDEFGJK'): ('C', 'G', 'B', 'D', 'J', 'F', 'E', 'K'),
    frozenset('BCDEFGIL'): ('C', 'G', 'B', 'D', 'E', 'F', 'L', 'I'),
    frozenset('BCDEFGIK'): ('C', 'G', 'B', 'D', 'E', 'F', 'I', 'K'),
    frozenset('BCDEFGIJ'): ('C', 'G', 'B', 'D', 'J', 'F', 'E', 'I'),
    frozenset('BCDEFGHL'): ('C', 'G', 'B', 'D', 'H', 'F', 'L', 'E'),
    frozenset('BCDEFGHK'): ('C', 'G', 'B', 'D', 'H', 'F', 'E', 'K'),
    frozenset('BCDEFGHJ'): ('H', 'G', 'B', 'C', 'J', 'F', 'D', 'E'),
    frozenset('BCDEFGHI'): ('C', 'G', 'B', 'D', 'H', 'F', 'E', 'I'),
    frozenset('AFGHIJKL'): ('H', 'J', 'I', 'F', 'A', 'G', 'L', 'K'),
    frozenset('AEGHIJKL'): ('E', 'J', 'I', 'A', 'H', 'G', 'L', 'K'),
    frozenset('AEFHIJKL'): ('E', 'J', 'I', 'F', 'A', 'H', 'L', 'K'),
    frozenset('AEFGIJKL'): ('E', 'J', 'I', 'F', 'A', 'G', 'L', 'K'),
    frozenset('AEFGHJKL'): ('E', 'G', 'J', 'F', 'A', 'H', 'L', 'K'),
    frozenset('AEFGHIKL'): ('E', 'G', 'I', 'F', 'A', 'H', 'L', 'K'),
    frozenset('AEFGHIJL'): ('E', 'G', 'J', 'F', 'A', 'H', 'L', 'I'),
    frozenset('AEFGHIJK'): ('E', 'G', 'J', 'F', 'A', 'H', 'I', 'K'),
    frozenset('ADGHIJKL'): ('H', 'J', 'I', 'D', 'A', 'G', 'L', 'K'),
    frozenset('ADFHIJKL'): ('H', 'J', 'I', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ADFGIJKL'): ('I', 'G', 'J', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ADFGHJKL'): ('H', 'G', 'J', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ADFGHIKL'): ('H', 'G', 'I', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ADFGHIJL'): ('H', 'G', 'J', 'D', 'A', 'F', 'L', 'I'),
    frozenset('ADFGHIJK'): ('H', 'G', 'J', 'D', 'A', 'F', 'I', 'K'),
    frozenset('ADEHIJKL'): ('E', 'J', 'I', 'D', 'A', 'H', 'L', 'K'),
    frozenset('ADEGIJKL'): ('E', 'J', 'I', 'D', 'A', 'G', 'L', 'K'),
    frozenset('ADEGHJKL'): ('E', 'G', 'J', 'D', 'A', 'H', 'L', 'K'),
    frozenset('ADEGHIKL'): ('E', 'G', 'I', 'D', 'A', 'H', 'L', 'K'),
    frozenset('ADEGHIJL'): ('E', 'G', 'J', 'D', 'A', 'H', 'L', 'I'),
    frozenset('ADEGHIJK'): ('E', 'G', 'J', 'D', 'A', 'H', 'I', 'K'),
    frozenset('ADEFIJKL'): ('E', 'J', 'I', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ADEFHJKL'): ('H', 'J', 'E', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ADEFHIKL'): ('H', 'E', 'I', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ADEFHIJL'): ('H', 'J', 'E', 'D', 'A', 'F', 'L', 'I'),
    frozenset('ADEFHIJK'): ('H', 'J', 'E', 'D', 'A', 'F', 'I', 'K'),
    frozenset('ADEFGJKL'): ('E', 'G', 'J', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ADEFGIKL'): ('E', 'G', 'I', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ADEFGIJL'): ('E', 'G', 'J', 'D', 'A', 'F', 'L', 'I'),
    frozenset('ADEFGIJK'): ('E', 'G', 'J', 'D', 'A', 'F', 'I', 'K'),
    frozenset('ADEFGHKL'): ('H', 'G', 'E', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ADEFGHJL'): ('H', 'G', 'J', 'D', 'A', 'F', 'L', 'E'),
    frozenset('ADEFGHJK'): ('H', 'G', 'J', 'D', 'A', 'F', 'E', 'K'),
    frozenset('ADEFGHIL'): ('H', 'G', 'E', 'D', 'A', 'F', 'L', 'I'),
    frozenset('ADEFGHIK'): ('H', 'G', 'E', 'D', 'A', 'F', 'I', 'K'),
    frozenset('ADEFGHIJ'): ('H', 'G', 'J', 'D', 'A', 'F', 'E', 'I'),
    frozenset('ACGHIJKL'): ('H', 'J', 'I', 'C', 'A', 'G', 'L', 'K'),
    frozenset('ACFHIJKL'): ('H', 'J', 'I', 'C', 'A', 'F', 'L', 'K'),
    frozenset('ACFGIJKL'): ('I', 'G', 'J', 'C', 'A', 'F', 'L', 'K'),
    frozenset('ACFGHJKL'): ('H', 'G', 'J', 'C', 'A', 'F', 'L', 'K'),
    frozenset('ACFGHIKL'): ('H', 'G', 'I', 'C', 'A', 'F', 'L', 'K'),
    frozenset('ACFGHIJL'): ('H', 'G', 'J', 'C', 'A', 'F', 'L', 'I'),
    frozenset('ACFGHIJK'): ('H', 'G', 'J', 'C', 'A', 'F', 'I', 'K'),
    frozenset('ACEHIJKL'): ('E', 'J', 'I', 'C', 'A', 'H', 'L', 'K'),
    frozenset('ACEGIJKL'): ('E', 'J', 'I', 'C', 'A', 'G', 'L', 'K'),
    frozenset('ACEGHJKL'): ('E', 'G', 'J', 'C', 'A', 'H', 'L', 'K'),
    frozenset('ACEGHIKL'): ('E', 'G', 'I', 'C', 'A', 'H', 'L', 'K'),
    frozenset('ACEGHIJL'): ('E', 'G', 'J', 'C', 'A', 'H', 'L', 'I'),
    frozenset('ACEGHIJK'): ('E', 'G', 'J', 'C', 'A', 'H', 'I', 'K'),
    frozenset('ACEFIJKL'): ('E', 'J', 'I', 'C', 'A', 'F', 'L', 'K'),
    frozenset('ACEFHJKL'): ('H', 'J', 'E', 'C', 'A', 'F', 'L', 'K'),
    frozenset('ACEFHIKL'): ('H', 'E', 'I', 'C', 'A', 'F', 'L', 'K'),
    frozenset('ACEFHIJL'): ('H', 'J', 'E', 'C', 'A', 'F', 'L', 'I'),
    frozenset('ACEFHIJK'): ('H', 'J', 'E', 'C', 'A', 'F', 'I', 'K'),
    frozenset('ACEFGJKL'): ('E', 'G', 'J', 'C', 'A', 'F', 'L', 'K'),
    frozenset('ACEFGIKL'): ('E', 'G', 'I', 'C', 'A', 'F', 'L', 'K'),
    frozenset('ACEFGIJL'): ('E', 'G', 'J', 'C', 'A', 'F', 'L', 'I'),
    frozenset('ACEFGIJK'): ('E', 'G', 'J', 'C', 'A', 'F', 'I', 'K'),
    frozenset('ACEFGHKL'): ('H', 'G', 'E', 'C', 'A', 'F', 'L', 'K'),
    frozenset('ACEFGHJL'): ('H', 'G', 'J', 'C', 'A', 'F', 'L', 'E'),
    frozenset('ACEFGHJK'): ('H', 'G', 'J', 'C', 'A', 'F', 'E', 'K'),
    frozenset('ACEFGHIL'): ('H', 'G', 'E', 'C', 'A', 'F', 'L', 'I'),
    frozenset('ACEFGHIK'): ('H', 'G', 'E', 'C', 'A', 'F', 'I', 'K'),
    frozenset('ACEFGHIJ'): ('H', 'G', 'J', 'C', 'A', 'F', 'E', 'I'),
    frozenset('ACDHIJKL'): ('H', 'J', 'I', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ACDGIJKL'): ('I', 'G', 'J', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ACDGHJKL'): ('H', 'G', 'J', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ACDGHIKL'): ('H', 'G', 'I', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ACDGHIJL'): ('H', 'G', 'J', 'C', 'A', 'D', 'L', 'I'),
    frozenset('ACDGHIJK'): ('H', 'G', 'J', 'C', 'A', 'D', 'I', 'K'),
    frozenset('ACDFIJKL'): ('C', 'J', 'I', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ACDFHJKL'): ('H', 'J', 'F', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ACDFHIKL'): ('H', 'F', 'I', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ACDFHIJL'): ('H', 'J', 'F', 'C', 'A', 'D', 'L', 'I'),
    frozenset('ACDFHIJK'): ('H', 'J', 'F', 'C', 'A', 'D', 'I', 'K'),
    frozenset('ACDFGJKL'): ('C', 'G', 'J', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ACDFGIKL'): ('C', 'G', 'I', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ACDFGIJL'): ('C', 'G', 'J', 'D', 'A', 'F', 'L', 'I'),
    frozenset('ACDFGIJK'): ('C', 'G', 'J', 'D', 'A', 'F', 'I', 'K'),
    frozenset('ACDFGHKL'): ('H', 'G', 'F', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ACDFGHJL'): ('C', 'G', 'J', 'D', 'A', 'F', 'L', 'H'),
    frozenset('ACDFGHJK'): ('H', 'G', 'J', 'C', 'A', 'F', 'D', 'K'),
    frozenset('ACDFGHIL'): ('H', 'G', 'F', 'C', 'A', 'D', 'L', 'I'),
    frozenset('ACDFGHIK'): ('H', 'G', 'F', 'C', 'A', 'D', 'I', 'K'),
    frozenset('ACDFGHIJ'): ('H', 'G', 'J', 'C', 'A', 'F', 'D', 'I'),
    frozenset('ACDEIJKL'): ('E', 'J', 'I', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ACDEHJKL'): ('H', 'J', 'E', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ACDEHIKL'): ('H', 'E', 'I', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ACDEHIJL'): ('H', 'J', 'E', 'C', 'A', 'D', 'L', 'I'),
    frozenset('ACDEHIJK'): ('H', 'J', 'E', 'C', 'A', 'D', 'I', 'K'),
    frozenset('ACDEGJKL'): ('E', 'G', 'J', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ACDEGIKL'): ('E', 'G', 'I', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ACDEGIJL'): ('E', 'G', 'J', 'C', 'A', 'D', 'L', 'I'),
    frozenset('ACDEGIJK'): ('E', 'G', 'J', 'C', 'A', 'D', 'I', 'K'),
    frozenset('ACDEGHKL'): ('H', 'G', 'E', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ACDEGHJL'): ('H', 'G', 'J', 'C', 'A', 'D', 'L', 'E'),
    frozenset('ACDEGHJK'): ('H', 'G', 'J', 'C', 'A', 'D', 'E', 'K'),
    frozenset('ACDEGHIL'): ('H', 'G', 'E', 'C', 'A', 'D', 'L', 'I'),
    frozenset('ACDEGHIK'): ('H', 'G', 'E', 'C', 'A', 'D', 'I', 'K'),
    frozenset('ACDEGHIJ'): ('H', 'G', 'J', 'C', 'A', 'D', 'E', 'I'),
    frozenset('ACDEFJKL'): ('C', 'J', 'E', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ACDEFIKL'): ('C', 'E', 'I', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ACDEFIJL'): ('C', 'J', 'E', 'D', 'A', 'F', 'L', 'I'),
    frozenset('ACDEFIJK'): ('C', 'J', 'E', 'D', 'A', 'F', 'I', 'K'),
    frozenset('ACDEFHKL'): ('H', 'E', 'F', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ACDEFHJL'): ('H', 'J', 'F', 'C', 'A', 'D', 'L', 'E'),
    frozenset('ACDEFHJK'): ('H', 'J', 'E', 'C', 'A', 'F', 'D', 'K'),
    frozenset('ACDEFHIL'): ('H', 'E', 'F', 'C', 'A', 'D', 'L', 'I'),
    frozenset('ACDEFHIK'): ('H', 'E', 'F', 'C', 'A', 'D', 'I', 'K'),
    frozenset('ACDEFHIJ'): ('H', 'J', 'E', 'C', 'A', 'F', 'D', 'I'),
    frozenset('ACDEFGKL'): ('C', 'G', 'E', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ACDEFGJL'): ('C', 'G', 'J', 'D', 'A', 'F', 'L', 'E'),
    frozenset('ACDEFGJK'): ('C', 'G', 'J', 'D', 'A', 'F', 'E', 'K'),
    frozenset('ACDEFGIL'): ('C', 'G', 'E', 'D', 'A', 'F', 'L', 'I'),
    frozenset('ACDEFGIK'): ('C', 'G', 'E', 'D', 'A', 'F', 'I', 'K'),
    frozenset('ACDEFGIJ'): ('C', 'G', 'J', 'D', 'A', 'F', 'E', 'I'),
    frozenset('ACDEFGHL'): ('H', 'G', 'F', 'C', 'A', 'D', 'L', 'E'),
    frozenset('ACDEFGHK'): ('H', 'G', 'E', 'C', 'A', 'F', 'D', 'K'),
    frozenset('ACDEFGHJ'): ('H', 'G', 'J', 'C', 'A', 'F', 'D', 'E'),
    frozenset('ACDEFGHI'): ('H', 'G', 'E', 'C', 'A', 'F', 'D', 'I'),
    frozenset('ABGHIJKL'): ('H', 'J', 'B', 'A', 'I', 'G', 'L', 'K'),
    frozenset('ABFHIJKL'): ('H', 'J', 'B', 'A', 'I', 'F', 'L', 'K'),
    frozenset('ABFGIJKL'): ('I', 'J', 'B', 'F', 'A', 'G', 'L', 'K'),
    frozenset('ABFGHJKL'): ('H', 'J', 'B', 'F', 'A', 'G', 'L', 'K'),
    frozenset('ABFGHIKL'): ('H', 'G', 'B', 'A', 'I', 'F', 'L', 'K'),
    frozenset('ABFGHIJL'): ('H', 'J', 'B', 'F', 'A', 'G', 'L', 'I'),
    frozenset('ABFGHIJK'): ('H', 'J', 'B', 'F', 'A', 'G', 'I', 'K'),
    frozenset('ABEHIJKL'): ('E', 'J', 'B', 'A', 'I', 'H', 'L', 'K'),
    frozenset('ABEGIJKL'): ('E', 'J', 'B', 'A', 'I', 'G', 'L', 'K'),
    frozenset('ABEGHJKL'): ('E', 'J', 'B', 'A', 'H', 'G', 'L', 'K'),
    frozenset('ABEGHIKL'): ('E', 'G', 'B', 'A', 'I', 'H', 'L', 'K'),
    frozenset('ABEGHIJL'): ('E', 'J', 'B', 'A', 'H', 'G', 'L', 'I'),
    frozenset('ABEGHIJK'): ('E', 'J', 'B', 'A', 'H', 'G', 'I', 'K'),
    frozenset('ABEFIJKL'): ('E', 'J', 'B', 'A', 'I', 'F', 'L', 'K'),
    frozenset('ABEFHJKL'): ('E', 'J', 'B', 'F', 'A', 'H', 'L', 'K'),
    frozenset('ABEFHIKL'): ('E', 'I', 'B', 'F', 'A', 'H', 'L', 'K'),
    frozenset('ABEFHIJL'): ('E', 'J', 'B', 'F', 'A', 'H', 'L', 'I'),
    frozenset('ABEFHIJK'): ('E', 'J', 'B', 'F', 'A', 'H', 'I', 'K'),
    frozenset('ABEFGJKL'): ('E', 'J', 'B', 'F', 'A', 'G', 'L', 'K'),
    frozenset('ABEFGIKL'): ('E', 'G', 'B', 'A', 'I', 'F', 'L', 'K'),
    frozenset('ABEFGIJL'): ('E', 'J', 'B', 'F', 'A', 'G', 'L', 'I'),
    frozenset('ABEFGIJK'): ('E', 'J', 'B', 'F', 'A', 'G', 'I', 'K'),
    frozenset('ABEFGHKL'): ('E', 'G', 'B', 'F', 'A', 'H', 'L', 'K'),
    frozenset('ABEFGHJL'): ('H', 'J', 'B', 'F', 'A', 'G', 'L', 'E'),
    frozenset('ABEFGHJK'): ('H', 'J', 'B', 'F', 'A', 'G', 'E', 'K'),
    frozenset('ABEFGHIL'): ('E', 'G', 'B', 'F', 'A', 'H', 'L', 'I'),
    frozenset('ABEFGHIK'): ('E', 'G', 'B', 'F', 'A', 'H', 'I', 'K'),
    frozenset('ABEFGHIJ'): ('H', 'J', 'B', 'F', 'A', 'G', 'E', 'I'),
    frozenset('ABDHIJKL'): ('I', 'J', 'B', 'D', 'A', 'H', 'L', 'K'),
    frozenset('ABDGIJKL'): ('I', 'J', 'B', 'D', 'A', 'G', 'L', 'K'),
    frozenset('ABDGHJKL'): ('H', 'J', 'B', 'D', 'A', 'G', 'L', 'K'),
    frozenset('ABDGHIKL'): ('I', 'G', 'B', 'D', 'A', 'H', 'L', 'K'),
    frozenset('ABDGHIJL'): ('H', 'J', 'B', 'D', 'A', 'G', 'L', 'I'),
    frozenset('ABDGHIJK'): ('H', 'J', 'B', 'D', 'A', 'G', 'I', 'K'),
    frozenset('ABDFIJKL'): ('I', 'J', 'B', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ABDFHJKL'): ('H', 'J', 'B', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ABDFHIKL'): ('H', 'I', 'B', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ABDFHIJL'): ('H', 'J', 'B', 'D', 'A', 'F', 'L', 'I'),
    frozenset('ABDFHIJK'): ('H', 'J', 'B', 'D', 'A', 'F', 'I', 'K'),
    frozenset('ABDFGJKL'): ('F', 'J', 'B', 'D', 'A', 'G', 'L', 'K'),
    frozenset('ABDFGIKL'): ('I', 'G', 'B', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ABDFGIJL'): ('F', 'J', 'B', 'D', 'A', 'G', 'L', 'I'),
    frozenset('ABDFGIJK'): ('F', 'J', 'B', 'D', 'A', 'G', 'I', 'K'),
    frozenset('ABDFGHKL'): ('H', 'G', 'B', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ABDFGHJL'): ('H', 'G', 'B', 'D', 'A', 'F', 'L', 'J'),
    frozenset('ABDFGHJK'): ('H', 'G', 'B', 'D', 'A', 'F', 'J', 'K'),
    frozenset('ABDFGHIL'): ('H', 'G', 'B', 'D', 'A', 'F', 'L', 'I'),
    frozenset('ABDFGHIK'): ('H', 'G', 'B', 'D', 'A', 'F', 'I', 'K'),
    frozenset('ABDFGHIJ'): ('H', 'G', 'B', 'D', 'A', 'F', 'I', 'J'),
    frozenset('ABDEIJKL'): ('E', 'J', 'B', 'A', 'I', 'D', 'L', 'K'),
    frozenset('ABDEHJKL'): ('E', 'J', 'B', 'D', 'A', 'H', 'L', 'K'),
    frozenset('ABDEHIKL'): ('E', 'I', 'B', 'D', 'A', 'H', 'L', 'K'),
    frozenset('ABDEHIJL'): ('E', 'J', 'B', 'D', 'A', 'H', 'L', 'I'),
    frozenset('ABDEHIJK'): ('E', 'J', 'B', 'D', 'A', 'H', 'I', 'K'),
    frozenset('ABDEGJKL'): ('E', 'J', 'B', 'D', 'A', 'G', 'L', 'K'),
    frozenset('ABDEGIKL'): ('E', 'G', 'B', 'A', 'I', 'D', 'L', 'K'),
    frozenset('ABDEGIJL'): ('E', 'J', 'B', 'D', 'A', 'G', 'L', 'I'),
    frozenset('ABDEGIJK'): ('E', 'J', 'B', 'D', 'A', 'G', 'I', 'K'),
    frozenset('ABDEGHKL'): ('E', 'G', 'B', 'D', 'A', 'H', 'L', 'K'),
    frozenset('ABDEGHJL'): ('H', 'J', 'B', 'D', 'A', 'G', 'L', 'E'),
    frozenset('ABDEGHJK'): ('H', 'J', 'B', 'D', 'A', 'G', 'E', 'K'),
    frozenset('ABDEGHIL'): ('E', 'G', 'B', 'D', 'A', 'H', 'L', 'I'),
    frozenset('ABDEGHIK'): ('E', 'G', 'B', 'D', 'A', 'H', 'I', 'K'),
    frozenset('ABDEGHIJ'): ('H', 'J', 'B', 'D', 'A', 'G', 'E', 'I'),
    frozenset('ABDEFJKL'): ('E', 'J', 'B', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ABDEFIKL'): ('E', 'I', 'B', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ABDEFIJL'): ('E', 'J', 'B', 'D', 'A', 'F', 'L', 'I'),
    frozenset('ABDEFIJK'): ('E', 'J', 'B', 'D', 'A', 'F', 'I', 'K'),
    frozenset('ABDEFHKL'): ('H', 'E', 'B', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ABDEFHJL'): ('H', 'J', 'B', 'D', 'A', 'F', 'L', 'E'),
    frozenset('ABDEFHJK'): ('H', 'J', 'B', 'D', 'A', 'F', 'E', 'K'),
    frozenset('ABDEFHIL'): ('H', 'E', 'B', 'D', 'A', 'F', 'L', 'I'),
    frozenset('ABDEFHIK'): ('H', 'E', 'B', 'D', 'A', 'F', 'I', 'K'),
    frozenset('ABDEFHIJ'): ('H', 'J', 'B', 'D', 'A', 'F', 'E', 'I'),
    frozenset('ABDEFGKL'): ('E', 'G', 'B', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ABDEFGJL'): ('E', 'G', 'B', 'D', 'A', 'F', 'L', 'J'),
    frozenset('ABDEFGJK'): ('E', 'G', 'B', 'D', 'A', 'F', 'J', 'K'),
    frozenset('ABDEFGIL'): ('E', 'G', 'B', 'D', 'A', 'F', 'L', 'I'),
    frozenset('ABDEFGIK'): ('E', 'G', 'B', 'D', 'A', 'F', 'I', 'K'),
    frozenset('ABDEFGIJ'): ('E', 'G', 'B', 'D', 'A', 'F', 'I', 'J'),
    frozenset('ABDEFGHL'): ('H', 'G', 'B', 'D', 'A', 'F', 'L', 'E'),
    frozenset('ABDEFGHK'): ('H', 'G', 'B', 'D', 'A', 'F', 'E', 'K'),
    frozenset('ABDEFGHJ'): ('H', 'G', 'B', 'D', 'A', 'F', 'E', 'J'),
    frozenset('ABDEFGHI'): ('H', 'G', 'B', 'D', 'A', 'F', 'E', 'I'),
    frozenset('ABCHIJKL'): ('I', 'J', 'B', 'C', 'A', 'H', 'L', 'K'),
    frozenset('ABCGIJKL'): ('I', 'J', 'B', 'C', 'A', 'G', 'L', 'K'),
    frozenset('ABCGHJKL'): ('H', 'J', 'B', 'C', 'A', 'G', 'L', 'K'),
    frozenset('ABCGHIKL'): ('I', 'G', 'B', 'C', 'A', 'H', 'L', 'K'),
    frozenset('ABCGHIJL'): ('H', 'J', 'B', 'C', 'A', 'G', 'L', 'I'),
    frozenset('ABCGHIJK'): ('H', 'J', 'B', 'C', 'A', 'G', 'I', 'K'),
    frozenset('ABCFIJKL'): ('I', 'J', 'B', 'C', 'A', 'F', 'L', 'K'),
    frozenset('ABCFHJKL'): ('H', 'J', 'B', 'C', 'A', 'F', 'L', 'K'),
    frozenset('ABCFHIKL'): ('H', 'I', 'B', 'C', 'A', 'F', 'L', 'K'),
    frozenset('ABCFHIJL'): ('H', 'J', 'B', 'C', 'A', 'F', 'L', 'I'),
    frozenset('ABCFHIJK'): ('H', 'J', 'B', 'C', 'A', 'F', 'I', 'K'),
    frozenset('ABCFGJKL'): ('C', 'J', 'B', 'F', 'A', 'G', 'L', 'K'),
    frozenset('ABCFGIKL'): ('I', 'G', 'B', 'C', 'A', 'F', 'L', 'K'),
    frozenset('ABCFGIJL'): ('C', 'J', 'B', 'F', 'A', 'G', 'L', 'I'),
    frozenset('ABCFGIJK'): ('C', 'J', 'B', 'F', 'A', 'G', 'I', 'K'),
    frozenset('ABCFGHKL'): ('H', 'G', 'B', 'C', 'A', 'F', 'L', 'K'),
    frozenset('ABCFGHJL'): ('H', 'G', 'B', 'C', 'A', 'F', 'L', 'J'),
    frozenset('ABCFGHJK'): ('H', 'G', 'B', 'C', 'A', 'F', 'J', 'K'),
    frozenset('ABCFGHIL'): ('H', 'G', 'B', 'C', 'A', 'F', 'L', 'I'),
    frozenset('ABCFGHIK'): ('H', 'G', 'B', 'C', 'A', 'F', 'I', 'K'),
    frozenset('ABCFGHIJ'): ('H', 'G', 'B', 'C', 'A', 'F', 'I', 'J'),
    frozenset('ABCEIJKL'): ('E', 'J', 'B', 'A', 'I', 'C', 'L', 'K'),
    frozenset('ABCEHJKL'): ('E', 'J', 'B', 'C', 'A', 'H', 'L', 'K'),
    frozenset('ABCEHIKL'): ('E', 'I', 'B', 'C', 'A', 'H', 'L', 'K'),
    frozenset('ABCEHIJL'): ('E', 'J', 'B', 'C', 'A', 'H', 'L', 'I'),
    frozenset('ABCEHIJK'): ('E', 'J', 'B', 'C', 'A', 'H', 'I', 'K'),
    frozenset('ABCEGJKL'): ('E', 'J', 'B', 'C', 'A', 'G', 'L', 'K'),
    frozenset('ABCEGIKL'): ('E', 'G', 'B', 'A', 'I', 'C', 'L', 'K'),
    frozenset('ABCEGIJL'): ('E', 'J', 'B', 'C', 'A', 'G', 'L', 'I'),
    frozenset('ABCEGIJK'): ('E', 'J', 'B', 'C', 'A', 'G', 'I', 'K'),
    frozenset('ABCEGHKL'): ('E', 'G', 'B', 'C', 'A', 'H', 'L', 'K'),
    frozenset('ABCEGHJL'): ('H', 'J', 'B', 'C', 'A', 'G', 'L', 'E'),
    frozenset('ABCEGHJK'): ('H', 'J', 'B', 'C', 'A', 'G', 'E', 'K'),
    frozenset('ABCEGHIL'): ('E', 'G', 'B', 'C', 'A', 'H', 'L', 'I'),
    frozenset('ABCEGHIK'): ('E', 'G', 'B', 'C', 'A', 'H', 'I', 'K'),
    frozenset('ABCEGHIJ'): ('H', 'J', 'B', 'C', 'A', 'G', 'E', 'I'),
    frozenset('ABCEFJKL'): ('E', 'J', 'B', 'C', 'A', 'F', 'L', 'K'),
    frozenset('ABCEFIKL'): ('E', 'I', 'B', 'C', 'A', 'F', 'L', 'K'),
    frozenset('ABCEFIJL'): ('E', 'J', 'B', 'C', 'A', 'F', 'L', 'I'),
    frozenset('ABCEFIJK'): ('E', 'J', 'B', 'C', 'A', 'F', 'I', 'K'),
    frozenset('ABCEFHKL'): ('H', 'E', 'B', 'C', 'A', 'F', 'L', 'K'),
    frozenset('ABCEFHJL'): ('H', 'J', 'B', 'C', 'A', 'F', 'L', 'E'),
    frozenset('ABCEFHJK'): ('H', 'J', 'B', 'C', 'A', 'F', 'E', 'K'),
    frozenset('ABCEFHIL'): ('H', 'E', 'B', 'C', 'A', 'F', 'L', 'I'),
    frozenset('ABCEFHIK'): ('H', 'E', 'B', 'C', 'A', 'F', 'I', 'K'),
    frozenset('ABCEFHIJ'): ('H', 'J', 'B', 'C', 'A', 'F', 'E', 'I'),
    frozenset('ABCEFGKL'): ('E', 'G', 'B', 'C', 'A', 'F', 'L', 'K'),
    frozenset('ABCEFGJL'): ('E', 'G', 'B', 'C', 'A', 'F', 'L', 'J'),
    frozenset('ABCEFGJK'): ('E', 'G', 'B', 'C', 'A', 'F', 'J', 'K'),
    frozenset('ABCEFGIL'): ('E', 'G', 'B', 'C', 'A', 'F', 'L', 'I'),
    frozenset('ABCEFGIK'): ('E', 'G', 'B', 'C', 'A', 'F', 'I', 'K'),
    frozenset('ABCEFGIJ'): ('E', 'G', 'B', 'C', 'A', 'F', 'I', 'J'),
    frozenset('ABCEFGHL'): ('H', 'G', 'B', 'C', 'A', 'F', 'L', 'E'),
    frozenset('ABCEFGHK'): ('H', 'G', 'B', 'C', 'A', 'F', 'E', 'K'),
    frozenset('ABCEFGHJ'): ('H', 'G', 'B', 'C', 'A', 'F', 'E', 'J'),
    frozenset('ABCEFGHI'): ('H', 'G', 'B', 'C', 'A', 'F', 'E', 'I'),
    frozenset('ABCDIJKL'): ('I', 'J', 'B', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ABCDHJKL'): ('H', 'J', 'B', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ABCDHIKL'): ('H', 'I', 'B', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ABCDHIJL'): ('H', 'J', 'B', 'C', 'A', 'D', 'L', 'I'),
    frozenset('ABCDHIJK'): ('H', 'J', 'B', 'C', 'A', 'D', 'I', 'K'),
    frozenset('ABCDGJKL'): ('C', 'J', 'B', 'D', 'A', 'G', 'L', 'K'),
    frozenset('ABCDGIKL'): ('I', 'G', 'B', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ABCDGIJL'): ('C', 'J', 'B', 'D', 'A', 'G', 'L', 'I'),
    frozenset('ABCDGIJK'): ('C', 'J', 'B', 'D', 'A', 'G', 'I', 'K'),
    frozenset('ABCDGHKL'): ('H', 'G', 'B', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ABCDGHJL'): ('H', 'G', 'B', 'C', 'A', 'D', 'L', 'J'),
    frozenset('ABCDGHJK'): ('H', 'G', 'B', 'C', 'A', 'D', 'J', 'K'),
    frozenset('ABCDGHIL'): ('H', 'G', 'B', 'C', 'A', 'D', 'L', 'I'),
    frozenset('ABCDGHIK'): ('H', 'G', 'B', 'C', 'A', 'D', 'I', 'K'),
    frozenset('ABCDGHIJ'): ('H', 'G', 'B', 'C', 'A', 'D', 'I', 'J'),
    frozenset('ABCDFJKL'): ('C', 'J', 'B', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ABCDFIKL'): ('C', 'I', 'B', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ABCDFIJL'): ('C', 'J', 'B', 'D', 'A', 'F', 'L', 'I'),
    frozenset('ABCDFIJK'): ('C', 'J', 'B', 'D', 'A', 'F', 'I', 'K'),
    frozenset('ABCDFHKL'): ('H', 'F', 'B', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ABCDFHJL'): ('C', 'J', 'B', 'D', 'A', 'F', 'L', 'H'),
    frozenset('ABCDFHJK'): ('H', 'J', 'B', 'C', 'A', 'F', 'D', 'K'),
    frozenset('ABCDFHIL'): ('H', 'F', 'B', 'C', 'A', 'D', 'L', 'I'),
    frozenset('ABCDFHIK'): ('H', 'F', 'B', 'C', 'A', 'D', 'I', 'K'),
    frozenset('ABCDFHIJ'): ('H', 'J', 'B', 'C', 'A', 'F', 'D', 'I'),
    frozenset('ABCDFGKL'): ('C', 'G', 'B', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ABCDFGJL'): ('C', 'G', 'B', 'D', 'A', 'F', 'L', 'J'),
    frozenset('ABCDFGJK'): ('C', 'G', 'B', 'D', 'A', 'F', 'J', 'K'),
    frozenset('ABCDFGIL'): ('C', 'G', 'B', 'D', 'A', 'F', 'L', 'I'),
    frozenset('ABCDFGIK'): ('C', 'G', 'B', 'D', 'A', 'F', 'I', 'K'),
    frozenset('ABCDFGIJ'): ('C', 'G', 'B', 'D', 'A', 'F', 'I', 'J'),
    frozenset('ABCDFGHL'): ('C', 'G', 'B', 'D', 'A', 'F', 'L', 'H'),
    frozenset('ABCDFGHK'): ('H', 'G', 'B', 'C', 'A', 'F', 'D', 'K'),
    frozenset('ABCDFGHJ'): ('H', 'G', 'B', 'C', 'A', 'F', 'D', 'J'),
    frozenset('ABCDFGHI'): ('H', 'G', 'B', 'C', 'A', 'F', 'D', 'I'),
    frozenset('ABCDEJKL'): ('E', 'J', 'B', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ABCDEIKL'): ('E', 'I', 'B', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ABCDEIJL'): ('E', 'J', 'B', 'C', 'A', 'D', 'L', 'I'),
    frozenset('ABCDEIJK'): ('E', 'J', 'B', 'C', 'A', 'D', 'I', 'K'),
    frozenset('ABCDEHKL'): ('H', 'E', 'B', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ABCDEHJL'): ('H', 'J', 'B', 'C', 'A', 'D', 'L', 'E'),
    frozenset('ABCDEHJK'): ('H', 'J', 'B', 'C', 'A', 'D', 'E', 'K'),
    frozenset('ABCDEHIL'): ('H', 'E', 'B', 'C', 'A', 'D', 'L', 'I'),
    frozenset('ABCDEHIK'): ('H', 'E', 'B', 'C', 'A', 'D', 'I', 'K'),
    frozenset('ABCDEHIJ'): ('H', 'J', 'B', 'C', 'A', 'D', 'E', 'I'),
    frozenset('ABCDEGKL'): ('E', 'G', 'B', 'C', 'A', 'D', 'L', 'K'),
    frozenset('ABCDEGJL'): ('E', 'G', 'B', 'C', 'A', 'D', 'L', 'J'),
    frozenset('ABCDEGJK'): ('E', 'G', 'B', 'C', 'A', 'D', 'J', 'K'),
    frozenset('ABCDEGIL'): ('E', 'G', 'B', 'C', 'A', 'D', 'L', 'I'),
    frozenset('ABCDEGIK'): ('E', 'G', 'B', 'C', 'A', 'D', 'I', 'K'),
    frozenset('ABCDEGIJ'): ('E', 'G', 'B', 'C', 'A', 'D', 'I', 'J'),
    frozenset('ABCDEGHL'): ('H', 'G', 'B', 'C', 'A', 'D', 'L', 'E'),
    frozenset('ABCDEGHK'): ('H', 'G', 'B', 'C', 'A', 'D', 'E', 'K'),
    frozenset('ABCDEGHJ'): ('H', 'G', 'B', 'C', 'A', 'D', 'E', 'J'),
    frozenset('ABCDEGHI'): ('H', 'G', 'B', 'C', 'A', 'D', 'E', 'I'),
    frozenset('ABCDEFKL'): ('C', 'E', 'B', 'D', 'A', 'F', 'L', 'K'),
    frozenset('ABCDEFJL'): ('C', 'J', 'B', 'D', 'A', 'F', 'L', 'E'),
    frozenset('ABCDEFJK'): ('C', 'J', 'B', 'D', 'A', 'F', 'E', 'K'),
    frozenset('ABCDEFIL'): ('C', 'E', 'B', 'D', 'A', 'F', 'L', 'I'),
    frozenset('ABCDEFIK'): ('C', 'E', 'B', 'D', 'A', 'F', 'I', 'K'),
    frozenset('ABCDEFIJ'): ('C', 'J', 'B', 'D', 'A', 'F', 'E', 'I'),
    frozenset('ABCDEFHL'): ('H', 'F', 'B', 'C', 'A', 'D', 'L', 'E'),
    frozenset('ABCDEFHK'): ('H', 'E', 'B', 'C', 'A', 'F', 'D', 'K'),
    frozenset('ABCDEFHJ'): ('H', 'J', 'B', 'C', 'A', 'F', 'D', 'E'),
    frozenset('ABCDEFHI'): ('H', 'E', 'B', 'C', 'A', 'F', 'D', 'I'),
    frozenset('ABCDEFGL'): ('C', 'G', 'B', 'D', 'A', 'F', 'L', 'E'),
    frozenset('ABCDEFGK'): ('C', 'G', 'B', 'D', 'A', 'F', 'E', 'K'),
    frozenset('ABCDEFGJ'): ('C', 'G', 'B', 'D', 'A', 'F', 'E', 'J'),
    frozenset('ABCDEFGI'): ('C', 'G', 'B', 'D', 'A', 'F', 'E', 'I'),
    frozenset('ABCDEFGH'): ('H', 'G', 'B', 'C', 'A', 'F', 'D', 'E'),
}

# ---------------------------------------------------------------------------
# Helpers para tiebreaker FIFA 2026
# ---------------------------------------------------------------------------

def _h2h_stats(team_ids: list[int], resultados: list[dict]) -> dict[int, dict]:
    """Calcula estadisticas head-to-head entre un subconjunto de equipos."""
    ids = set(team_ids)
    h2h: dict[int, dict] = {eid: {"pts": 0, "gd": 0, "gf": 0} for eid in team_ids}
    for r in resultados:
        lid, vid, gl, gv = r["lid"], r["vid"], r["gl"], r["gv"]
        if lid not in ids or vid not in ids:
            continue
        h2h[lid]["gf"] += gl
        h2h[lid]["gd"] += gl - gv
        h2h[vid]["gf"] += gv
        h2h[vid]["gd"] += gv - gl
        if gl > gv:
            h2h[lid]["pts"] += 3
        elif gv > gl:
            h2h[vid]["pts"] += 3
        else:
            h2h[lid]["pts"] += 1
            h2h[vid]["pts"] += 1
    return h2h


def _sort_grupo(equipos: list[dict], resultados: list[dict]) -> list[dict]:
    """
    Ordena equipos dentro de un grupo con criterios de desempate FIFA 2026
    (Art. 13 del Reglamento de Competición):

    1. Puntos (general)
    2. Diferencia de goles (general)
    3. Goles marcados (general)
    4. Puntos H2H (entre equipos empatados)
    5. Diferencia de goles H2H
    6. Goles marcados H2H
    7. Fair play: amarillas×1 + rojas×3  (menor = mejor conducta)
    8. Ranking FIFA (menor = mejor)
    9. Nombre (alfabético, solo para determinismo)

    Nota: fair_play_pts debe estar calculado y presente en cada equipo.
    Si = 0 para todos, el criterio 7 no tiene efecto (datos de tarjetas no disponibles).
    """
    def primary_key(e: dict) -> tuple:
        return (-e["pts"], -e["gd"], -e["gf"])

    sorted_all = sorted(equipos, key=primary_key)
    result: list[dict] = []
    i = 0

    while i < len(sorted_all):
        j = i + 1
        while j < len(sorted_all) and primary_key(sorted_all[j]) == primary_key(sorted_all[i]):
            j += 1
        tied = sorted_all[i:j]

        if len(tied) == 1:
            result.extend(tied)
            i = j
            continue

        ids = [e["equipo_id"] for e in tied]
        h2h = _h2h_stats(ids, resultados)

        def h2h_key(e: dict) -> tuple:
            s = h2h[e["equipo_id"]]
            return (-s["pts"], -s["gd"], -s["gf"])

        tied_h2h = sorted(tied, key=h2h_key)

        k = 0
        while k < len(tied_h2h):
            m2 = k + 1
            while m2 < len(tied_h2h) and h2h_key(tied_h2h[m2]) == h2h_key(tied_h2h[k]):
                m2 += 1
            sub = tied_h2h[k:m2]
            if len(sub) > 1:
                sub = sorted(sub, key=lambda e: (
                    e.get("fair_play_pts") or 0,
                    e.get("fifa_ranking") or 9999,
                    (e.get("nombre_es") or e.get("nombre", "")),
                ))
            result.extend(sub)
            k = m2

        i = j

    return result


# ---------------------------------------------------------------------------
# Standings simulados por apostador
# ---------------------------------------------------------------------------

async def simular_standings_usuario(
    db: AsyncSession,
    apostador_id: int,
    torneo_id: int,
) -> dict[str, dict]:
    """
    Standings simulados basados en apuestas del apostador.
    Prioridad: prediccion > resultado real > no contar.
    Tiebreaker: H2H + fair_play_pts + fifa_ranking.
    """
    rf = await db.execute(
        text("SELECT id, nombre FROM fase WHERE torneo_id = :tid AND tipo = 'grupo' ORDER BY nombre"),
        {"tid": torneo_id},
    )
    fases = [dict(r) for r in rf.mappings()]
    resultado: dict[str, dict] = {}

    for fase in fases:
        fid = fase["id"]
        grupo_letra = fase["nombre"].replace("Grupo ", "").strip()

        rp = await db.execute(
            text("""
                SELECT e.id AS equipo_id, e.nombre, e.nombre_es, e.logo_url,
                       e.fifa_ranking,
                       COALESCE(pa.fair_play_pts, 0) AS fair_play_pts
                FROM participacion pa
                JOIN equipo e ON e.id = pa.equipo_id
                WHERE pa.fase_id = :fid
            """),
            {"fid": fid},
        )
        stats: dict[int, dict] = {}
        for r in rp.mappings():
            eid = r["equipo_id"]
            stats[eid] = {
                "equipo_id": eid, "nombre": r["nombre"], "nombre_es": r["nombre_es"],
                "logo_url": r["logo_url"], "fifa_ranking": r["fifa_ranking"],
                "fair_play_pts": r["fair_play_pts"], "grupo": grupo_letra,
                "pj": 0, "pg": 0, "pe": 0, "pp": 0, "gf": 0, "gc": 0, "gd": 0, "pts": 0,
            }

        rm = await db.execute(
            text("""
                SELECT p.equipo_local_id AS local_id, p.equipo_visitante_id AS visit_id,
                       p.goles_local, p.goles_visitante, p.estado,
                       a.pred_local, a.pred_visitante
                FROM partido p
                LEFT JOIN apuesta a ON a.partido_id = p.id AND a.apostador_id = :uid
                WHERE p.fase_id = :fid AND p.torneo_id = :tid
                  AND p.equipo_local_id IS NOT NULL AND p.equipo_visitante_id IS NOT NULL
            """),
            {"fid": fid, "tid": torneo_id, "uid": apostador_id},
        )

        resultados_raw: list[dict] = []
        for p in rm.mappings():
            lid, vid = p["local_id"], p["visit_id"]
            if lid not in stats or vid not in stats:
                continue
            if p["pred_local"] is not None and p["pred_visitante"] is not None:
                gl, gv = int(p["pred_local"]), int(p["pred_visitante"])
            elif p["estado"] == "finalizado" and p["goles_local"] is not None:
                gl, gv = int(p["goles_local"]), int(p["goles_visitante"])
            else:
                continue

            resultados_raw.append({"lid": lid, "vid": vid, "gl": gl, "gv": gv})
            stats[lid]["pj"] += 1; stats[lid]["gf"] += gl; stats[lid]["gc"] += gv; stats[lid]["gd"] += gl - gv
            stats[vid]["pj"] += 1; stats[vid]["gf"] += gv; stats[vid]["gc"] += gl; stats[vid]["gd"] += gv - gl
            if gl > gv:
                stats[lid]["pg"] += 1; stats[lid]["pts"] += 3; stats[vid]["pp"] += 1
            elif gl < gv:
                stats[vid]["pg"] += 1; stats[vid]["pts"] += 3; stats[lid]["pp"] += 1
            else:
                stats[lid]["pe"] += 1; stats[lid]["pts"] += 1
                stats[vid]["pe"] += 1; stats[vid]["pts"] += 1

        sorted_eqs = _sort_grupo(list(stats.values()), resultados_raw)
        for idx, eq in enumerate(sorted_eqs):
            eq["pos"] = idx + 1

        resultado[grupo_letra] = {"fase_id": fid, "grupo": grupo_letra, "equipos": sorted_eqs}

    return resultado


# ---------------------------------------------------------------------------
# Seleccion de mejores terceros (criterio FIFA 2026)
# ---------------------------------------------------------------------------

def seleccionar_mejores_terceros(
    standings_por_grupo: dict[str, dict],
    fill_incomplete: bool = True,
    sort_unified: bool = False,
) -> tuple[list[dict], list[dict]]:
    """
    Rankea los 12 terceros (uno por grupo) y devuelve (mejores_8, eliminados_4).

    Criterio FIFA 2026 para comparar terceros ENTRE grupos (Art. 13.3):
      1. Puntos
      2. Diferencia de goles
      3. Goles marcados
      4. Fair play: amarillas×1 + rojas×3  (menor = mejor conducta)
      5. Ranking FIFA (menor = mejor)
      6. Nombre del grupo (solo para determinismo)

    Nota: H2H NO aplica al comparar terceros de grupos distintos (FIFA Art. 13.3).

    fill_incomplete=True (default): rellena slots faltantes con los mejores
      terceros de grupos incompletos (útil para bracket de apostador / simulación).
      Los terceros de grupos completos se ordenan PRIMERO y luego se agregan los
      incompletos para llegar a 8.
    fill_incomplete=False: solo usa terceros de grupos completos; si hay < 8
      grupos completos los slots restantes quedan vacíos → el bracket muestra TBD.

    sort_unified=True: ordena TODOS los terceros juntos (completos e incompletos)
      sin distinción, igual que el endpoint mejores-terceros-provisorios. Usar para
      el bracket REAL provisional cuando hay grupos aún en curso — produce el mismo
      ranking que la tabla de provisorios y asegura coherencia entre vistas.
    """
    _sort_key = lambda e: (
        -e["pts"], -e["gd"], -e["gf"],
        e.get("fair_play_pts") or 0,
        e.get("fifa_ranking") or 9999,
        e["grupo"],
    )

    terceros = []
    incompletos: list[dict] = []

    for grupo_letra, grupo in standings_por_grupo.items():
        eqs = grupo["equipos"]
        if len(eqs) < 3:
            continue
        pj_esperado = len(eqs) - 1
        pj_min = min(eq.get("pj", 0) for eq in eqs)
        tercero = {**eqs[2], "grupo": grupo_letra}
        if pj_min >= pj_esperado:
            terceros.append(tercero)
        else:
            incompletos.append(tercero)

    if sort_unified:
        # Ordena TODOS juntos (mismo criterio que mejores-terceros-provisorios).
        # Produce ranking coherente con la vista provisional; no da prioridad
        # a grupos completos sobre incompletos.
        todos = sorted(terceros + incompletos, key=_sort_key)
        return todos[:8], todos[8:]

    # Modo por fases: completos primero, luego incompletos rellanan hasta 8
    terceros.sort(key=_sort_key)

    if fill_incomplete and len(terceros) < 8 and incompletos:
        incompletos.sort(key=_sort_key)
        faltantes = 8 - len(terceros)
        terceros.extend(incompletos[:faltantes])
        incompletos = incompletos[faltantes:]

    todos = terceros + incompletos
    return todos[:8], todos[8:]


# ---------------------------------------------------------------------------
# Armar Ronda de 32
# ---------------------------------------------------------------------------

def armar_ronda32(
    standings_por_grupo: dict[str, dict],
    mejores_terceros: list[dict],
) -> list[dict]:
    """Construye los 16 partidos de Ronda de 32 (nums 73-88)."""
    primeros: dict[str, dict] = {}
    segundos: dict[str, dict] = {}
    terceros_map: dict[str, dict] = {}

    for letra, grupo in standings_por_grupo.items():
        eqs = grupo["equipos"]
        if eqs:
            primeros[letra] = {**eqs[0], "slot": f"1{letra}"}
        if len(eqs) >= 2:
            segundos[letra] = {**eqs[1], "slot": f"2{letra}"}

    for t in mejores_terceros:
        terceros_map[t["grupo"]] = {**t, "slot": f"3{t['grupo']}"}

    grupos_clasificados = frozenset(terceros_map.keys())
    combinacion = TERCEROS_COMBINACIONES.get(grupos_clasificados)

    tercero_de: dict[str, str | None] = {k: None for k in "ABDEGIKL"}
    if combinacion:
        vs_1A, vs_1B, vs_1D, vs_1E, vs_1G, vs_1I, vs_1K, vs_1L = combinacion
        tercero_de = {
            "A": vs_1A, "B": vs_1B, "D": vs_1D, "E": vs_1E,
            "G": vs_1G, "I": vs_1I, "K": vs_1K, "L": vs_1L,
        }

    def t(g: str) -> dict | None:
        src = tercero_de.get(g)
        return terceros_map.get(src) if src else None

    def m(num: int, local: dict | None, visitante: dict | None) -> dict:
        return {"num": num, "local": local, "visitante": visitante}

    return [
        m(73, segundos.get("A"),  segundos.get("B")),
        m(74, primeros.get("E"),  t("E")),
        m(75, primeros.get("F"),  segundos.get("C")),
        m(76, primeros.get("C"),  segundos.get("F")),
        m(77, primeros.get("I"),  t("I")),
        m(78, segundos.get("E"),  segundos.get("I")),
        m(79, primeros.get("A"),  t("A")),
        m(80, primeros.get("L"),  t("L")),
        m(81, primeros.get("D"),  t("D")),
        m(82, primeros.get("G"),  t("G")),
        m(83, segundos.get("K"),  segundos.get("L")),
        m(84, primeros.get("H"),  segundos.get("J")),
        m(85, primeros.get("B"),  t("B")),
        m(86, primeros.get("J"),  segundos.get("H")),
        m(87, primeros.get("K"),  t("K")),
        m(88, segundos.get("D"),  segundos.get("G")),
    ]


# ---------------------------------------------------------------------------
# Propagación KO completa según pronósticos del apostador
# ---------------------------------------------------------------------------

async def propagar_ko_usuario(
    db: AsyncSession,
    apostador_id: int,
    torneo_id: int,
    r32_bracket: list[dict],
) -> list[dict]:
    """Propaga el bracket KO completo (R32 → Final) usando las predicciones del
    apostador. Para partidos YA FINALIZADOS usa el ganador/perdedor real.
    Para partidos no finalizados usa pred_local vs pred_visitante; empate/sin
    predicción → FIFA ranking.

    Retorna lista de matches con la misma estructura que /bracket-real:
      {num, tipo, local_id, visit_id, local, visitante,
       pred_gl, pred_gv, pred_penales, winner_id, loser_id}
    """
    from app.services.ko_scoring import build_num_maps, KO_FEEDERS, TIPO_NUM_RANGE

    maps = await build_num_maps(db, torneo_id)
    num2pid = maps.get("num2pid", {})
    num2tipo = maps.get("num2tipo", {})

    # ── Resultados reales de todos los partidos KO ─────────────────────────
    ko_pids = list(num2pid.values())
    real_results: dict[int, dict] = {}  # pid → {estado, gl, gv, local_id, visit_id, winner_id, loser_id}
    if ko_pids:
        r = await db.execute(
            text("""
                SELECT p.id AS pid, p.estado,
                       p.goles_local AS gl, p.goles_visitante AS gv,
                       p.equipo_local_id AS local_id,
                       p.equipo_visitante_id AS visit_id,
                       p.penales_local, p.penales_visitante
                FROM partido p
                WHERE p.id = ANY(:pids)
            """),
            {"pids": ko_pids},
        )
        for row in r.mappings():
            d = dict(row)
            pid = d["pid"]
            # Determinar ganador real si el partido está finalizado
            if d["estado"] == "finalizado" and d["gl"] is not None and d["gv"] is not None:
                if d["gl"] > d["gv"]:
                    d["winner_id"] = d["local_id"]
                    d["loser_id"]  = d["visit_id"]
                elif d["gv"] > d["gl"]:
                    d["winner_id"] = d["visit_id"]
                    d["loser_id"]  = d["local_id"]
                else:
                    # Empate en 90' → resolver por penales si están disponibles
                    pl, pv = d.get("penales_local"), d.get("penales_visitante")
                    if pl is not None and pv is not None:
                        d["winner_id"] = d["local_id"] if pl > pv else d["visit_id"]
                        d["loser_id"]  = d["visit_id"] if pl > pv else d["local_id"]
                    else:
                        d["winner_id"] = None
                        d["loser_id"]  = None
            else:
                d["winner_id"] = None
                d["loser_id"]  = None
            real_results[pid] = d

    # ── Apuestas KO del apostador ──────────────────────────────────────────
    if ko_pids:
        r = await db.execute(
            text("""
                SELECT partido_id, pred_local, pred_visitante, pred_penales
                FROM apuesta
                WHERE apostador_id = :uid AND partido_id = ANY(:pids)
            """),
            {"uid": apostador_id, "pids": ko_pids},
        )
        ko_aps: dict[int, dict] = {row["partido_id"]: dict(row) for row in r.mappings()}
    else:
        ko_aps = {}

    # ── Datos de equipos ──────────────────────────────────────────────────
    r = await db.execute(
        text("SELECT id, nombre, nombre_es, logo_url, fifa_ranking FROM equipo")
    )
    eq_data: dict[int, dict] = {row["id"]: dict(row) for row in r.mappings()}

    # ── Helper: ganador/perdedor según predicción ─────────────────────────
    def _winner_loser_pred(local_id: int | None, visit_id: int | None,
                           pred_gl, pred_gv) -> tuple[int | None, int | None]:
        if not local_id or not visit_id:
            return None, None
        if pred_gl is not None and pred_gv is not None:
            if pred_gl > pred_gv:
                return local_id, visit_id
            if pred_gv > pred_gl:
                return visit_id, local_id
        # Empate o sin predicción → FIFA ranking (menor = mejor); local gana si igual
        lr = (eq_data.get(local_id) or {}).get("fifa_ranking") or 9999
        vr = (eq_data.get(visit_id) or {}).get("fifa_ranking") or 9999
        return (local_id, visit_id) if lr <= vr else (visit_id, local_id)

    def _eq_obj(eid: int | None) -> dict | None:
        if not eid:
            return None
        e = eq_data.get(eid)
        if not e:
            return None
        return {"equipo_id": eid, "nombre": e.get("nombre"),
                "nombre_es": e.get("nombre_es"), "logo_url": e.get("logo_url"),
                "fifa_ranking": e.get("fifa_ranking")}

    result: list[dict] = []
    winners: dict[int, int | None] = {}  # num → winner_id
    losers:  dict[int, int | None] = {}  # num → loser_id

    # ── R32 ──────────────────────────────────────────────────────────────
    for m in r32_bracket:
        num = m["num"]
        local_obj  = m.get("local")
        visit_obj  = m.get("visitante")
        local_id   = (local_obj  or {}).get("equipo_id") if local_obj  else None
        visit_id   = (visit_obj  or {}).get("equipo_id") if visit_obj  else None

        pid = num2pid.get(num)
        ap  = ko_aps.get(pid, {}) if pid else {}
        pred_gl  = ap.get("pred_local")
        pred_gv  = ap.get("pred_visitante")
        pred_pen = ap.get("pred_penales")

        # Si ya está finalizado, usar ganador/perdedor real
        real = real_results.get(pid, {}) if pid else {}
        if real.get("winner_id") is not None:
            winner_id, loser_id = real["winner_id"], real["loser_id"]
        else:
            winner_id, loser_id = _winner_loser_pred(local_id, visit_id, pred_gl, pred_gv)
        winners[num] = winner_id
        losers[num]  = loser_id

        result.append({
            "num": num, "tipo": "ronda32",
            "partido_id": pid,
            "local_id": local_id, "visit_id": visit_id,
            "local": local_obj, "visitante": visit_obj,
            "pred_gl": pred_gl, "pred_gv": pred_gv, "pred_penales": pred_pen,
                        "winner_id": winner_id, "loser_id": loser_id,
        })

    # ── R16 → Final (en orden topológico garantizado por la secuencia) ────
    KO_FASES_ORDER = ["ronda16", "cuartos", "semis", "tercer_puesto", "final"]
    for tipo in KO_FASES_ORDER:
        for num in TIPO_NUM_RANGE.get(tipo, []):
            feeders = KO_FEEDERS.get(num)
            if not feeders:
                continue
            (sl_tipo, sl_num), (sv_tipo, sv_num) = feeders
            local_id = (winners if sl_tipo == "W" else losers).get(sl_num)
            visit_id = (winners if sv_tipo == "W" else losers).get(sv_num)

            pid = num2pid.get(num)
            ap  = ko_aps.get(pid, {}) if pid else {}
            pred_gl  = ap.get("pred_local")
            pred_gv  = ap.get("pred_visitante")
            pred_pen = ap.get("pred_penales")

            # Si el partido ya está finalizado, usar ganador real
            real = real_results.get(pid, {}) if pid else {}
            if real.get("estado") == "finalizado":
                real_lid = real.get("local_id")
                real_vid = real.get("visit_id")
                if real_lid:
                    local_id = real_lid
                if real_vid:
                    visit_id = real_vid
                if real.get("winner_id") is not None:
                    winner_id, loser_id = real["winner_id"], real["loser_id"]
                else:
                    winner_id, loser_id = _winner_loser_pred(local_id, visit_id, pred_gl, pred_gv)
            else:
                winner_id, loser_id = _winner_loser_pred(local_id, visit_id, pred_gl, pred_gv)

            winners[num] = winner_id
            losers[num]  = loser_id

            result.append({
                "num": num, "tipo": tipo,
                "partido_id": pid,
                "local_id": local_id, "visit_id": visit_id,
                "local": _eq_obj(local_id), "visitante": _eq_obj(visit_id),
                "pred_gl": pred_gl, "pred_gv": pred_gv, "pred_penales": pred_pen,
                "winner_id": winner_id, "loser_id": loser_id,
            })

    return result
