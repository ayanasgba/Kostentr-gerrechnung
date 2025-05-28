from sqlalchemy import (
    Column, String, Float, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Auftrag(Base):
    __tablename__ = 'auftrag'
    auftrag_nr = Column('auftrag_nr', String, primary_key=True)
    k_mat      = Column('K_mat', Float)
    k_fert     = Column('K_fert', Float)
    dat_kost   = Column('dat_kost', String)

class Material(Base):
    __tablename__ = 'material'
    nr   = Column('Nr', String, primary_key=True)
    kost = Column('kost', Float)

class Maschine(Base):
    __tablename__ = 'maschine'
    nr          = Column('Nr', String, primary_key=True)
    bezeichnung = Column('Bezeichnung', String)
    ks          = Column('KS (€/h)', Float)

class Teil(Base):
    __tablename__ = 'teil'
    teil_id = Column('teil_id', String, primary_key=True)
    teil_nr = Column('teil_nr', String)
    knoten  = Column('knoten', String)
    k_mat   = Column('K_mat', Float)
    k_fert  = Column('K_fert', Float)
    anzahl  = Column('Anzahl', Float)
    mat     = Column('Mat', String, ForeignKey('material."Nr"'))

class Arbeitsplan(Base):
    __tablename__ = 'arbeitsplan'
    teil_id  = Column('teil_id', String, primary_key=True)
    ag_nr    = Column('ag_nr',     String, primary_key=True)
    maschine = Column('maschine',  String, ForeignKey('maschine."Nr"'))
    # Подставляем точное имя столбца из БД:
    dauer    = Column('dauer (min)', Float)

