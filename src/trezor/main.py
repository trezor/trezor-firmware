from trezor import config
from trezor import loop
from trezor import workflow
from trezor import log

config.init()

log.level = log.DEBUG


def run(default_workflow):
    workflow.start_default(default_workflow)
    loop.run_forever()
