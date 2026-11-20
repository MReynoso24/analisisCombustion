"""
Modulo: simulacion.py
-----------------------
Define la clase SimulacionCombustion, orquestador principal del proyecto.
En cada paso de tiempo:
    1. Obtiene la composicion de aire de entrada al artefacto (la del
       ambiente para tipo A/B, o la del exterior para tipo C).
    2. Resuelve el equilibrio de combustion (ModeloCombustion / Cantera).
    3. Calcula la generacion neta de cada especie sobre la habitacion:
        - Aporte de los gases de combustion (segun la tasa de fuga del
          artefacto: 100% para A/B, 0.01% para C).
        - Extraccion de aire ambiente tomado para la combustion (solo
          para artefactos que toman aire del ambiente, A/B).
    4. Aplica la dilucion/reposicion por ventilacion (intercambio
       bidireccional con el aire exterior).
    5. Integra el balance de masa (Euler explicito, paso de tiempo fijo)
       y actualiza la composicion de la habitacion.

Parametros de simulacion (tiempo total y paso de tiempo) definidos como
constantes de clase, editables aqui si se desea modificar su valor.
"""

import numpy as np


class SimulacionCombustion:
    """Orquesta la simulacion temporal del balance de masa en la habitacion."""

    R = 8.314462618  # J/(mol K)

    # --- Parametros de simulacion (editables) ---
    TIEMPO_TOTAL_S = 2 * 60 * 60  # 2 horas
    DELTA_T_S = 1.0                # paso de tiempo: 1 segundo

    def __init__(self, habitacion, artefacto, ventilacion, modelo_combustion,
                 tiempo_total_s=None, delta_t_s=None):
        self.habitacion = habitacion
        self.artefacto = artefacto
        self.ventilacion = ventilacion
        self.modelo_combustion = modelo_combustion

        self.tiempo_total_s = tiempo_total_s if tiempo_total_s is not None else self.TIEMPO_TOTAL_S
        self.delta_t_s = delta_t_s if delta_t_s is not None else self.DELTA_T_S

        self.caudal_ventilacion_molar = self._caudal_ventilacion_a_molar()

        n_pasos = int(round(self.tiempo_total_s / self.delta_t_s)) + 1
        self.tiempos_s = np.linspace(0.0, self.tiempo_total_s, n_pasos)
        self.co_ppm = np.zeros(n_pasos)
        self.o2_pct = np.zeros(n_pasos)
        self.temperatura_llama_K = np.zeros(n_pasos)

    def _caudal_ventilacion_a_molar(self):
        """Convierte el caudal de ventilacion [m3/h] a caudal molar [mol/s] (gas ideal)."""
        Q_m3_h = self.ventilacion.calcular_caudal()
        Q_m3_s = Q_m3_h / 3600.0
        T = self.habitacion.temperatura_K
        P = self.habitacion.presion_Pa
        return P * Q_m3_s / (self.R * T)

    def _paso_temporal(self):
        """Ejecuta un ciclo de calculo de un paso temporal y actualiza la habitacion."""
        habitacion = self.habitacion
        artefacto = self.artefacto
        combustible = artefacto.combustible

        if artefacto.toma_aire_ambiente():
            composicion_aire_entrada = habitacion.composicion_actual
        else:
            composicion_aire_entrada = habitacion.COMPOSICION_AIRE_EXTERIOR

        resultado = self.modelo_combustion.calcular_equilibrio(
            combustible=combustible,
            composicion_aire=composicion_aire_entrada,
            ndot_gas=artefacto.caudal_molar_gas,
            ndot_aire=artefacto.caudal_molar_aire,
        )
        ndot_salida = resultado["ndot_salida"]
        tasa_fuga = artefacto.tasa_fuga()
        toma_aire_ambiente = artefacto.toma_aire_ambiente()

        # --- Generacion neta por combustion [mol/s] para cada especie ---
        generacion = {}
        for especie in habitacion.ESPECIES:
            aporte = tasa_fuga * ndot_salida[especie]
            extraccion = 0.0
            if toma_aire_ambiente:
                extraccion = artefacto.caudal_molar_aire * habitacion.composicion_actual[especie]
            generacion[especie] = aporte - extraccion

        # --- Termino de ventilacion (intercambio bidireccional con el exterior) ---
        Qn_vent = self.caudal_ventilacion_molar
        N_total = habitacion.moles_totales
        dt = self.delta_t_s

        nueva_composicion = {}
        for especie in habitacion.ESPECIES:
            X_actual = habitacion.composicion_actual[especie]
            X_exterior = habitacion.COMPOSICION_AIRE_EXTERIOR[especie]
            dX_dt = generacion[especie] / N_total - Qn_vent * (X_actual - X_exterior) / N_total
            nueva_composicion[especie] = X_actual + dX_dt * dt

        habitacion.actualizar_composicion(nueva_composicion)
        return resultado["temperatura_llama"]

    def ejecutar(self):
        """Ejecuta la simulacion completa a lo largo de todo tiempo_total_s."""
        self.co_ppm[0] = self.habitacion.composicion_actual["CO"] * 1e6
        self.o2_pct[0] = self.habitacion.composicion_actual["O2"] * 100.0
        self.temperatura_llama_K[0] = np.nan

        for i in range(1, len(self.tiempos_s)):
            T_llama = self._paso_temporal()
            self.co_ppm[i] = self.habitacion.composicion_actual["CO"] * 1e6
            self.o2_pct[i] = self.habitacion.composicion_actual["O2"] * 100.0
            self.temperatura_llama_K[i] = T_llama

    def obtener_resultados(self):
        """
        Retorna los arrays de resultados listos para graficar:
        (tiempo en minutos, concentracion de CO en ppm, concentracion de O2 en %).
        """
        tiempo_min = self.tiempos_s / 60.0
        return tiempo_min, self.co_ppm, self.o2_pct
