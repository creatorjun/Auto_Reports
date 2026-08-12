# backend/src/infrastructure/factories/jira_factory.py
from src.application.ports.jira_port import JiraPort
from src.infrastructure.config.settings import Settings
from src.infrastructure.external.jira_client import JiraClient


class JiraFactory:
    @staticmethod
    def create(settings: Settings) -> JiraPort:
        return JiraClient(
            base_url=settings.jira_base_url,
            email=settings.jira_email,
            api_token=settings.jira_api_token,
            sla_initial_response_field_id=settings.sla_initial_response_field_id,
            sla_resolution_field_id=settings.sla_resolution_field_id,
            jira_tac_assignee_field_id=settings.jira_tac_assignee_field_id,
            jira_qa_assignee_field_id=settings.jira_qa_assignee_field_id,
        )
