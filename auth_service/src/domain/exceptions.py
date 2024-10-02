class UserAlreadyExistsException(Exception):
    pass


class UserNotFoundException(Exception):
    pass


class InvalidCredentialsException(Exception):
    pass


class NotAuthorizedException(Exception):
    pass
