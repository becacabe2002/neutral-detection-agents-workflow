import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(trace_id)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

class WorkflowLogger:
    @staticmethod
    def get_logger(name: str, trace_id: str = "N/A"):
        logger = logging.getLogger(name)
        return logging.LoggerAdapter(logger, {"trace_id": trace_id})