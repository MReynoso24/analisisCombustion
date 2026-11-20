"""
Modulo: combustible.py
----------------------
Define la clase Combustible, que representa el gas seleccionado por el
usuario (GLP o GN) y encapsula su composicion molar y sus propiedades
de combustion (masa molar, poder calorifico inferior, oxigeno
estequiometrico requerido).

Nota sobre la fuente de datos termodinamicos:
GRI-Mech 3.0 (el mecanismo "estandar" de Cantera para combustion de gas
natural) NO incluye butano (C4H10) entre sus especies. Por eso, en lugar
de usar 'gri30.yaml', se arma una fase Cantera "a medida" ('ideal-gas')
importando unicamente las especies necesarias desde la base de datos
termodinamica NASA que Cantera distribuye ('nasa_gas.yaml'), la cual si
incluye n-butano. Esto permite representar fielmente la mezcla GLP
(60% butano / 40% propano) indicada en la definicion del proyecto.

El poder calorifico inferior (PCI o LHV) de cada combustible se calcula
de forma autoconsistente a partir de esos mismos datos termodinamicos
(diferencia de entalpia de formacion entre reactivos y productos de
combustion completa a 298.15 K), en lugar de tomar valores bibliograficos
sueltos que podrian ser inconsistentes con el resto del modelo de
combustion usado en ModeloCombustion.
"""

import cantera as ct


class Combustible:
    """Representa el combustible (GLP o GN) y sus propiedades de combustion."""

    # Composicion molar de cada combustible, expresada con los nombres de
    # especie tal como figuran en la base de datos 'nasa_gas.yaml' de Cantera.
    COMPOSICIONES = {
        "GLP": {
            "especies": {"C4H10,n-butane": 0.6, "C3H8": 0.4},
            "atomos_C_promedio": 0.6 * 4 + 0.4 * 3,   # 3.6 atomos de C por mol de mezcla
            "atomos_H_promedio": 0.6 * 10 + 0.4 * 8,  # 9.2 atomos de H por mol de mezcla
        },
        "GN": {
            "especies": {"CH4": 1.0},
            "atomos_C_promedio": 1.0,
            "atomos_H_promedio": 4.0,
        },
    }

    # Especies que deben existir en la fase de referencia de Cantera para
    # poder representar ambos combustibles y sus productos de combustion.
    ESPECIES_NASA_REQUERIDAS = [
        "C4H10,n-butane", "C3H8", "CH4", "O2", "N2", "CO", "CO2", "H2O",
    ]

    TEMPERATURA_REFERENCIA_K = 298.15  # 25 C, condicion estandar para el calculo del PCI
    PRESION_REFERENCIA_Pa = ct.one_atm

    def __init__(self, nombre):
        nombre = nombre.upper()
        if nombre not in self.COMPOSICIONES:
            raise ValueError(f"Combustible '{nombre}' no soportado. Use 'GLP' o 'GN'.")

        self.nombre = nombre
        datos = self.COMPOSICIONES[nombre]
        self.composicion_molar = dict(datos["especies"])
        self._atomos_C = datos["atomos_C_promedio"]
        self._atomos_H = datos["atomos_H_promedio"]

        gas_ref = self._crear_fase_referencia()

        # Masa molar de la mezcla combustible [kg/mol]
        self.masa_molar_kg_mol = self._calcular_masa_molar(gas_ref)

        # Oxigeno estequiometrico requerido por mol de mezcla combustible
        # (a partir de CxHy + (x + y/4) O2 -> x CO2 + y/2 H2O)
        self.o2_estequiometrico_por_mol_fuel = self._atomos_C + self._atomos_H / 4.0

        # Poder calorifico inferior [J/kg], calculado de forma autoconsistente
        self.pci_masico = self._calcular_pci_masico(gas_ref)

    # ------------------------------------------------------------------
    # Construccion de la fase termodinamica de referencia
    # ------------------------------------------------------------------
    def _crear_fase_referencia(self):
        todas_las_especies = ct.Species.list_from_file("nasa_gas.yaml")
        seleccionadas = [sp for sp in todas_las_especies if sp.name in self.ESPECIES_NASA_REQUERIDAS]
        if len(seleccionadas) != len(self.ESPECIES_NASA_REQUERIDAS):
            faltantes = set(self.ESPECIES_NASA_REQUERIDAS) - {sp.name for sp in seleccionadas}
            raise RuntimeError(f"No se encontraron en nasa_gas.yaml las especies: {faltantes}")
        return ct.Solution(thermo="ideal-gas", species=seleccionadas)

    def _calcular_masa_molar(self, gas_ref):
        """Masa molar de la mezcla combustible [kg/mol]."""
        masa_molar_kg_kmol = sum(
            frac * gas_ref.molecular_weights[gas_ref.species_index(especie)]
            for especie, frac in self.composicion_molar.items()
        )
        return masa_molar_kg_kmol / 1000.0  # kg/kmol -> kg/mol

    def _calcular_pci_masico(self, gas_ref):
        """
        Calcula el poder calorifico inferior (LHV) en J/kg mediante la
        diferencia de entalpia entre reactivos (combustible + O2
        estequiometrico) y productos de combustion completa (CO2 + H2O
        gaseoso), ambos evaluados a 298.15 K y 1 atm (ley de Hess).
        """
        n_fuel = 1.0
        n_o2 = self.o2_estequiometrico_por_mol_fuel

        # --- Reactivos: combustible + O2 estequiometrico (sin N2) ---
        total_reactivos = n_fuel + n_o2
        x_reactivos = {
            especie: frac * n_fuel / total_reactivos
            for especie, frac in self.composicion_molar.items()
        }
        x_reactivos["O2"] = n_o2 / total_reactivos
        gas_ref.TPX = self.TEMPERATURA_REFERENCIA_K, self.PRESION_REFERENCIA_Pa, x_reactivos
        H_reactivos = gas_ref.enthalpy_mole * total_reactivos  # J (base: total_reactivos kmol)

        # --- Productos: combustion completa -> CO2 + H2O(g) ---
        n_co2 = self._atomos_C
        n_h2o = self._atomos_H / 2.0
        total_productos = n_co2 + n_h2o
        x_productos = {"CO2": n_co2 / total_productos, "H2O": n_h2o / total_productos}
        gas_ref.TPX = self.TEMPERATURA_REFERENCIA_K, self.PRESION_REFERENCIA_Pa, x_productos
        H_productos = gas_ref.enthalpy_mole * total_productos

        pci_molar = (H_reactivos - H_productos) / n_fuel  # J/kmol de combustible
        pci_masico = pci_molar / (self.masa_molar_kg_mol * 1000.0)  # J/kg
        return pci_masico

    # ------------------------------------------------------------------
    # Metodos publicos utilizados por Artefacto
    # ------------------------------------------------------------------
    def caudal_masico(self, potencia_kW):
        """Caudal masico de gas [kg/s] necesario para entregar la potencia nominal indicada."""
        potencia_W = potencia_kW * 1000.0
        return potencia_W / self.pci_masico

    def caudal_molar(self, potencia_kW):
        """Caudal molar de gas [mol/s] necesario para entregar la potencia nominal indicada."""
        return self.caudal_masico(potencia_kW) / self.masa_molar_kg_mol
