"""
Modulo: app.py
----------------
Interfaz web (Streamlit) del simulador. Reemplaza a la capa tkinter
(gui.py / main.py) para poder publicar el proyecto en la web.

Esta capa se limita a: recibir los datos de entrada, validarlos de forma
simple, ejecutar la simulacion y mostrar los graficos. Toda la logica de
calculo vive en las clases de dominio (combustible, artefacto,
habitacion, ventilacion, modelo_combustion, simulacion), que no fueron
modificadas.

Ejecucion local:
    streamlit run app.py
"""

import streamlit as st
from matplotlib.figure import Figure

from combustible import Combustible
from artefacto import Artefacto
from habitacion import Habitacion
from ventilacion import Ventilacion
from modelo_combustion import ModeloCombustion
from simulacion import SimulacionCombustion

# Valores iniciales por defecto, segun definicion del proyecto
GAS_POR_DEFECTO = "GLP"
TIPO_ARTEFACTO_POR_DEFECTO = "A"
POTENCIA_POR_DEFECTO = 4.2
ANCHO_POR_DEFECTO = 2.0
PROFUNDIDAD_POR_DEFECTO = 4.0
ALTO_POR_DEFECTO = 3.0


@st.cache_resource
def obtener_modelo_combustion():
    """Crea la fase de Cantera una unica vez y la reutiliza entre simulaciones."""
    return ModeloCombustion()


@st.cache_data(show_spinner=False)
def ejecutar_simulacion(gas, alto, ancho, profundidad, tiene_ventilacion, tipo, potencia_kW):
    """
    Ejecuta la simulacion completa (2 h, dt = 1 s). Se cachea por
    combinacion de parametros: repetir una simulacion ya calculada es inmediato.
    """
    combustible = Combustible(gas)
    artefacto = Artefacto(tipo, potencia_kW, combustible)
    habitacion = Habitacion(alto_m=alto, ancho_m=ancho, profundidad_m=profundidad)
    ventilacion = Ventilacion(tiene_ventilacion=tiene_ventilacion)

    simulacion = SimulacionCombustion(habitacion, artefacto, ventilacion, obtener_modelo_combustion())
    simulacion.ejecutar()
    tiempo_min, co_ppm, o2_pct = simulacion.obtener_resultados()
    return tiempo_min, co_ppm, o2_pct, habitacion.volumen


def construir_figura(tiempo_min, co_ppm, o2_pct):
    figura = Figure(figsize=(8, 7))
    ax_co = figura.add_subplot(211)
    ax_o2 = figura.add_subplot(212)

    ax_co.plot(tiempo_min, co_ppm, color="firebrick", linewidth=1.5)
    ax_co.set_title("Concentracion de CO en la habitacion")
    ax_co.set_xlabel("Tiempo [min]")
    ax_co.set_ylabel("CO [ppm]")
    ax_co.grid(True, alpha=0.3)

    ax_o2.plot(tiempo_min, o2_pct, color="steelblue", linewidth=1.5)
    ax_o2.set_title("Concentracion de O2 en la habitacion")
    ax_o2.set_xlabel("Tiempo [min]")
    ax_o2.set_ylabel("O2 [%]")
    ax_o2.grid(True, alpha=0.3)

    figura.tight_layout()
    return figura


def main():
    st.set_page_config(page_title="Simulador de combustion y CO", layout="wide")
    st.title("Simulador de combustion y generacion de CO en ambientes cerrados")
    st.caption(
        "Evolucion de la concentracion de CO (ppm) y O2 (%) durante 2 horas de "
        "funcionamiento de un artefacto a gas dentro de una habitacion."
    )

    # ------------------------------------------------------------------
    # Entradas (barra lateral)
    # ------------------------------------------------------------------
    with st.sidebar:
        st.header("Datos de entrada")

        gas = st.selectbox("Tipo de gas", ["GLP", "GN"], index=["GLP", "GN"].index(GAS_POR_DEFECTO))

        st.subheader("Habitacion (m)")
        alto = st.number_input("Altura", min_value=0.1, value=ALTO_POR_DEFECTO, step=0.1, format="%.2f")
        ancho = st.number_input("Ancho", min_value=0.1, value=ANCHO_POR_DEFECTO, step=0.1, format="%.2f")
        profundidad = st.number_input(
            "Profundidad", min_value=0.1, value=PROFUNDIDAD_POR_DEFECTO, step=0.1, format="%.2f"
        )

        ventilacion_txt = st.radio("Ventilacion", ["No", "Si"], index=0, horizontal=True)

        st.subheader("Artefacto")
        tipos = list(Artefacto.POTENCIAS_TIPICAS_KW.keys())
        tipo = st.selectbox("Tipo de artefacto", tipos, index=tipos.index(TIPO_ARTEFACTO_POR_DEFECTO))

        # La lista de potencias depende del tipo seleccionado
        potencias = Artefacto.POTENCIAS_TIPICAS_KW[tipo]
        indice_potencia = potencias.index(POTENCIA_POR_DEFECTO) if POTENCIA_POR_DEFECTO in potencias else 0
        potencia = st.selectbox("Potencia (kW)", potencias, index=indice_potencia)

        simular = st.button("Simular", type="primary", use_container_width=True)

    # ------------------------------------------------------------------
    # Simulacion y resultados
    # ------------------------------------------------------------------
    if not simular:
        st.info("Configure los datos en la barra lateral y presione **Simular**.")
        return

    try:
        with st.spinner("Simulando (puede tardar unos segundos)..."):
            tiempo_min, co_ppm, o2_pct, volumen = ejecutar_simulacion(
                gas, float(alto), float(ancho), float(profundidad),
                ventilacion_txt == "Si", tipo, float(potencia),
            )
    except Exception as exc:  # noqa: BLE001 - se informa cualquier error al usuario
        st.error(f"Ocurrio un error durante la simulacion: {exc}")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Volumen de la habitacion", f"{volumen:.1f} m3")
    col2.metric("CO maximo", f"{co_ppm.max():.1f} ppm")
    col3.metric("CO final (t = 2 h)", f"{co_ppm[-1]:.1f} ppm")
    col4.metric("O2 final (t = 2 h)", f"{o2_pct[-1]:.2f} %")

    st.pyplot(construir_figura(tiempo_min, co_ppm, o2_pct))


if __name__ == "__main__":
    main()
