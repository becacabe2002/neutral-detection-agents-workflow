import logging
import sys

class TraceIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'trace_id'):
            record.trace_id = 'N/A'
        return True

# Configure root logger
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(trace_id)s] %(name)s: %(message)s")
handler.setFormatter(formatter)
handler.addFilter(TraceIdFilter())

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
for h in root_logger.handlers[:]:
    root_logger.removeHandler(h)
root_logger.addHandler(handler)

class WorkflowLogger:
    @staticmethod
    def get_logger(name: str, trace_id: str = "N/A"):
        logger = logging.getLogger(name)
        return logging.LoggerAdapter(logger, {"trace_id": trace_id})