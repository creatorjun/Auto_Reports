# backend/src/application/errors.py
class EntityNotFoundError(Exception):
    def __init__(self, entity: str, identifier: object) -> None:
        super().__init__(f"{entity} not found: {identifier}")
        self.entity = entity
        self.identifier = identifier


class JobAlreadyRunningError(Exception):
    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        super().__init__(f"A report job is already running: {job_id}")
