# backend/src/domain/value_objects/widget_id.py
from enum import StrEnum


class WidgetId(StrEnum):
    YEARLY_CREATED         = "w1"
    YEARLY_RESOLVED        = "w2"
    CREATED_VS_RESOLVED    = "w3"
    ISSUE_REVIEW           = "w4"
    DATA_REQUEST           = "w5"
    RESULT_PENDING         = "w6"
    SLA_INITIAL_RESPONSE   = "w7"
    SLA_RESOLUTION_MONTHLY = "w8"
    SLA_MET_VS_VIOLATED    = "w9"
    SLA_DELAY_REASON       = "w10"
    AVG_RESOLUTION_TYPE    = "w11"
    OVERDUE_ISSUES         = "w12"
    RECENT_ISSUES          = "w13"
