"""
Modulo: modelo_combustion.py
------------------------------
Define la clase ModeloCombustion, que encapsula toda la interaccion con
Cantera. En cada paso de tiempo, resuelve el equilibrio quimico de la
mezcla combustible/aire (condicion HP: entalpia y presion constantes),
usando como aire de entrada la composicion actual entregada por
SimulacionCombustion (que sera la del ambiente para artefactos tipo A/B,
o la del exterior para tipo C).

Se utiliza equilibrio termodinamico (no cinetica quimica detallada) para
mantener la complejidad del modelo acotada al alcance del proyecto: al
disminuir la disponibilidad de O2 en el aire de entrada, el equilibrio
predice una generacion creciente de CO, lo cual reproduce el fenomeno
fisico de interes (combustion incompleta por deficit de aire).
"""

import cantera as ct


class ModeloCombustion:
    """Resuelve el equilibrio quimico de la combustion combustible/aire."""

    # Especies necesarias en la fase de Cantera: combustibles (GLP y GN)
    # mas las especies de interes en los productos de combustion.
    ESPECIES_NASA_REQUERIDAS = [
        "C4H10,n-butane", "C3H8", "CH4", "O2", "N2", "CO", "CO2", "H2O",
    ]

    ESPECIES_BALANCE = ["CO", "CO2", "O2", "H2O", "N2"]

    TEMPERATURA_ENTRADA_K = 293.15  # 20 C, temperatura de reactivos al ingresar al artefacto

    def __init__(self, presion_Pa=101325.0):
        self.presion_Pa = presion_Pa
        self._gas = self._crear_fase()

    def _crear_fase(self):
        todas_las_especies = ct.Species.list_from_file("nasa_gas.yaml")
        seleccionadas = [sp for sp in todas_las_especies if sp.name in self.ESPECIES_NASA_REQUERIDAS]
        return ct.Solution(thermo="ideal-gas", species=seleccionadas)

    def calcular_equilibrio(self, combustible, composicion_aire, ndot_gas, ndot_aire):
        """
        Resuelve el equilibrio quimico de la mezcla combustible/aire.

        Parametros
        ----------
        combustible : Combustible
            Objeto con la composicion molar y masa molar del gas.
        composicion_aire : dict
            Fracciones molares del aire de entrada
            {"CO":.., "CO2":.., "O2":.., "H2O":.., "N2":..} (deben sumar 1).
        ndot_gas : float
            Caudal molar de combustible [mol/s].
        ndot_aire : float
            Caudal molar de aire de combustion [mol/s].

        Retorna
        -------
        dict con:
            'ndot_salida' : dict {especie: caudal molar de salida [mol/s]}
                             para CO, CO2, O2, H2O, N2.
            'temperatura_llama' : temperatura adiabatica de equilibrio [K].
        """
        gas = self._gas

        # --- Caudales masicos (la masa SI se conserva exactamente en la reaccion,
        #     a diferencia del numero total de moles) ---
        mdot_gas = ndot_gas * combustible.masa_molar_kg_mol  # kg/s

        masa_molar_aire_actual = sum(
            composicion_aire[especie] * gas.molecular_weights[gas.species_index(especie)] / 1000.0
            for especie in composicion_aire
        )  # kg/mol
        mdot_aire = ndot_aire * masa_molar_aire_actual  # kg/s
        mdot_total = mdot_gas + mdot_aire

        # --- Composicion de entrada combinada (combustible + aire), en fraccion molar ---
        n_total = ndot_gas + ndot_aire
        entrada = {}
        for especie, frac in combustible.composicion_molar.items():
            entrada[especie] = entrada.get(especie, 0.0) + frac * ndot_gas / n_total
        for especie, frac in composicion_aire.items():
            entrada[especie] = entrada.get(especie, 0.0) + frac * ndot_aire / n_total

        # --- Equilibrio quimico a entalpia y presion constantes ---
        gas.TPX = self.TEMPERATURA_ENTRADA_K, self.presion_Pa, entrada
        gas.equilibrate("HP")

        # --- Caudales molares de salida, a partir de fracciones masicas
        #     (la masa total SI se conserva; el numero de moles, no necesariamente) ---
        ndot_salida = {}
        for especie in self.ESPECIES_BALANCE:
            fraccion_masica = gas[especie].Y[0]
            mdot_especie = mdot_total * fraccion_masica
            masa_molar_especie = gas.molecular_weights[gas.species_index(especie)] / 1000.0  # kg/mol
            ndot_salida[especie] = mdot_especie / masa_molar_especie  # mol/s

        return {"ndot_salida": ndot_salida, "temperatura_llama": gas.T}
