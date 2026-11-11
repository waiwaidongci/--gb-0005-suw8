from enum import StrEnum
class Dimension(StrEnum):
    CHANNEL="channel"
    MONTH="month"
    REGION="region"
BASE_FIELDS={"revenue","cost","refunds","orders"}
