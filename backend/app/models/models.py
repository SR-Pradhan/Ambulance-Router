from sqlalchemy import Column, Integer, Float, String, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.sql import expression
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
    # Physical length of the road in km. This never changes.
    weight = Column(Float, nullable=False)
    # How congested this road is: 1.0 is free flowing, 2.0 is half speed.
    # Always >= 1, because traffic can only slow a road down. Routing weights
    # are travel TIME derived from these two columns, not from weight alone.
    traffic_factor = Column(Float, nullable=False, default=1.0,
                            server_default="1.0")

class Hospital(Base):
    __tablename__ = "hospitals"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    total_beds = Column(Integer, nullable=False)
    available_beds = Column(Integer, nullable=False)

    # Facility status. Separate boolean columns rather than a free text list,
    # so the database can index and constrain them and the meaning is fixed.
    # These are CAPABILITIES, not capacity: a hospital either has a cardiac
    # unit or it does not, and no amount of free beds substitutes for one.
    has_icu = Column(Boolean, nullable=False, default=False,
                     server_default=expression.false())
    has_trauma_unit = Column(Boolean, nullable=False, default=False,
                             server_default=expression.false())
    has_cardiac_unit = Column(Boolean, nullable=False, default=False,
                              server_default=expression.false())

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
    # server_default as well as default: `default` is applied by SQLAlchemy on
    # insert, `server_default` is a real DEFAULT in the table. Without the
    # latter, a row inserted by raw SQL (or psql by hand) would violate the NOT
    # NULL constraint, and the schema created by create_all would not match the
    # one this project was originally developed against.
    status = Column(String, nullable=False, default="pending",
                    server_default="pending")
    # Triage severity: critical | urgent | standard. Drives the priority queue.
    severity = Column(String, nullable=False, default="standard",
                      server_default="standard")
    # Nullable: most cases need no specialist unit.
    required_facility = Column(String, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    # When an ambulance was actually assigned, which is NOT when the request
    # was made: a queued patient can wait a long time first. Live positions are
    # interpolated from this, because using created_at means a patient who
    # waited twenty minutes gets an ambulance that has notionally already
    # driven for twenty minutes and arrives instantly. Nullable, because a
    # pending request has not been dispatched yet.
    dispatched_at = Column(TIMESTAMP, nullable=True)