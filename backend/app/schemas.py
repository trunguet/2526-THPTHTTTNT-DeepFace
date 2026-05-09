from pydantic import BaseModel


class EmployeeCreate(BaseModel):
    full_name: str
    employee_id: str
    email: str = ""
    department: str = ""
    image_url: str = ""
    image_object_key: str = ""


class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    department: str | None = None


class VerifyFaceRequest(BaseModel):
    image: str
    employee_id: str | None = None
    camera_location: str = "Main Gate"
    access_type: str = "check_in"
    # Optional client-side liveness challenge (blink / head-turn).
    # If provided and false, server rejects immediately.
    challenge_passed: bool | None = None
    challenge_type: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class AdminRegisterRequest(BaseModel):
    username: str
    password: str


class AdminLoginRequest(BaseModel):
    username: str
    password: str
