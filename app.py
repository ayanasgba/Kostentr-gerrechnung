import streamlit as st
import pandas as pd
from scripts.calc import (
    get_all_teil_ids,
    calc_cost,
    get_all_auftrag_ids,
    calc_order_cost,
    calc_full_cost_structure
)
from scripts.database import Session
from scripts.utils import format_de

st.set_page_config(page_title="Kostenträgerrechnung", layout="wide")
st.title("Kostenträgerrechnung")

mode = st.radio(
    "Bitte wählen Sie einen Modus",
    ["Nach Position (Teil)", "Nach Auftrag", "Detaillierte Tabelle nach Auftrag"]
)


def display_structure(structure, level=0):
    indent = "&nbsp;" * 4 * level
    for teil in structure:
        st.markdown(
            f"{indent}- **Teil-ID**: {teil['teil_id']} | "
            f"**Menge**: {teil['anzahl']} | "
            f"**Einzelkosten**: {format_de(teil['kosten_pro_stk'])} € | "
            f"**Gesamt**: {format_de(teil['kosten_gesamt'])} €",
            unsafe_allow_html=True
        )
        if teil["struktur"]:
            display_structure(teil["struktur"], level + 1)


if mode == "Nach Position (Teil)":
    @st.cache_data
    def load_ids():
        return get_all_teil_ids()


    ids = load_ids()
    teil = st.selectbox("Wählen Sie die Teile-ID aus", ids)
    teil = str(teil).zfill(7)

    if st.button("Berechnen"):
        session = Session()
        try:
            res = calc_cost(teil, session)
            col1, col2 = st.columns(2)
            col1.metric("Direkte Materialkosten", f"{res['k_mat']:.2f} €")
            col1.metric("Materialgemeinkosten (10%)", f"{res['mgk']:.2f} €")
            col2.metric("Direkte Fertigungskosten", f"{res['k_fert']:.2f} €")
            col2.metric("Fertigungsgemeinkosten (10%)", f"{res['fgk']:.2f} €")
            st.markdown("---")
            st.markdown(f"## Summe: {res['total']:.2f} €")

            if res['structure']:
                st.subheader("Komponentenstruktur")
                display_structure(res['structure'])
        finally:
            session.close()

elif mode == "Nach Auftrag":
    @st.cache_data
    def load_orders():
        return get_all_auftrag_ids()


    orders = load_orders()
    auftrag = st.selectbox("Wählen Sie einen Auftrag", orders)

    if st.button("Berechnen"):
        session = Session()
        try:
            oc = calc_order_cost(auftrag)
            st.subheader(f"📦 Auftragspositionen: **{auftrag}**")

            for p in oc["positions"]:
                with st.expander(f"Teil {p['teil_id']} ({p['amount']}x) – Gesamt: {format_de(p['total_cost'])} €"):
                    st.markdown(f"**Einzelpreis**: {format_de(p['cost_per_unit'])} €")
                    st.markdown(f"**Direktmaterial**: {format_de(p['details']['direct_material'])} €")
                    st.markdown(f"**Materialgemeinkosten (10%)**: {format_de(p['details']['material_overhead'])} €")
                    st.markdown(f"**Direkte Fertigung**: {format_de(p['details']['direct_production'])} €")
                    st.markdown(f"**Fertigungsgemeinkosten (10%)**: {format_de(p['details']['production_overhead'])} €")
                    st.markdown(f"**Kosten Subkomponenten**: {format_de(p['details']['subcomponents_cost'])} €")

                    if p["structure"]:
                        st.markdown("**🔽 Komponentenstruktur:**")
                        display_structure(p["structure"])

            st.markdown("---")
            st.markdown(f"## 💰 Gesamtkosten Auftrag: {format_de(oc['order_total'])} €")
        finally:
            session.close()

elif mode == "Detaillierte Tabelle nach Auftrag":
    @st.cache_data
    def load_orders():
        return get_all_auftrag_ids()


    orders = load_orders()
    auftrag = st.selectbox("Wählen Sie einen Auftrag für die detaillierte Tabelle", orders)

    if st.button("Tabelle generieren"):
        session = Session()
        try:
            df = calc_full_cost_structure(auftrag)
            st.subheader(f"Detaillierte Kostenstruktur für Auftrag {auftrag}")

            # Formatierung der numerischen Spalten
            numeric_cols = ["Gesamt Anzahl", "Mat. Einzel", "Mat. Pos.", "MGK", "Fert. Pos.", "FGK", "Kumuliert"]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = df[col].apply(
                        lambda x: format_de(x) if isinstance(x, (int, float)) else x
                    )


            # Highlight der Gesamtsumme
            def color_last_row(row):
                if row["Position"] == "GESAMT":
                    return ['background-color: #FFEB3B; font-weight: bold;'] * len(row)
                return [''] * len(row)


            styled_df = df.style.apply(color_last_row, axis=1)

            st.dataframe(
                styled_df,
                use_container_width=True,
                height=min(800, 35 * len(df))
            )

            # Gesamtsumme extra anzeigen
            total_row = df[df["Position"] == "GESAMT"].iloc[0]
            total_value = total_row["Kumuliert"]
            st.success(f"## Gesamtsumme des Auftrags: {total_value} €")
        finally:
            session.close()