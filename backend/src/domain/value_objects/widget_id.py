# backend/src/domain/value_objects/widget_id.py
from enum import StrEnum


class WidgetId(StrEnum):
    OVERDUE_ISSUES         = "w1"
    ISSUE_REVIEW           = "w2"
    DATA_REQUEST           = "w3"
    SLA_DELAY_REASON       = "w4"
    YEARLY_CREATED         = "w5"
    YEARLY_RESOLVED        = "w6"
    AVG_RESOLUTION_TYPE    = "w7"
    RESOLUTION_REPORT      = "w8"
    SLA_MET_VS_VIOLATED    = "w9"
    RESULT_PENDING         = "w10"
    CREATED_VS_RESOLVED    = "w11"
    SLA_INITIAL_RESPONSE   = "w12"
    SLA_RESOLUTION_MONTHLY = "w13"
