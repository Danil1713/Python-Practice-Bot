class AttemptError(Exception):
    pass


class AttemptUserNotFound(AttemptError):
    pass


class AttemptProjectNotFound(AttemptError):
    pass


class AttemptProjectLocked(AttemptError):
    pass


class AttemptAlreadyPending(AttemptError):
    pass


class AttemptAILimitReached(AttemptError):
    pass
