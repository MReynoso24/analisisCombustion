"""
Modulo: ventilacion.py
------------------------
Define la clase Ventilacion, que representa la condicion de ventilacion
de la habitacion. Esta pensada como clase base extensible: el unico punto
de acoplamiento con el resto del modelo es el metodo 'calcular_caudal()',
por lo que en el futuro puede reemplazarse (por ejemplo, mediante una
subclase que implemente el calculo real segun la norma UNIT 1005) sin
modificar ninguna otra clase del proyecto.
"""


class Ventilacion:
    """Representa la condicion de ventilacion de la habitacion."""

    def __init__(self, tiene_ventilacion):
        self.tiene_ventilacion = tiene_ventilacion

    def calcular_caudal(self):
        """
        Caudal volumetrico de aire de ventilacion [m3/h].

        Implementacion de esta primera version del proyecto (placeholder):
        devuelve un valor fijo de 1 m3/h si la habitacion cuenta con
        ventilacion, o 0 si no cuenta con ventilacion.

        A reemplazar en una iteracion futura por el calculo real segun la
        norma UNIT 1005 (que depende de la superficie de ventilacion, el
        tipo de local, el tipo de artefacto, etc.) mediante una subclase
        que sobrescriba este metodo, por ejemplo VentilacionUNIT1005.
        """
        return 1.0 if self.tiene_ventilacion else 0.0


class VentilacionUNIT1005(Ventilacion):
    """
    Placeholder para la futura implementacion del calculo de ventilacion
    segun la norma UNIT 1005. La formula real depende de multiples
    factores (superficie de ventilacion, tipo de local, tipo de
    artefacto, etc.) que quedan pendientes de definicion.
    """

    def calcular_caudal(self):
        raise NotImplementedError(
            "El calculo de ventilacion segun UNIT 1005 aun no fue implementado."
        )
