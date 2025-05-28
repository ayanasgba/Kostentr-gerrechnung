from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from collections import defaultdict
from typing import List
from scripts.models import (
    Auftrag, Material, Maschine,
    Teil, Arbeitsplan, Base
)


DB_URL = 'postgresql+psycopg2://admin:admin123@localhost:5432/kostcalc'
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)

def calc_cost(teil_id: str) -> dict:
    """
    Считает и возвращает словарь с ключами:
     - k_mat: прямые Materialkosten
     - mgk:  косвенные Materialgemeinkosten
     - k_fert: прямые Fertigungskosten
     - fgk:  косвенные Fertigungsgemeinkosten
     - total: суммарная себестоимость
    """
    session = Session()

    # 1) Materialkosten
    teile = session.query(Teil).filter_by(teil_id=teil_id).all()
    k_mat = sum(t.anzahl * session.get(Material, t.mat).kost for t in teile)
    mgk   = k_mat * 0.10  # 10%

    # 2) Fertigungskosten
    ops = session.query(Arbeitsplan).filter_by(teil_id=teil_id).all()
    k_fert = 0.0
    anzahl = teile[0].anzahl if teile else 1
    for op in ops:
        mas = session.get(Maschine, op.maschine)
        k_fert += ((op.dauer / 60) * mas.ks) * anzahl
    fgk = k_fert * 0.10  # 10%

    session.close()

    total = k_mat + mgk + k_fert + fgk
    return {
        "k_mat":   k_mat,
        "mgk":     mgk,
        "k_fert":  k_fert,
        "fgk":     fgk,
        "total":   total
    }


def get_all_teil_ids() -> List[str]:
    """Возвращает список всех ID деталей из таблицы Teil."""
    session = Session()
    # вытаскиваем список кортежей [('0000001',), ('0000002',), …]
    rows = session.query(Teil.teil_id).distinct().all()
    session.close()
    # распаковываем в простой список
    return [row[0] for row in rows]

def get_all_auftrag_ids() -> list[str]:
    session = Session()
    rows = session.query(Auftrag.auftrag_nr).distinct().all()
    session.close()
    return [r[0] for r in rows]

def calc_order_cost(auftrag_nr: str) -> dict:
    """
    Считает по заказу:
      - детализацию по позициям (Teil) с их total
      - сумму total по всему заказу
    Возвращает словарь:
      {
        "positions": [{"teil_id": "...", "total": ...}, ...],
        "order_total": ...
      }
    """
    session = Session()
    # находим все Unterposition (Teil), где Teil.knoten == auftrag_nr
    teile = session.query(Teil).filter_by(knoten=auftrag_nr).all()
    positions = []
    order_total = 0.0
    for t in teile:
        costs = calc_cost(t.teil_id)
        positions.append({"teil_id": t.teil_id, **costs})
        order_total += costs["total"]
    session.close()
    return {"positions": positions, "order_total": order_total}

def calc_machine_costs(order_nr: str | None = None) -> dict[str, float]:
    """
    Считает прямые производственные затраты (без OH!) по каждой машине.
    Если order_nr указан, берёт только операции по деталям этого заказа;
    иначе — по всем деталям в базе.
    Возвращает словарь {maschine_nr: kosten_€}.
    """
    session = Session()
    # фильтр по заказу
    if order_nr:
        # находим все teil_id, у которых knoten == order_nr
        teil_ids = [t[0] for t in session
                    .query(Teil.teil_id)
                    .filter_by(knoten=order_nr)
                    .all()]
        ops = session.query(Arbeitsplan).filter(Arbeitsplan.teil_id.in_(teil_ids)).all()
    else:
        ops = session.query(Arbeitsplan).all()

    costs: dict[str, float] = defaultdict(float)
    for op in ops:
        mas = session.get(Maschine, op.maschine)
        # время в часах * ставка
        c = (op.dauer / 60) * mas.ks
        costs[op.maschine] += c

    session.close()
    return dict(costs)

if __name__ == '__main__':
    print("Alle Aufträge:", get_all_auftrag_ids())
    oc = calc_order_cost('A00001')
    print("Auftrag's Details A00001:", oc["positions"])
    print("Total nach Auftrag:", oc["order_total"])
    print("Kostenstellen (все):", calc_machine_costs())
    print("Kostenstellen для A00001:", calc_machine_costs("A00001"))


