class VideoError(Exception):
    def __init__(self, code, message, retryable=False, *, details=None):
        super().__init__(message)
        self.code, self.retryable = code, retryable
        self.details = details or {}
