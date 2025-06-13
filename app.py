import streamlit as st
import pandas as pd

from scripts.calc import (
    get_all_teil_ids,
    calc_cost,
    get_all_auftrag_ids,
    calc_order_cost,
    calc_machine_costs,
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
    indent = "&nbsp;" * 4 * level  # HTML-отступ
    for teil in structure:
        st.markdown(
            f"{indent}- **Teil-ID**: {teil['teil_id']} | "
            f"**Menge**: {teil['anzahl']} | "
            f"**Einzelkosten**: {teil['kosten_pro_stk']:.2f} € | "
            f"**Gesamt**: {teil['kosten_gesamt']:.2f} €",
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
        res = calc_cost(teil, session)
        session.close()
        col1, col2 = st.columns(2)
        col1.metric("Direkte Materialkosten",        f"{res['k_mat']:.3f} €")
        col1.metric("Materialgemeinkosten (10%)",   f"{res['mgk']:.2f} €")
        col2.metric("Direkte Fertigungskosten",      f"{res['k_fert']:.2f} €")
        col2.metric("Fertigungsgemeinkosten (10%)", f"{res['fgk']:.2f} €")
        st.markdown("---")
        st.markdown(f"## Summe: {res['total']:.2f} €")


elif mode == "Nach Auftrag":
    @st.cache_data
    def load_orders():
        return get_all_auftrag_ids()


    orders = load_orders()
    auftrag = st.selectbox("Выберите номер заказа", orders)

    if st.button("Berechnen"):
        oc = calc_order_cost(auftrag)
        st.subheader(f"📦 Позиции заказа **{auftrag}**")

        for p in oc["positions"]:
            with st.expander(f"Teil {p['teil_id']} (x{p['amount']}) — Gesamt: {p['total_cost']:.2f} €"):
                st.markdown(f"**Einzelpreis**: {p['cost_per_unit']:.2f} €")
                st.markdown(f"**Direktmaterial**: {p['details']['direct_material']:.2f} €")
                st.markdown(f"**Materialgemeinkosten (10%)**: {p['details']['material_overhead']:.2f} €")
                st.markdown(f"**Direkte Fertigung**: {p['details']['direct_production']:.2f} €")
                st.markdown(f"**Fertigungsgemeinkosten (10%)**: {p['details']['production_overhead']:.2f} €")
                st.markdown(f"**Kosten Subkomponenten**: {p['details']['subcomponents_cost']:.2f} €")

                if p["structure"]:
                    st.markdown("**🔽 Struktur:**")
                    display_structure(p["structure"])

        st.markdown("---")
        st.markdown(f"## 💰 Gesamtkosten: {format_de(oc['order_total'])} €")

# else:  # По центрам затрат (Maschinen)
#     @st.cache_data
#     def load_orders():
#         return ["<Alle>"] + get_all_auftrag_ids()
#     orders = load_orders()
#     sel = st.selectbox("Для какого заказа показать?", orders)
#     if st.button("Показать по машинам"):
#         key = None if sel == "<Все>" else sel
#         mc = calc_machine_costs(order_nr=key)
#         if not mc:
#             st.info("Нет операций для выбранного заказа.")
#         else:
#             df = (
#                 pd.DataFrame.from_dict(mc, orient="index", columns=["Kosten (€)"])
#                   .reset_index()
#                   .rename(columns={"index": "Maschine"})
#             )
#             st.subheader(
#                 f"Fertigungskosten по машинам "
#                 f"{'(всех заказов)' if key is None else f'для заказа {key}'}"
#             )
#             st.dataframe(df, use_container_width=True)
#             st.bar_chart(df.set_index("Maschine")["Kosten (€)"])

elif mode == "Detaillierte Tabelle nach Auftrag":
    @st.cache_data
    def load_orders():
        return get_all_auftrag_ids()

    orders = load_orders()
    auftrag = st.selectbox("Wähle Auftrag für die detaillierte Tabelle", orders)

    if st.button("Tabelle anzeigen"):
        df = calc_full_cost_structure(auftrag)
        st.subheader(f"Detaillierte Kostenstruktur für Auftrag {auftrag}")
        st.dataframe(df, use_container_width=True)

