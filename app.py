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
from scripts.models import Teil, Auftrag, Material, Maschine, Arbeitsplan


st.set_page_config(page_title="Kostenträgerrechnung", layout="wide")
st.title("Kostenträgerrechnung")

mode = st.radio(
    "Bitte wählen Sie einen Modus",
    ["Detaillierte Tabelle nach Auftrag", "Daten eingeben"]
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


if mode == "Detaillierte Tabelle nach Auftrag":
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
            numeric_cols = ["Anzahl", "Gesamt Anzahl", "Mat. Einzel", "Mat. Pos.", "MGK", "Fert. Pos.", "FGK", "Gesamtkosten"]
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
            total_value = total_row["Gesamtkosten"]
            st.success(f"## Gesamtsumme des Auftrags: {format_de(total_value)} €")
        finally:
            session.close()

if mode == "Daten eingeben":
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Auftrag", "➕ Teil", "➕ Arbeitsplan", "➕ Material / Maschine"])

    with tab1:
        st.subheader("Neuen Auftrag anlegen")
        auftrag_nr = st.text_input("Auftrag-Nr", max_chars=10, key="inp_auftrag_nr").strip().upper()

        if st.button("Auftrag speichern", key="btn_save_auftrag"):
            if not auftrag_nr:
                st.error("Bitte geben Sie eine Auftragsnummer ein.")
            else:
                session = Session()
                try:
                    exists = session.query(Auftrag).filter_by(auftrag_nr=auftrag_nr).first()
                    if exists:
                        st.warning(f"Auftrag {auftrag_nr} existiert bereits.")
                    else:
                        session.add(Auftrag(auftrag_nr=auftrag_nr))
                        session.commit()
                        st.success(f"Auftrag {auftrag_nr} wurde erfolgreich gespeichert.")
                finally:
                    session.close()

    with tab2:
        st.subheader("Neues Teil anlegen")
        teil_id_raw = st.text_input("Teil-ID (z. B. 0000042)", key="inp_teil_id_raw")
        teil_id = teil_id_raw.strip().zfill(7)
        teil_nr = st.text_input("Teil-Nr", key="inp_teil_nr")
        knoten = st.text_input("Gehört zu (Auftrag oder übergeordnetes Teil)", key="inp_knoten").strip().upper()
        mat = st.text_input("Material-Nr (z. B. M004)", key="inp_mat").strip().upper()
        anzahl = st.number_input("Anzahl", min_value=1, value=1, key="inp_anzahl")

        if st.button("Teil speichern", key="btn_save_teil"):
            session = Session()
            try:
                if session.query(Teil).filter_by(teil_id=teil_id).first():
                    st.warning(f"Teil {teil_id} existiert bereits.")
                elif not session.query(Material).filter_by(nr=mat).first():
                    st.error(f"Material {mat} existiert nicht.")
                else:
                    session.add(Teil(teil_id=teil_id, teil_nr=teil_nr, knoten=knoten, anzahl=anzahl, mat=mat))
                    session.commit()
                    st.success(f"Teil {teil_id} wurde gespeichert.")
            finally:
                session.close()

    with tab3:
        st.subheader("Arbeitsplan hinzufügen")
        ap_teil_id = st.text_input("Teil-ID (für Arbeitsplan)", max_chars=7, key="inp_ap_teil_id").zfill(7)
        ag_nr = st.text_input("AG-Nr", key="inp_ag_nr")
        maschine = st.text_input("Maschine-Nr", key="inp_ap_maschine")
        dauer = st.number_input("Dauer (min)", min_value=1, key="inp_dauer")

        if st.button("Arbeitsplan speichern", key="btn_save_ap"):
            session = Session()
            try:
                if not session.query(Teil).filter_by(teil_id=ap_teil_id).first():
                    st.error("Teil existiert nicht.")
                elif not session.query(Maschine).filter_by(nr=maschine).first():
                    st.error("Maschine existiert nicht.")
                else:
                    exists = session.query(Arbeitsplan).filter_by(teil_id=ap_teil_id, ag_nr=ag_nr).first()
                    if exists:
                        st.warning("Diese Arbeitsplan-Zeile existiert bereits.")
                    else:
                        session.add(Arbeitsplan(teil_id=ap_teil_id, ag_nr=ag_nr, maschine=maschine, dauer=dauer))
                        session.commit()
                        st.success("Arbeitsplan gespeichert.")
            finally:
                session.close()

    with tab4:
        st.subheader("Material oder Maschine hinzufügen")

        subtab1, subtab2 = st.columns(2)

        with subtab1:
            mat_nr = st.text_input("Material-Nr", key="inp_mat_nr").strip().upper()
            mat_kost = st.number_input("Kosten (€)", min_value=0.0, key="inp_mat_kost")
            if st.button("Material speichern", key="btn_save_mat"):
                session = Session()
                try:
                    if session.query(Material).filter_by(nr=mat_nr).first():
                        st.warning("Material existiert bereits.")
                    else:
                        session.add(Material(nr=mat_nr, kost=mat_kost))
                        session.commit()
                        st.success("Material gespeichert.")
                finally:
                    session.close()

        with subtab2:
            maschine_nr = st.text_input("Maschine-Nr", key="inp_maschine_nr").strip().upper()
            bezeichnung = st.text_input("Bezeichnung", key="inp_m_bezeichnung")
            ks = st.number_input("Kosten €/h", min_value=0.0, key="inp_m_ks")
            if st.button("Maschine speichern", key="btn_save_maschine"):
                session = Session()
                try:
                    if session.query(Maschine).filter_by(nr=maschine_nr).first():
                        st.warning("Maschine existiert bereits.")
                    else:
                        session.add(Maschine(nr=maschine_nr, bezeichnung=bezeichnung, ks=ks))
                        session.commit()
                        st.success("Maschine gespeichert.")
                finally:
                    session.close()