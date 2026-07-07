from enum import StrEnum


class WidgetId(StrEnum):
    OVERDUE_ISSUES            = "w1"
    DEV_SLA_DELAY             = "w2"
    TAC_SLA_DELAY             = "w3"
    LAB_UNASSIGNED            = "w4"
    SLA_DELAY_BY_TYPE         = "w5"
    SLA_DELAY_BY_STATUS       = "w6"
    SLA_DELAY_REASON          = "w7"
    YEARLY_CREATED            = "w8"
    YEARLY_RESOLVED           = "w9"
    AVG_RESOLUTION_TYPE       = "w10"
    RESOLUTION_REPORT         = "w11"
    SLA_MET_VS_VIOLATED       = "w12"
    QA_SLA_DELAY              = "w13"
    CREATED_VS_RESOLVED       = "w14"
    SLA_INITIAL_RESPONSE      = "w15"
    SLA_RESOLUTION_MONTHLY    = "w16"
