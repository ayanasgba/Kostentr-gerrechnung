from typing import List, Dict, Optional, Set
from sqlalchemy.orm import joinedload
from collections import defaultdict
from .models import Auftrag, Material, Maschine, Teil, Arbeitsplan
from .database import Session

def get_all_auftrag_ids() -> List[str]:
    session = Session()
    rows = session.query(Auftrag.auftrag_nr).distinct().all()
    session.close()
    return [r[0] for r in rows]

def get_all_teil_ids() -> List[str]:
    session = Session()
    rows = session.query(Teil.teil_id).distinct().all()
    session.close()
    return [r[0] for r in rows]

def calc_cost(teil_id: str, session, parent_amount: float = 1) -> dict:
    teil_id = str(teil_id).zfill(7)
    teil = session.query(Teil).options(joinedload(Teil.material_obj)).get(teil_id)
    if not teil:
        return {"k_mat": 0, "mgk": 0, "k_fert": 0, "fgk": 0, "children_cost": 0, "total": 0}

    direct_mat = teil.material_obj.kost if teil.mat and teil.material_obj else 0
    mgk = direct_mat * 0.10

    direct_fert = 0.0
    operations = session.query(Arbeitsplan).filter_by(teil_id=teil_id).all()
    for op in operations:
        maschine = session.query(Maschine).get(op.maschine)
        if maschine:
            direct_fert += (op.dauer / 60) * maschine.ks
    fgk = direct_fert * 0.10

    children_cost = 0.0
    print("Ищу детей для TEIL:", teil.teil_id)
    print("Сравниваю с KNOTEN:", repr(teil.teil_id))

    children = session.query(Teil).filter(Teil.knoten == teil_id).all()
    for child in children:
        child_cost = calc_cost(str(child.teil_id).zfill(7), session)
        children_cost += (child.anzahl or 1) * child_cost["total"]

    total = direct_mat + mgk + direct_fert + fgk + children_cost

    return {
        "k_mat": direct_mat,
        "mgk": mgk,
        "k_fert": direct_fert,
        "fgk": fgk,
        "children_cost": children_cost,
        "total": total
    }

def calc_order_cost(auftrag_nr: str) -> Dict:
    session = Session()
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
            "details": {
                "direct_material": cost["k_mat"],
                "material_overhead": cost["mgk"],
                "direct_production": cost["k_fert"],
                "production_overhead": cost["fgk"],
                "subcomponents_cost": cost["children_cost"]
            }
        })
        order_total += total_component

    session.close()
    return {"auftrag_nr": auftrag_nr, "positions": positions, "order_total": order_total}

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