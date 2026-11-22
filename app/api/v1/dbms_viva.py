"""DBMS Viva REST API Endpoints: Exposes live schema introspection, multi-table joins,
constraint rejection proofs, atomic transaction tests, and query execution plans."""
from fastapi import APIRouter, Query
from app.services.dbms_service import DBMSService

router = APIRouter(prefix="/dbms", tags=["DBMS Viva & Database Architecture"])


@router.get("/overview")
def get_dbms_overview():
    """Returns database engine type, normalization summary, and table inventory."""
    return DBMSService.get_database_overview()


@router.get("/join")
def get_multi_table_join(limit: int = Query(default=10, ge=1, le=50)):
    """Executes a 6-table relational join across organizations, departments, positions,
    users, workspaces, documents, versions, and digital signatures."""
    records = DBMSService.run_multi_table_join(limit=limit)
    return {"count": len(records), "records": records}


@router.post("/test-constraint")
def test_constraint_rejection():
    """EXTRA CREDIT: Deliberately violates UNIQUE constraint and returns captured DB engine error."""
    return DBMSService.demonstrate_constraint_rejection()


@router.post("/test-transaction")
def test_atomic_transaction(simulate_failure: bool = Query(default=False)):
    """Demonstrates multi-table ACID transaction atomicity and rollback safety."""
    return DBMSService.demonstrate_atomic_transaction(simulate_failure=simulate_failure)


@router.get("/explain-plan")
def get_query_execution_plans():
    """Runs EXPLAIN QUERY PLAN comparing indexed B-Tree search vs unindexed full table scan."""
    return DBMSService.explain_query_plans()
