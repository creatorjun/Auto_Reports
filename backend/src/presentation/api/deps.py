# backend/src/presentation/api/deps.py
from fastapi import Request

from src.application.ports.job_runner_port import JobRunnerPort
from src.domain.ports.jira_port import JiraPort


def get_job_runner(request: Request) -> JobRunnerPort:
    return request.app.state.job_runner


def get_jira(request: Request) -> JiraPort:
    return request.app.state.container.jira_port()
