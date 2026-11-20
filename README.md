# Simulador de combustion y generacion de CO en ambientes cerrados

Simulacion en Python 3.13 de la combustion de un artefacto a gas (GLP o GN)
dentro de una habitacion, para estimar la evolucion en el tiempo de la
concentracion de CO (ppm) y O2 (%) en el ambiente.

La interfaz principal es una **aplicacion web con Streamlit** (`app.py`).
La interfaz de escritorio original con tkinter (`main.py` / `gui.py`) se
conserva, pero no es necesaria para la version web.

## Ejecucion local

```bash
python -m venv venv
source venv/bin/activate      # En Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Se abre en el navegador (normalmente en http://localhost:8501). En la
barra lateral se configuran tipo de gas, dimensiones de la habitacion,
ventilacion, tipo de artefacto y potencia; al presionar **Simular** se
muestran las metricas y los graficos de CO y O2 vs. tiempo.

> Si `pip install cantera` fallara, se puede instalar con conda:
> `conda install -c cantera cantera`.

## Publicacion en Streamlit Community Cloud (gratis)

1. Crear un repositorio **publico** en GitHub y subir los archivos del
   proyecto (`app.py`, los modulos `.py`, `requirements.txt`).
2. Entrar en https://share.streamlit.io e iniciar sesion con GitHub.
3. Elegir **Create app** -> seleccionar el repositorio, la rama y el
   archivo principal `app.py`.
4. Presionar **Deploy**. La plataforma instala las dependencias de
   `requirements.txt` y entrega una URL publica.

Las actualizaciones posteriores se publican automaticamente con cada
`git push`. En el plan gratuito la app puede "dormirse" tras un periodo
de inactividad y tardar unos segundos en despertar. Los limites del plan
gratuito pueden cambiar: conviene confirmarlos en la documentacion de
Streamlit.

## Estructura del proyecto

```
simulador_combustion/
├── app.py                  # Interfaz web (Streamlit) - sin logica de calculo
├── main.py / gui.py        # Interfaz de escritorio (tkinter), opcional
├── combustible.py          # Clase Combustible (GLP / GN)
├── artefacto.py            # Clase Artefacto (tipo A / B / C)
├── habitacion.py           # Clase Habitacion (geometria y composicion)
├── ventilacion.py          # Clase Ventilacion (placeholder UNIT 1005)
├── modelo_combustion.py    # Clase ModeloCombustion (equilibrio via Cantera)
├── simulacion.py           # Clase SimulacionCombustion (orquestador)
├── requirements.txt
└── README.md
```

## Notas de modelado

- La composicion del GLP se modela como 60% n-butano / 40% propano
  (fraccion molar). Como el mecanismo GRI-Mech 3.0 de Cantera no
  incluye butano, se arma una fase termodinamica "a medida" a partir
  de la base de datos `nasa_gas.yaml` que distribuye Cantera.
- El poder calorifico de cada combustible se calcula de forma
  autoconsistente a partir de esos mismos datos termodinamicos.
- Se resuelve equilibrio quimico (no cinetica detallada), en condicion
  de entalpia y presion constantes (HP).
- Artefactos tipo A y B: vuelcan la totalidad de los gases de combustion
  al ambiente y toman su aire de combustion del ambiente
  (retroalimentacion: al caer el O2 disponible, aumenta la generacion
  de CO).
- Artefacto tipo C: toma aire del exterior y evacua al exterior; se
  modela una fuga del 0.01% de los gases de combustion hacia el ambiente.
- La ventilacion es un *placeholder* (1 m3/h fijo) pensado para ser
  reemplazado por el calculo real segun UNIT 1005 mediante una subclase
  de `Ventilacion`, sin modificar el resto del codigo.
- Parametros editables en el codigo: `SimulacionCombustion.TIEMPO_TOTAL_S`
  y `SimulacionCombustion.DELTA_T_S` (en `simulacion.py`).
- En la version web, el modelo de Cantera se crea una sola vez
  (`st.cache_resource`) y los resultados de cada combinacion de
  parametros se cachean (`st.cache_data`), por lo que repetir una
  simulacion ya calculada es inmediato.
