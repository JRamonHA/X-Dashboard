from pathlib import Path
import pandas as pd
import plotly.express as px
import faicons as fa
import io
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget


consumo = pd.read_csv(Path(__file__).parent / "consumo_kwh.csv", index_col="Fecha", parse_dates=True)

ICONS = {
    "download": fa.icon_svg("download"),
    "charge": fa.icon_svg("charging-station"),
    "plug": fa.icon_svg("plug-circle-bolt"),
    "energy": fa.icon_svg("bolt-lightning"),
}

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_selectize(
            "consumos",
            "Consumo:",
            {
                "A": "Total",
                "B": "Acumulado hasta las 12:00 (todos los días)",
                "C": "Acumulado hasta las 15:00 (primeros 15 días)",
                "D": "Acumulado (lunes a sábado)",
                "E": "Acumulado (solo domingo)",
            },
        ),
        ui.input_selectize(
            "puntos_carga",
            "Puntos de carga:",
            {
                "1": "Punto de carga 1", "2": "Punto de carga 2",
                "3": "Punto de carga 3", "4": "Punto de carga 4",
                "5": "Punto de carga 5", "6": "Punto de carga 6",
                "7": "Punto de carga 7", "8": "Punto de carga 8",
                "9": "Punto de carga 9", "10": "Punto de carga 10",
            },
            multiple=True,
            selected=["1"]
        ),
        ui.input_date_range(
            "daterange", 
            "Fecha:",
            start=consumo.index.min(), 
            end=consumo.index.max()
        ),
        open="desktop",
    ),
    # Tarjetas de valor
    ui.layout_columns(
        ui.value_box("Puntos de carga", ui.output_ui("charge_point"), showcase=ICONS["charge"]),
        ui.value_box("Consumo total", ui.output_ui("total_kwh"), showcase=ICONS["plug"]),
        ui.value_box("Promedio por punto", ui.output_ui("mean_kwh"), showcase=ICONS["energy"]),
        fill=False,
    ),
    # Primera fila: Gráfico de columnas y tabla de máximos/mínimos
    ui.layout_columns(
        ui.card(ui.card_header("Consumo por punto"), output_widget("consumo_columns"), full_screen=True),
        ui.card(ui.card_header("Máximos y mínimos"), ui.output_data_frame("max_min_table"), full_screen=True),
        col_widths=[6, 6],
    ),
    # Segunda fila: Tabla de datos y gráfico de líneas
    ui.layout_columns(
        ui.card(ui.card_header("Datos", ui.download_link("download_data", "Descargar", icon=ICONS["download"]), 
                               class_="d-flex justify-content-between align-items-center"), ui.output_data_frame("table"), full_screen=True),
        ui.card(ui.card_header("Gráfico"), output_widget("consumo_plot"), full_screen=True),
        col_widths=[4, 8],
    ),
    title="Tablero: Consumo energético en puntos de carga",
    fillable=True,
)


def server(input, output, session):
    # 1. Funciones reactivas base (filtros y cálculos)
    @reactive.calc
    def date_filter() -> pd.DataFrame:
        start_date, end_date = input.daterange()
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        return consumo.loc[(consumo.index >= start_date) & (consumo.index <= end_date)]
    
    @reactive.calc
    def consumo_data():
        data = date_filter().copy()
        pcs_seleccionados = input.puntos_carga()
        if pcs_seleccionados:
            cols = [f"PC{pc}" for pc in pcs_seleccionados]
            data = data[cols]
        opcion = input.consumos()
        if opcion == "A":
            return data
        elif opcion == "B":
            cons_12h = data.between_time('00:00:00', '12:00:00')
            acum_12h = cons_12h.groupby(cons_12h.index.date).cumsum()
            tot_12h = acum_12h.groupby(acum_12h.index.date).last()
            tot_12h.index = pd.to_datetime(tot_12h.index)
            return tot_12h
        elif opcion == "C":
            cons_15h = data.between_time('00:00:00', '15:00:00')
            acum_15h = cons_15h.groupby(cons_15h.index.date).cumsum()
            tot_15d15h = acum_15h.groupby(acum_15h.index.date).last().head(15)
            tot_15d15h.index = pd.to_datetime(tot_15d15h.index)
            return tot_15d15h
        elif opcion == "D":
            weekdays = data[data.index.dayofweek != 6]
            acum_weekdays = weekdays.groupby(weekdays.index.date).cumsum()
            tot_weekdays = acum_weekdays.groupby(acum_weekdays.index.date).last()
            tot_weekdays.index = pd.to_datetime(tot_weekdays.index)
            return tot_weekdays
        elif opcion == "E":
            sundays = data[data.index.dayofweek == 6]
            acum_sundays = sundays.groupby(sundays.index.date).cumsum()
            tot_sundays = acum_sundays.groupby(acum_sundays.index.date).last()
            tot_sundays.index = pd.to_datetime(tot_sundays.index)
            return tot_sundays

    # 2. Funciones de renderizado de datos
    @render.data_frame
    def table():
        data = consumo_data().copy()
        data.insert(0, "Fecha", data.index)
        data = data.reset_index(drop=True)
        return render.DataGrid(data)

    @render.ui
    def charge_point():
        data = consumo_data().copy()
        num_puntos = data.shape[1]
        return f"{num_puntos} punto(s)"

    @render.ui
    def total_kwh():
        data = consumo_data().copy()
        total = data.sum().sum()
        return f"{total:.2f} kWh"

    @render.ui
    def mean_kwh():
        data = consumo_data().copy()
        promedio = data.sum(axis=0).mean()
        return f"{promedio:.2f} kWh"

    @render.data_frame
    def max_min_table():
        data = consumo_data().copy()
        
        datos = []

        for punto in data.columns:
            valor_max = data[punto].max()
            valor_min = data[punto].min()
            fecha_max = data[punto].idxmax()
            fecha_min = data[punto].idxmin()

            datos.append([punto, 'Máximo', valor_max, fecha_max])
            datos.append([punto, 'Mínimo', valor_min, fecha_min])

        statistics = pd.DataFrame(datos, columns=['Punto de carga', 'Estadística', 'Valor (kWh)', 'Fecha'])
        statistics = statistics.sort_values(["Punto de carga", "Estadística"])

        return render.DataGrid(statistics)

    # 3. Funciones de visualización
    @render_widget
    def consumo_plot():
        data = consumo_data().copy()
        data.index = pd.to_datetime(data.index)
        data["Fecha"] = data.index.strftime("%Y-%m-%d %H:%M:%S")
        fig = px.line(
            data,
            x="Fecha",
            y=data.columns[:-1],
            labels={"value": "kWh", "variable": "Punto de carga"},
        )
        fig.update_xaxes(tickmode="auto")
        fig.update_layout(hovermode='x unified')
        return fig

    @render_widget
    def consumo_columns():
        data = consumo_data().copy()
        total_by_point = data.sum().reset_index()
        total_by_point.columns = ["Punto de carga", "kWh"]
        fig = px.bar(
            total_by_point,
            x="Punto de carga",
            y="kWh",
            color="Punto de carga",  
            color_discrete_sequence=px.colors.qualitative.Plotly, 
            labels={"kWh": "kWh"}
        )
        return fig

    # 4. Funciones de exportación
    @render.download(filename="consumo_datos.csv")
    def download_data():
        filtered = consumo_data().reset_index()
        with io.StringIO() as buf:
            filtered.to_csv(buf, index=False)
            yield buf.getvalue().encode()


app = App(app_ui, server)
