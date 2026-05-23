from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.queues.embedding_queue import (
    EMBEDDING_QUEUE_NAME,
    EmbeddingJob,
    enqueue_embedding_job,
)
from app.repositories.employee_repository import (
    create_employee,
    get_employee_by_code,
    get_employee_by_id,
    list_employees,
    soft_delete_employee,
    update_employee,
    update_employee_embedding_status,
)
from app.schemas.employee import EmployeeCreate, EmployeeUpdate


class EmployeeCodeAlreadyExistsError(Exception):
    pass


class EmployeeNotFoundError(Exception):
    pass


def get_employees(db: Session) -> list[Employee]:
    return list_employees(db)


def get_employee(db: Session, employee_id: int) -> Employee | None:
    return get_employee_by_id(db, employee_id)


def add_employee(db: Session, payload: EmployeeCreate) -> Employee:
    existing_employee = get_employee_by_code(db, payload.code)
    if existing_employee is not None:
        raise EmployeeCodeAlreadyExistsError

    return create_employee(db, payload)


def edit_employee(
    db: Session,
    employee_id: int,
    payload: EmployeeUpdate,
) -> Employee | None:
    employee = get_employee_by_id(db, employee_id)
    if employee is None:
        return None

    if payload.code is not None and payload.code != employee.code:
        existing_employee = get_employee_by_code(db, payload.code)
        if existing_employee is not None:
            raise EmployeeCodeAlreadyExistsError

    return update_employee(db, employee, payload)


def delete_employee(db: Session, employee_id: int) -> Employee | None:
    employee = get_employee_by_id(db, employee_id)
    if employee is None:
        return None

    return soft_delete_employee(db, employee)


def queue_employee_embedding_job(
    db: Session,
    employee_id: int,
    image_key: str,
) -> EmbeddingJob:
    employee = get_employee_by_id(db, employee_id)
    if employee is None:
        raise EmployeeNotFoundError

    job = enqueue_embedding_job(employee.id, image_key)
    update_employee_embedding_status(
        db,
        employee,
        status="pending",
        error=None,
    )
    return job


def get_embedding_queue_name() -> str:
    return EMBEDDING_QUEUE_NAME
