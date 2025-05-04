
import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="ROI y Margen Amazon - Múltiples archivos", layout="wide")
st.title("Calculadora de ROI y Margen Neto - Amazon FBA")

# Paso 1: Subir archivos de pedidos con SKUs (pueden ser varios)
st.header("1. Cargar archivos de pedidos mensuales (con costes en SKUs)")
pedido_files = st.file_uploader("Sube uno o varios archivos .csv de pedidos de Amazon (Exportados desde Seller Central)", type="csv", accept_multiple_files=True)

sku_master = []

if pedido_files:
    for file in pedido_files:
        try:
            df = pd.read_csv(file, delimiter="\t")
            df.columns = [col.strip().strip('"') for col in df.columns]
            if "SKU del vendedor" in df.columns and "Nombre del producto" in df.columns:
                for _, row in df.iterrows():
                    sku_raw = str(row["SKU del vendedor"]).strip()
                    nombre = str(row["Nombre del producto"]).strip()
                    match = re.search(r"-\s*([\d]+,[\d]+)", sku_raw)
                    if match:
                        coste = match.group(1)
                        sku_master.append({
                            "Producto": nombre,
                            "Seller SKU": sku_raw,
                            "Coste adquisición (coma)": coste
                        })
        except Exception as e:
            st.error(f"Error leyendo archivo {file.name}: {e}")

    if sku_master:
        df_sku_master = pd.DataFrame(sku_master).drop_duplicates()
        st.success(f"Se han procesado {len(df_sku_master)} productos únicos con coste.")
        st.dataframe(df_sku_master)

        # Paso 2: Subir archivo CSV de transacciones
        st.header("2. Cargar archivo de transacciones")
        trans_file = st.file_uploader("Sube el archivo de transacciones de Amazon (ventas)", type="csv")

        if trans_file:
            try:
                df_trans = pd.read_csv(trans_file)
                df_trans.columns = [col.strip() for col in df_trans.columns]
                if "Detalles del producto" in df_trans.columns and "Total (EUR)" in df_trans.columns:
                    df_trans["Producto_normalizado"] = df_trans["Detalles del producto"].str.lower().str.strip()
                    df_sku_master["Producto_normalizado"] = df_sku_master["Producto"].str.lower().str.strip()
                    df_merged = pd.merge(
                        df_trans,
                        df_sku_master[["Producto_normalizado", "Coste adquisición (coma)"]],
                        on="Producto_normalizado",
                        how="left"
                    )

                    faltantes = df_merged[df_merged["Coste adquisición (coma)"].isnull()]["Detalles del producto"].unique().tolist()
                    if len(faltantes) > 0:
                        st.warning("Faltan costes para algunos productos. Introduce manualmente los valores.")
                        manual_costes = {}
                        for producto in faltantes:
                            key = f"manual_{producto[:40]}"
                            value = st.text_input(f"Coste para: {producto}", key=key)
                            if value:
                                manual_costes[producto.strip().lower()] = value

                        def asignar_coste_manual(row):
                            if pd.isna(row["Coste adquisición (coma)"]):
                                return manual_costes.get(row["Producto_normalizado"], None)
                            return row["Coste adquisición (coma)"]

                        df_merged["Coste final"] = df_merged.apply(asignar_coste_manual, axis=1)
                    else:
                        df_merged["Coste final"] = df_merged["Coste adquisición (coma)"]

                    # Cálculos
                    df_merged["Total (EUR)"] = df_merged["Total (EUR)"].astype(str).str.replace(",", ".").astype(float)
                    df_merged["Coste final"] = df_merged["Coste final"].astype(str).str.replace(",", ".").astype(float)
                    df_merged["Beneficio Neto"] = df_merged["Total (EUR)"] - df_merged["Coste final"]
                    df_merged["ROI (%)"] = (df_merged["Beneficio Neto"] / df_merged["Coste final"]) * 100
                    df_merged["Margen Neto (%)"] = (df_merged["Beneficio Neto"] / df_merged["Total (EUR)"]) * 100

                    st.header("3. Resultados")
                    st.dataframe(df_merged[[
                        "Fecha" if "Fecha" in df_merged.columns else df_merged.columns[0],
                        "Detalles del producto", "Total (EUR)", "Coste final",
                        "Beneficio Neto", "ROI (%)", "Margen Neto (%)"
                    ]])

                    csv = df_merged.to_csv(index=False).encode("utf-8")
                    st.download_button("Descargar resultados en CSV", csv, "resultados_amazon.csv", "text/csv")
                else:
                    st.error("El archivo de transacciones no contiene las columnas esperadas.")
            except Exception as e:
                st.error(f"Error procesando archivo de transacciones: {e}")
else:
    st.info("Sube primero uno o más archivos mensuales con productos y costes.")
