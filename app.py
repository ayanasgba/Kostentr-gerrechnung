import streamlit as st
import pandas as pd
from scripts.calc import (
    get_all_teil_ids,
    calc_cost,
    get_all_auftrag_ids,
    calc_order_cost,
    calc_machine_costs
)
from scripts.database import Session
from scripts.utils import format_de

st.set_page_config(page_title="Kostenträgerrechnung", layout="wide")
st.title("Kostenträgerrechnung")

mode = st.radio(
    "Bitte wählen Sie einen Modus",
    ["Nach Position (Teil)", "Nach Auftrag"]
)

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
        st.subheader(f"Позиции заказа {auftrag}")
        st.table([
            {
                "Teil_ID": p["teil_id"],
                "Materialkosten": format_de(p['details']['direct_material']) + " €",
                "Fertigungskosten": format_de(p['details']['direct_production']) + " €",
                "Total (€)": format_de(p['total_cost']) + " €"
            }
            for p in oc["positions"]
        ])
        st.markdown("---")
        st.markdown(f"## Summe: {format_de(oc['order_total'])} €")

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
