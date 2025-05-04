
import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Calculadora de ROI y Margen Amazon", layout="wide")

st.title("Calculadora de ROI y Margen Neto para Ventas en Amazon")

# Paso 1: Subida de archivos
st.header("1. Subida de archivos")
csv_file = st.file_uploader("Sube el archivo CSV de transacciones (con columnas en español)", type=["csv"])
txt_file = st.file_uploader("Sube el archivo TXT de SKUs y costes", type=["txt"])

if csv_file and txt_file:
    # Lectura del CSV
    try:
        df_csv = pd.read_csv(csv_file)
    except Exception as e:
        st.error(f"Error al leer el CSV: {e}")
        st.stop()

    # Verificación de columnas necesarias en español
    required_cols = ["Tipo de transacción", "Id. de pedido", "Detalles del producto", "Total (EUR)"]
    if not all(col in df_csv.columns for col in required_cols):
        st.error("El archivo CSV no contiene todas las columnas necesarias.")
        st.stop()

    # Filtrar ventas
    df_sales = df_csv[df_csv["Tipo de transacción"] == "Pago del pedido"].copy()

    # Lectura del TXT de SKUs
    try:
        txt_lines = txt_file.read().decode("utf-8").splitlines()
        sku_cost_dict = {}
        for line in txt_lines:
            match = re.search(r"(\d{2}/\d{2}/\d{4})\s+-\s+([0-9]+,[0-9]+)", line)
            if match:
                sku_key = line.strip().split()[0]
                cost = match.group(2).replace(",", ".")
                sku_cost_dict[sku_key] = float(cost)
    except Exception as e:
        st.error(f"Error al procesar el TXT: {e}")
        st.stop()

    # Extraer el SKU del final del campo "Detalles del producto"
    def extraer_sku(descripcion):
        partes = descripcion.split("-")
        return partes[-1].strip() if len(partes) > 1 else descripcion.strip()

    df_sales["SKU extraído"] = df_sales["Detalles del producto"].apply(extraer_sku)

    # Asignar coste
    df_sales["Coste"] = df_sales["SKU extraído"].apply(lambda sku: sku_cost_dict.get(sku, None))

    # Pedir costes manuales si faltan
    missing = df_sales[df_sales["Coste"].isnull()]["SKU extraído"].unique()
    if len(missing) > 0:
        st.warning("Faltan costes para algunos SKUs. Introduce los valores manualmente:")
        for sku in missing:
            value = st.number_input(f"Coste para SKU {sku}:", min_value=0.0, format="%.2f", key=sku)
            df_sales.loc[df_sales["SKU extraído"] == sku, "Coste"] = value

    # Cálculos
    df_sales["Total (EUR)"] = df_sales["Total (EUR)"].astype(str).str.replace(",", ".").astype(float)
    df_sales["Beneficio Neto"] = df_sales["Total (EUR)"] - df_sales["Coste"]
    df_sales["ROI (%)"] = (df_sales["Beneficio Neto"] / df_sales["Coste"]) * 100
    df_sales["Margen Neto (%)"] = (df_sales["Beneficio Neto"] / df_sales["Total (EUR)"]) * 100

    # Mostrar resultados
    st.header("2. Resultados")
    st.dataframe(df_sales[["Fecha", "Detalles del producto", "SKU extraído", "Total (EUR)",
                           "Coste", "Beneficio Neto", "ROI (%)", "Margen Neto (%)"]])

    # Exportación
    st.header("3. Exportar resultados")
    output = df_sales.to_csv(index=False).encode("utf-8")
    st.download_button("Descargar CSV con resultados", output, "resultados_roi.csv", "text/csv")
else:
    st.info("Por favor, sube ambos archivos para comenzar.")
