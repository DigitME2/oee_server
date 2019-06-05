import sys
import logging

# logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)
#
#
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
# #logger.addHandler(handler)
# logger.addHandler(logging.StreamHandler(sys.stdout))

logging.debug("testdebug")
logging.info("testinfo")
logging.warn("testwarn")
logging.error("testerror")