"""
Modulo: artefacto.py
---------------------
Define la clase Artefacto, que representa el equipo de combustion
(tipo A, B o C) y calcula los caudales molares de gas y de aire de
combustion de diseno (fijos durante toda la simulacion), a partir de
la potencia nominal seleccionada y del exceso de aire inicial.

Definicion de tipos (segun norma de referencia del proyecto):
    Tipo A: sin conducto de evacuacion; vuelca el 100% de los gases de
            combustion al ambiente. Toma aire de combustion del ambiente.
    Tipo B: con conducto de evacuacion; vuelca el 100% de los gases de
            combustion al ambiente (mismo tratamiento que el tipo A en
            este modelo). Toma aire de combustion del ambiente.
    Tipo C (estanco): toma aire de combustion del exterior y evacua los
            gases de combustion al exterior. Se modela una pequena fuga
            de gases de combustion hacia el ambiente (0.01%).
"""

from combustible import Combustible


class Artefacto:
    """Representa el artefacto de combustion y sus caudales de diseno."""

    POTENCIAS_TIPICAS_KW = {
        "A": [1.4, 2.8, 4.2, 7, 12, 16, 20],
        "B": [7, 12, 16, 20, 26],
        "C": [20, 26, 28, 32],
    }

    EXCESO_AIRE_INICIAL = 0.10   # 10% de exceso de aire, fijado en el instante de diseno (t=0)
    TASA_FUGA_TIPO_C = 0.0001    # 0.01% de los humos de combustion hacia el ambiente (solo tipo C)

    # Composicion de aire estandar de referencia, usada UNICAMENTE para
    # dimensionar (una sola vez) el caudal de aire de diseno del artefacto.
    X_O2_AIRE_ESTANDAR = 0.21

    def __init__(self, tipo, potencia_kW, combustible: Combustible):
        tipo = tipo.upper()
        if tipo not in self.POTENCIAS_TIPICAS_KW:
            raise ValueError("Tipo de artefacto invalido. Debe ser 'A', 'B' o 'C'.")
        if potencia_kW not in self.POTENCIAS_TIPICAS_KW[tipo]:
            raise ValueError(
                f"Potencia {potencia_kW} kW no es un valor tipico valido para el tipo {tipo}. "
                f"Valores validos: {self.POTENCIAS_TIPICAS_KW[tipo]} kW"
            )

        self.tipo = tipo
        self.potencia_kW = potencia_kW
        self.combustible = combustible

        # Caudales de diseno, FIJOS durante toda la simulacion:
        self.caudal_molar_gas = combustible.caudal_molar(potencia_kW)   # mol/s
        self.caudal_molar_aire = self._calcular_caudal_aire_diseno()    # mol/s

    def _calcular_caudal_aire_diseno(self):
        """
        Caudal molar de aire de combustion [mol/s], calculado UNA SOLA VEZ
        con la composicion de aire estandar (t=0), de forma que se logre el
        exceso de aire inicial definido (10%). Este caudal permanece fijo
        durante toda la simulacion; lo que varia en el tiempo (para tipo A
        y B) es la composicion del aire realmente disponible en el ambiente,
        lo cual modifica la relacion de equivalencia EFECTIVA de la mezcla.
        """
        n_o2_estequiometrico = self.combustible.o2_estequiometrico_por_mol_fuel
        ndot_o2_estequiometrico = self.caudal_molar_gas * n_o2_estequiometrico
        ndot_aire_estequiometrico = ndot_o2_estequiometrico / self.X_O2_AIRE_ESTANDAR
        return (1.0 + self.EXCESO_AIRE_INICIAL) * ndot_aire_estequiometrico

    def toma_aire_ambiente(self):
        """True para tipo A y B (combustion abierta a la habitacion); False para tipo C (estanco)."""
        return self.tipo in ("A", "B")

    def tasa_fuga(self):
        """
        Fraccion de los gases de combustion que efectivamente se incorpora
        al balance de masa de la habitacion.
        Tipo A y B: 1.0 (vuelcan la totalidad de los gases de combustion).
        Tipo C: 0.0001 (0.01% de fuga hacia el ambiente).
        """
        if self.tipo == "C":
            return self.TASA_FUGA_TIPO_C
        return 1.0
