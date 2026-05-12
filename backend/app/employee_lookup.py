from sqlalchemy.orm import Session

from app.db import Employee


def resolve_employee(db: Session, identifier: object | None) -> Employee | None:
    value = str(identifier or "").strip()
    if not value:
        return None

    employee = db.query(Employee).filter(Employee.employee_code == value).first()
    if employee is not None:
        return employee

    if value.isdigit():
        return db.query(Employee).filter(Employee.id == int(value)).first()
    return None
