class GitHubError(Exception):
    pass

class GitHubAuthenticationError(GitHubError):
    pass

class GitHubPermissionError(GitHubError):
    pass

class GitHubRateLimitError(GitHubError):
    pass
