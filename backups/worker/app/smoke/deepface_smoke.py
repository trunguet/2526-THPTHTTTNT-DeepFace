import time
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import insert, text, update

from app.config.database import get_db_session
from app.db.schema import access_logs, employees
from app.services.embedding_service import create_employee_embedding
from app.services.face_pipeline_service import process_access_check


SMOKE_DIR = Path("/app/data/smoke")
EMPLOYEE_REF_IMAGE = SMOKE_DIR / "employee_a_ref.jpg"
SAME_PERSON_IMAGE = SMOKE_DIR / "employee_a_ok.jpg"
DIFFERENT_PERSON_IMAGE = SMOKE_DIR / "employee_b_ok.jpg"
NO_FACE_IMAGE = SMOKE_DIR / "no_face.jpg"


@dataclass(frozen=True)
class SmokeCase:
    name: str
    image_path: Path
    expected_status: str


@dataclass(frozen=True)
class SmokeResult:
    name: str
    image_path: str
    expected_status: str
    actual_status: str
    employee_id: int | None
    score: float | None
    seconds: float
    message: str

    @property
    def passed(self) -> bool:
        return self.actual_status == self.expected_status


def _require_smoke_images() -> None:
    missing = [
        str(path)
        for path in (
            EMPLOYEE_REF_IMAGE,
            SAME_PERSON_IMAGE,
            DIFFERENT_PERSON_IMAGE,
            NO_FACE_IMAGE,
        )
        if not path.is_file()
    ]
    if missing:
        raise SystemExit(f"Missing smoke image(s): {', '.join(missing)}")


def _create_camera(db) -> int:
    result = db.execute(
        text(
            "INSERT INTO cameras (name, location, stream_url, status) "
            "VALUES (:name, :location, :stream_url, :status) "
            "RETURNING id"
        ),
        {
            "name": "DeepFace Smoke Camera",
            "location": "Container smoke test",
            "stream_url": None,
            "status": "active",
        },
    )
    camera_id = result.scalar_one()
    db.commit()
    return int(camera_id)


def _create_employee(db) -> int:
    run_id = time.strftime("%Y%m%d%H%M%S")
    result = db.execute(
        insert(employees).values(
            code=f"SMOKE_A_{run_id}",
            name="Smoke Test Employee A",
            department="QA",
            status="active",
            embedding_status="pending",
            embedding_error=None,
        )
    )
    employee_id = int(result.inserted_primary_key[0])
    db.commit()
    return employee_id


def _create_access_log(db, *, camera_id: int, image_path: Path) -> int:
    result = db.execute(
        insert(access_logs).values(
            employee_id=None,
            camera_id=camera_id,
            status="processing",
            score=None,
            image_path=str(image_path),
        )
    )
    log_id = int(result.inserted_primary_key[0])
    db.commit()
    return log_id


def _run_case(db, *, camera_id: int, smoke_case: SmokeCase) -> SmokeResult:
    log_id = _create_access_log(db, camera_id=camera_id, image_path=smoke_case.image_path)
    started_at = time.perf_counter()
    decision = process_access_check(
        db,
        log_id=log_id,
        image_path=str(smoke_case.image_path),
    )
    seconds = time.perf_counter() - started_at
    return SmokeResult(
        name=smoke_case.name,
        image_path=str(smoke_case.image_path),
        expected_status=smoke_case.expected_status,
        actual_status=decision.status,
        employee_id=decision.employee_id,
        score=decision.score,
        seconds=seconds,
        message=decision.message,
    )


def _print_result(result: SmokeResult) -> None:
    score = "n/a" if result.score is None else f"{result.score:.6f}"
    marker = "PASS" if result.passed else "FAIL"
    print(
        f"[{marker}] {result.name}: expected={result.expected_status} "
        f"actual={result.actual_status} employee_id={result.employee_id} "
        f"score={score} seconds={result.seconds:.2f}"
    )
    print(f"      image={result.image_path}")
    print(f"      message={result.message}")


def main() -> None:
    _require_smoke_images()
    total_started_at = time.perf_counter()

    with get_db_session() as db:
        camera_id = _create_camera(db)
        employee_id = _create_employee(db)

        print("Creating real DeepFace embedding in worker container...")
        embedding_started_at = time.perf_counter()
        embedding = create_employee_embedding(
            db,
            employee_id=employee_id,
            image_path=str(EMPLOYEE_REF_IMAGE),
        )
        db.execute(
            update(employees)
            .where(employees.c.id == employee_id)
            .values(embedding_status="success", embedding_error=None)
        )
        db.commit()
        print(
            "Embedding ready: "
            f"employee_id={employee_id} embedding_id={embedding.id} "
            f"model={embedding.model_name} vector_size={len(embedding.vector)} "
            f"seconds={time.perf_counter() - embedding_started_at:.2f}"
        )

        cases = [
            SmokeCase("same person should be granted", SAME_PERSON_IMAGE, "granted"),
            SmokeCase("different person should be denied", DIFFERENT_PERSON_IMAGE, "denied"),
            SmokeCase("image without face should be error", NO_FACE_IMAGE, "error"),
        ]
        results = [
            _run_case(db, camera_id=camera_id, smoke_case=smoke_case)
            for smoke_case in cases
        ]

    print("")
    print("DeepFace smoke results:")
    for result in results:
        _print_result(result)

    failed = [result for result in results if not result.passed]
    print("")
    print(f"Total smoke time: {time.perf_counter() - total_started_at:.2f}s")
    if failed:
        raise SystemExit(f"{len(failed)} DeepFace smoke case(s) failed.")

    print("DeepFace container smoke test passed.")


if __name__ == "__main__":
    main()
