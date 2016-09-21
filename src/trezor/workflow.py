from trezor import log, loop

_started_workflows = []
_default_workflow = None
_default_workflow_genfunc = None


def start_default(genfunc):
    global _default_workflow
    global _default_workflow_genfunc
    _default_workflow_genfunc = genfunc
    _default_workflow = _default_workflow_genfunc()
    log.info(__name__, 'starting default workflow %s', _default_workflow)
    loop.schedule_task(_default_workflow)


def start_workflow(workflow):
    global _default_workflow
    if _default_workflow is not None:
        log.info(__name__, 'closing default workflow %s', _default_workflow)
        _default_workflow.close()
        _default_workflow = None

    log.info(__name__, 'starting workflow %s', workflow)
    _started_workflows.append(workflow)
    loop.schedule_task(watch_workflow(workflow))


async def watch_workflow(workflow):
    global _default_workflow
    try:
        return await workflow
    finally:
        _started_workflows.remove(workflow)

        if not _started_workflows and _default_workflow_genfunc is not None:
            start_default(_default_workflow_genfunc)
