
import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Calculadora de ROI y Margen Amazon", layout="wide")

st.title("Calculadora de ROI y Margen Neto para Ventas en Amazon")

# Paso 1: Subida de archivos
st.header("1. Subida de archivos")
csv_file = st.file_uploader("Sube el archivo CSV de transacciones", type=["csv"])
txt_file = st.file_uploader("Sube el archivo TXT de SKUs y costes", type=["txt"])

if csv_file and txt_file:
    # Lectura del CSV
    try:
        df_csv = pd.read_csv(csv_file)
    except Exception as e:
        st.error(f"Error al leer el CSV: {e}")
        st.stop()

    # Lectura del TXT y extracción de costes
    try:
        txt_lines = txt_file.read().decode("utf-8").splitlines()
        sku_cost_dict = {}
        for line in txt_lines:
            match = re.search(r"(\d{2}/\d{2}/\d{4})\s+-\s+([0-9]+,[0-9]+)", line)
            if match:
                sku = line.strip().split()[0]
                cost = match.group(2).replace(",", ".")
                sku_cost_dict[sku] = float(cost)
    except Exception as e:
        st.error(f"Error al procesar el TXT: {e}")
        st.stop()

    # Verificación de columnas necesarias
    required_cols = ["TRANSACTION_TYPE", "TRANSACTION_EVENT_ID", "ITEM_DESCRIPTION",
                     "SELLER_SKU", "TOTAL_ACTIVITY_VALUE_AMT_VAT_EXCL"]
    if not all(col in df_csv.columns for col in required_cols):
        st.error("El archivo CSV no contiene todas las columnas necesarias.")
        st.stop()

    # Filtro solo para ventas
    df_sales = df_csv[df_csv["TRANSACTION_TYPE"] == "SALE"].copy()

    # Cálculo
    def obtener_coste(sku):
        return sku_cost_dict.get(sku, None)

    df_sales["Coste"] = df_sales["SELLER_SKU"].apply(obtener_coste)

    # Solicitar coste manualmente si falta
    missing_costs = df_sales[df_sales["Coste"].isnull()]["SELLER_SKU"].unique()
    if len(missing_costs) > 0:
        st.warning("Faltan costes para algunos SKUs. Introduce los valores manualmente:")
        for sku in missing_costs:
            value = st.number_input(f"Coste para {sku}:", min_value=0.0, format="%.2f", key=sku)
            df_sales.loc[df_sales["SELLER_SKU"] == sku, "Coste"] = value

    # Cálculo de Beneficio, ROI y Margen
    df_sales["TOTAL_ACTIVITY_VALUE_AMT_VAT_EXCL"] = df_sales["TOTAL_ACTIVITY_VALUE_AMT_VAT_EXCL"].astype(str).str.replace(",", ".").astype(float)
    df_sales["Beneficio Neto"] = df_sales["TOTAL_ACTIVITY_VALUE_AMT_VAT_EXCL"] - df_sales["Coste"]
    df_sales["ROI (%)"] = (df_sales["Beneficio Neto"] / df_sales["Coste"]) * 100
    df_sales["Margen Neto (%)"] = (df_sales["Beneficio Neto"] / df_sales["TOTAL_ACTIVITY_VALUE_AMT_VAT_EXCL"]) * 100

    # Paso 2: Visualización
    st.header("2. Resultados")
    st.dataframe(df_sales[["ITEM_DESCRIPTION", "SELLER_SKU", "TOTAL_ACTIVITY_VALUE_AMT_VAT_EXCL",
                           "Coste", "Beneficio Neto", "ROI (%)", "Margen Neto (%)"]])

    # Paso 3: Exportación
    st.header("3. Exportar resultados")
    to_export = df_sales.to_csv(index=False).encode("utf-8")
    st.download_button("Descargar CSV con resultados", to_export, "resultados_roi.csv", "text/csv")
else:
    st.info("Por favor, sube ambos archivos para comenzar.")
