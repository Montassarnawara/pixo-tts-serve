"""
viseme_mapping.py — Table de correspondance entre les formes de bouche Rhubarb Lip Sync
(A, B, C... X) et nos ids de visème habituels (0-21, voir visemes.md à la racine du dépôt).

Rhubarb utilise 9 formes standard (charte Hanna-Barbera / Preston Blair) :
A : bouche fermée (M, B, P)
B : bouche légèrement ouverte, dents serrées (la plupart des consonnes : K, S, T...)
C : bouche ouverte (voyelles EH, AE)
D : bouche grande ouverte (voyelle AA)
E : bouche arrondie (voyelles AO, ER)
F : lèvres pincées (U, W, OO)
G : dents du haut sur la lèvre du bas (F, V)
H : langue relevée (L)
X : position de repos (silence)
"""

from __future__ import annotations

RHUBARB_TO_VISEME_ID: dict[str, int] = {
    "X": 0,   # silence
    "C": 4,   # EH, AE
    "D": 2,   # AA (voyelle grande ouverte)
    "E": 3,   # AO, ER
    "F": 7,   # U, W, OO
    "G": 18,  # F, V
    "H": 14,  # L
    "B": 19,  # la plupart des consonnes (K, S, T...)
    "A": 21,  # M, B, P (bouche fermée)
}


def rhubarb_shape_to_viseme_id(shape: str) -> int:
    """Id de visème pour une forme Rhubarb donnée. Forme inconnue -> silence (0), jamais d'erreur :
    une entrée imprévue d'un outil externe ne doit pas faire planter la génération.
    """
    return RHUBARB_TO_VISEME_ID.get(shape, 0)
