from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeUpdate


def list_employees(db: Session) -> list[Employee]:
    return list(db.scalars(select(Employee).order_by(Employee.id)))


def get_employee_by_id(db: Session, employee_id: int) -> Employee | None:
    return db.get(Employee, employee_id)


def get_employee_by_code(db: Session, code: str) -> Employee | None:
    return db.scalar(select(Employee).where(Employee.code == code))


def create_employee(db: Session, payload: EmployeeCreate) -> Employee:
    employee = Employee(**payload.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


def update_employee(
    db: Session,
    employee: Employee,
    payload: EmployeeUpdate,
) -> Employee:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)

    db.commit()
    db.refresh(employee)
    return employee


def soft_delete_employee(db: Session, employee: Employee) -> Employee:
    employee.status = "inactive"
    db.commit()
    db.refresh(employee)
    return employee


def update_employee_embedding_status(
    db: Session,
    employee: Employee,
    *,
    status: str,
    error: str | None = None,
) -> Employee:
    employee.embedding_status = status
    employee.embedding_error = error
    db.commit()
    db.refresh(employee)
    return employee
