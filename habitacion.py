"""
Modulo: habitacion.py
----------------------
Define la clase Habitacion, que representa el recinto (bien mezclado,
temperatura y presion constantes) donde ocurre la combustion, y que
trackea la composicion molar de las especies de interes en el balance
de masa: CO, CO2, O2, H2O y N2.
"""


class Habitacion:
    """Representa el recinto donde ocurre la combustion."""

    R = 8.314462618  # J/(mol K), constante universal de los gases

    ESPECIES = ["CO", "CO2", "O2", "H2O", "N2"]

    # Composicion de aire exterior / atmosferico estandar (fracciones molares),
    # usada como condicion inicial de la habitacion y como composicion del
    # aire de combustion para el artefacto tipo C y del aire de ventilacion.
    COMPOSICION_AIRE_EXTERIOR = {
        "CO": 0.0,
        "CO2": 0.0004,   # ~400 ppm, CO2 atmosferico de referencia
        "O2": 0.2095,
        "H2O": 0.0,
        "N2": 0.7901,
    }

    def __init__(self, alto_m, ancho_m, profundidad_m, temperatura_C=20.0, presion_Pa=101325.0):
        if alto_m <= 0 or ancho_m <= 0 or profundidad_m <= 0:
            raise ValueError("Las dimensiones de la habitacion deben ser mayores a cero.")

        self.alto = alto_m
        self.ancho = ancho_m
        self.profundidad = profundidad_m
        self.temperatura_K = temperatura_C + 273.15
        self.presion_Pa = presion_Pa

        self.volumen = self._calcular_volumen()
        self.moles_totales = self._calcular_moles_totales()

        # Condicion inicial: aire exterior estandar (CO = 0)
        self.composicion_actual = dict(self.COMPOSICION_AIRE_EXTERIOR)

    def _calcular_volumen(self):
        """Volumen de la habitacion [m3], a partir de las tres dimensiones."""
        return self.alto * self.ancho * self.profundidad

    def _calcular_moles_totales(self):
        """
        Moles totales de gas contenidos en la habitacion [mol] (ley de
        gases ideales). Se mantiene constante durante toda la simulacion,
        ya que se asumen T y P constantes en el ambiente.
        """
        return self.presion_Pa * self.volumen / (self.R * self.temperatura_K)

    def actualizar_composicion(self, nueva_composicion):
        """
        Reemplaza la composicion actual de la habitacion por la nueva,
        normalizando para que las fracciones molares sumen exactamente 1
        (corrige la deriva numerica acumulada por la integracion explicita
        a lo largo de miles de pasos de tiempo).
        """
        composicion_no_negativa = {esp: max(val, 0.0) for esp, val in nueva_composicion.items()}
        suma = sum(composicion_no_negativa.values())
        self.composicion_actual = {esp: val / suma for esp, val in composicion_no_negativa.items()}
