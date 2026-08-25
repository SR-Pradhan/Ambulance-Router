from sqlalchemy import Column, Integer, Float, String, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from app.db import Base

class RoadNode(Base):
    __tablename__ = "road_nodes"
    id = Column(Integer, primary_key=True)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)

class RoadEdge(Base):
    __tablename__ = "road_edges"
    id = Column(Integer, primary_key=True)
    from_node_id = Column(Integer, ForeignKey("road_nodes.id"))
    to_node_id = Column(Integer, ForeignKey("road_nodes.id"))
    weight = Column(Float, nullable=False)

class Hospital(Base):
    __tablename__ = "hospitals"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    total_beds = Column(Integer, nullable=False)
    available_beds = Column(Integer, nullable=False)

class Ambulance(Base):
    __tablename__ = "ambulances"
    id = Column(Integer, primary_key=True)
    current_lat = Column(Float, nullable=False)
    current_lng = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="available")

class EmergencyRequest(Base):
    __tablename__ = "emergency_requests"
    id = Column(Integer, primary_key=True)
    patient_lat = Column(Float, nullable=False)
    patient_lng = Column(Float, nullable=False)
    assigned_ambulance_id = Column(Integer, ForeignKey("ambulances.id"))
    assigned_hospital_id = Column(Integer, ForeignKey("hospitals.id"))
    status = Column(String, nullable=False, default="pending")
    # Triage severity: critical | urgent | standard. Drives the priority queue.
    severity = Column(String, nullable=False, default="standard")
    created_at = Column(TIMESTAMP, server_default=func.now())