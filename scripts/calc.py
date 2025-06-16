from sqlalchemy.orm import Session, joinedload
from collections import defaultdict
import pandas as pd
from typing import List, Dict, Optional
from .models import Auftrag, Material, Maschine, Teil, Arbeitsplan
from .database import Session


def normalize_id(id_str):
    """Normalisiert IDs auf 7 Stellen mit führenden Nullen"""
    return str(id_str).zfill(7)


def calc_full_cost_structure(auftrag_nr: str) -> pd.DataFrame:
    session = Session()

    try:
        # Alle Teile mit Beziehungen laden
        all_teile = session.query(Teil).options(
            joinedload(Teil.material_obj),
            joinedload(Teil.arbeitsplaene)
        ).all()

        # Hierarchie-Struktur aufbauen
        children_map = defaultdict(list)
        for t in all_teile:
            if t.knoten:
                parent_id = normalize_id(t.knoten)
                children_map[parent_id].append(t)

        # Rekursive Funktion für Kostenberechnung
        def walk(teil: Teil, ebene: int, parent_anzahl: int) -> List[dict]:
            teil_id = normalize_id(teil.teil_id)
            anzahl = teil.anzahl or 1
            gesamt_anzahl = anzahl * parent_anzahl

            # Materialkosten berechnen
            mat_kost = teil.material_obj.kost if teil.mat and teil.material_obj else 0.0
            mat_pos = mat_kost * gesamt_anzahl
            mgk = mat_pos * 0.10

            # Fertigungskosten berechnen
            fert_kost = 0.0
            for op in teil.arbeitsplaene:
                maschine = session.query(Maschine).get(op.maschine)
                if maschine:
                    hours = op.dauer / 60
                    fert_kost += hours * maschine.ks
            fert_pos = fert_kost * gesamt_anzahl
            fgk = fert_pos * 0.10

            # Gesamtkosten für diese Position
            kumuliert = mat_pos + mgk + fert_pos + fgk

            # Datensatz erstellen
            record = {
                "Position": f"Teil {teil_id}",
                "Ebene": ebene,
                "Anzahl": anzahl,
                "Gesamt Anzahl": gesamt_anzahl,
                "Mat. Einzel": mat_kost,
                "Mat. Pos.": mat_pos,
                "MGK": mgk,
                "Fert. Pos.": fert_pos,
                "FGK": fgk,
                "Kumuliert": kumuliert
            }

            # Unterkomponenten verarbeiten
            result = [record]
            for child in children_map.get(teil_id, []):
                result.extend(walk(child, ebene + 1, gesamt_anzahl))

            return result

        # Start mit Auftragskopf
        table = [{
            "Position": f"Auftrag {auftrag_nr}",
            "Ebene": 0,
            "Anzahl": 1,
            "Gesamt Anzahl": 1,
            "Mat. Einzel": "",
            "Mat. Pos.": "",
            "MGK": "",
            "Fert. Pos.": "",
            "FGK": "",
            "Kumuliert": ""
        }]

        # Top-Level-Komponenten verarbeiten
        top_teile = [t for t in all_teile if t.knoten == auftrag_nr]
        for teil in top_teile:
            table.extend(walk(teil, 1, 1))

        # DataFrame erstellen
        df = pd.DataFrame(table)

        # Gesamtsumme berechnen
        total_sum = df["Kumuliert"].replace("", 0).sum()
        total_row = pd.DataFrame([{
            "Position": "GESAMT",
            "Ebene": "",
            "Anzahl": "",
            "Gesamt Anzahl": "",
            "Mat. Einzel": "",
            "Mat. Pos.": "",
            "MGK": "",
            "Fert. Pos.": "",
            "FGK": "",
            "Kumuliert": total_sum
        }])

        return pd.concat([df, total_row], ignore_index=True)

    finally:
        session.close()


def get_all_auftrag_ids() -> List[str]:
    session = Session()
    try:
        rows = session.query(Auftrag.auftrag_nr).distinct().all()
        return [r[0] for r in rows]
    finally:
        session.close()


def get_all_teil_ids() -> List[str]:
    session = Session()
    try:
        rows = session.query(Teil.teil_id).distinct().all()
        return [r[0] for r in rows]
    finally:
        session.close()


def calc_cost(teil_id: str, session: Session, parent_amount: float = 1, level: int = 0) -> dict:
    teil_id = normalize_id(teil_id)
    teil = session.query(Teil).options(
        joinedload(Teil.material_obj),
        joinedload(Teil.arbeitsplaene)
    ).get(teil_id)

    if not teil:
        return {
            "teil_id": teil_id,
            "total": 0,
            "structure": [],
            "level": level
        }

    # Materialkosten berechnen
    direct_mat = teil.material_obj.kost if teil.mat and teil.material_obj else 0.0
    mgk = direct_mat * 0.10

    # Fertigungskosten berechnen
    direct_fert = 0.0
    for op in teil.arbeitsplaene:
        maschine = session.query(Maschine).get(op.maschine)
        if maschine:
            hours = op.dauer / 60
            direct_fert += hours * maschine.ks
    fgk = direct_fert * 0.10

    # Unterkomponenten verarbeiten
    children_cost = 0.0
    children_struct = []

    children = session.query(Teil).filter(Teil.knoten == teil_id).all()
    for child in children:
        child_cost = calc_cost(child.teil_id, session, level=level + 1)
        child_total = (child.anzahl or 1) * child_cost["total"]
        children_cost += child_total

        children_struct.append({
            "teil_id": child.teil_id,
            "teil_nr": child.teil_nr,
            "anzahl": child.anzahl or 1,
            "kosten_pro_stk": child_cost["total"],
            "kosten_gesamt": child_total,
            "level": level + 1,
            "struktur": child_cost.get("structure", [])
        })

    # Gesamtkosten berechnen
    total = direct_mat + mgk + direct_fert + fgk + children_cost

    return {
        "teil_id": teil.teil_id,
        "teil_nr": teil.teil_nr,
        "level": level,
        "k_mat": direct_mat,
        "mgk": mgk,
        "k_fert": direct_fert,
        "fgk": fgk,
        "children_cost": children_cost,
        "total": total,
        "structure": children_struct
    }


def calc_order_cost(auftrag_nr: str) -> Dict:
    session = Session()
    try:
        top_level_teile = session.query(Teil).filter_by(knoten=auftrag_nr).all()

        positions = []
        order_total = 0.0

        for teil in top_level_teile:
            cost = calc_cost(teil.teil_id, session)
            anzahl = teil.anzahl or 1
            total_component = cost["total"] * anzahl

            positions.append({
                "teil_id": teil.teil_id,
                "teil_nr": teil.teil_nr,
                "amount": anzahl,
                "cost_per_unit": cost["total"],
                "total_cost": total_component,
                "structure": cost["structure"],
                "details": {
                    "direct_material": cost["k_mat"],
                    "material_overhead": cost["mgk"],
                    "direct_production": cost["k_fert"],
                    "production_overhead": cost["fgk"],
                    "subcomponents_cost": cost["children_cost"]
                }
            })
            order_total += total_component

        return {
            "auftrag_nr": auftrag_nr,
            "positions": positions,
            "order_total": order_total
        }
    finally:
        session.close()

def calc_machine_costs(order_nr: Optional[str] = None) -> Dict[str, float]:
    session = Session()
    if order_nr:
        teil_ids = [t.teil_id for t in session.query(Teil).filter_by(knoten=order_nr).all()]
        ops = session.query(Arbeitsplan).filter(Arbeitsplan.teil_id.in_(teil_ids)).all()
    else:
        ops = session.query(Arbeitsplan).all()

    costs = defaultdict(float)
    for op in ops:
        maschine = session.query(Maschine).get(op.maschine)
        if maschine:
            costs[op.maschine] += (op.dauer / 60) * maschine.ks

    session.close()
    return dict(costs)

def calc_machine_utilization(weeks: int = 1) -> Dict[str, Dict]:
    session = Session()
    max_hours = weeks * 40
    all_ops = session.query(Arbeitsplan).all()
    machine_hours = defaultdict(float)

    for op in all_ops:
        machine_hours[op.maschine] += op.dauer / 60

    result = {}
    for machine_id, hours in machine_hours.items():
        machine = session.query(Maschine).get(machine_id)
        result[machine_id] = {
            "bezeichnung": machine.bezeichnung if machine else "Unknown",
            "total_hours": hours,
            "max_hours": max_hours,
            "overload": hours > max_hours,
            "overload_percent": (hours / max_hours * 100) if max_hours else 0
        }

    session.close()
    return result

def get_material_costs() -> Dict[str, Dict]:
    session = Session()
    material_usage = defaultdict(float)
    all_teile = session.query(Teil).all()
    for teil in all_teile:
        if teil.mat and teil.material_obj:
            material_usage[teil.mat] += teil.material_obj.kost * (teil.anzahl or 1)

    result = {}
    for material_id, direct_cost in material_usage.items():
        material = session.query(Material).get(material_id)
        overhead = direct_cost * 0.10
        result[material_id] = {
            "material_name": material.bezeichnung if material else "Unknown",
            "direct_cost": direct_cost,
            "overhead": overhead,
            "total_cost": direct_cost + overhead
        }

    session.close()
    return result