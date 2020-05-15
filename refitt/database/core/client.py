# Copyright REFITT Team 2019. All rights reserved.
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the Apache License (v2.0) as published by the Apache Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the Apache License for more details.
#
# You should have received a copy of the Apache License along with this program.
# If not, see <https://www.apache.org/licenses/LICENSE-2.0>.

"""Connection and interface to database."""

# type annotations
from __future__ import annotations
from typing import Optional

# standard libs
import os
import atexit

# internal libs
from .types import ServerAddress, UserAuth
from .config import connection_info
from ...core.config import HOME
from ...core.logging import Logger

# external libs
from sshtunnel import SSHTunnelForwarder
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, Connection  # noqa (__all__)


# initialize module level logger
log = Logger(__name__)


class SSHTunnel:
    """Wraps `sshtunnel.SSHTunnelForwarder`."""

    # host:port configuration
    _ssh: ServerAddress = None
    _remote: ServerAddress = None
    _local: ServerAddress = None

    # username/password
    _auth: Optional[UserAuth] = None
    _pkey: Optional[str] = None  # for password-less

    # the ssh-tunnel server
    _forwarder: SSHTunnelForwarder = None

    def __init__(self, ssh: ServerAddress, auth: UserAuth,
                 remote: ServerAddress, local: ServerAddress,
                 keyfile: str = f'{HOME}/.ssh/id_rsa') -> None:

        self.ssh = ssh
        self.remote = remote
        self.local = local
        self.auth = auth

        if os.path.isfile(keyfile):
            self.pkey = keyfile

        self.forwarder = SSHTunnelForwarder(
            (self.ssh.host, self.ssh.port),
            ssh_username=self.auth.username,
            ssh_password=self.auth.password, ssh_pkey=self.pkey,
            remote_bind_address=(self.remote.host, self.remote.port),
            local_bind_address=(self.local.host, self.local.port))

    @property
    def ssh(self) -> ServerAddress:
        """SSH server address."""
        return self._ssh

    @ssh.setter
    def ssh(self, other: ServerAddress) -> None:
        """Set SSH server address."""
        if isinstance(other, ServerAddress):
            self._ssh = other
        else:
            raise TypeError(f'{self.__class__.__name__}.ssh expects {ServerAddress}')

    @property
    def remote(self) -> ServerAddress:
        """Remote server address."""
        return self._remote

    @remote.setter
    def remote(self, other: ServerAddress) -> None:
        """Set remote server address."""
        if isinstance(other, ServerAddress):
            self._remote = other
        else:
            raise TypeError(f'{self.__class__.__name__}.remote expects {ServerAddress}')

    @property
    def local(self) -> ServerAddress:
        """Local server address."""
        return self._local

    @local.setter
    def local(self, other: ServerAddress) -> None:
        """Set local server address."""
        if isinstance(other, ServerAddress):
            self._local = other
        else:
            raise TypeError(f'{self.__class__.__name__}.local expects {ServerAddress}')

    @property
    def auth(self) -> UserAuth:
        """User authentication for the ssh server."""
        return self._auth

    @auth.setter
    def auth(self, other: UserAuth) -> None:
        """Set user authentication for the ssh server."""
        if other is None:
            self._auth = UserAuth(None, None)
        if isinstance(other, UserAuth):
            self._auth = other
        else:
            raise TypeError(f'{self.__class__.__name__}.auth expects {UserAuth}')

    @property
    def pkey(self) -> str:
        """SSH keyfile (e.g., ~/.ssh/id_rsa)."""
        return self._pkey

    @pkey.setter
    def pkey(self, other: str) -> None:
        """Set SSH keyfile (e.g., ~/.ssh/id_rsa)."""
        if not isinstance(other, str):
            raise TypeError(f'{self.__class__.__name__}.pkey expects {str}')
        elif not os.path.isfile(other):
            raise FileNotFoundError(other)
        else:
            self._pkey = other

    @property
    def forwarder(self) -> SSHTunnelForwarder:
        """`SSHTunnelForwarder` instance."""
        return self._forwarder

    @forwarder.setter
    def forwarder(self, other: SSHTunnelForwarder) -> None:
        """Set `SSHTunnelForwarder` instance."""
        if isinstance(other, SSHTunnelForwarder):
            self._forwarder = other
        else:
            raise TypeError(f'{self.__class__.__name__}.forwarder expects {SSHTunnelForwarder}')

    def __str__(self) -> str:
        """String representation."""
        cls_ = self.__class__.__name__
        pad_ = ' ' * len(cls_)
        return (f'{cls_}(ssh={self.ssh},\n{pad_} local={self.local},\n'
                f'{pad_} remote={self.remote},\n{pad_} auth={self.auth},\n'
                f'{pad_} pkey={self.pkey})')

    def __repr__(self) -> str:
        """String representation."""
        return str(self)


class DatabaseClient:
    """Connect to a database (optionally via an SSH tunnel)."""

    # connection details
    _server: ServerAddress = ServerAddress('localhost', 5432)
    _auth: Optional[UserAuth] = None
    _database: str = None

    # SQLAlchemy database engine
    _engine: Engine = None

    # tunnel instance
    _tunnel: Optional[SSHTunnel] = None

    def __init__(self, server: ServerAddress, auth: UserAuth, database: str) -> None:
        """Initialize database connection details."""

        self.server = server
        self.auth = auth
        self.database = database

    @property
    def server(self) -> ServerAddress:
        """Database server address."""
        return self._server

    @server.setter
    def server(self, other: ServerAddress) -> None:
        """Set database server address."""
        if isinstance(other, ServerAddress):
            self._server = other
        else:
            raise TypeError(f'{self.__class__.__name__}.server expects {ServerAddress}')

    @property
    def auth(self) -> UserAuth:
        """User authentication for the database server."""
        return self._auth

    @auth.setter
    def auth(self, other: UserAuth) -> None:
        """Set user authentication for the database server."""
        if other is None:
            self._auth = None
        elif isinstance(other, UserAuth):
            self._auth = other
        else:
            raise TypeError(f'{self.__class__.__name__}.auth expects {UserAuth}')

    @property
    def database(self) -> str:
        """Database name."""
        return self._database

    @database.setter
    def database(self, other: str) -> None:
        """Set database name."""
        if isinstance(other, str):
            self._database = other
        else:
            raise TypeError(f'{self.__class__.__name__}.database expects {str}')

    @property
    def engine(self) -> Engine:
        """Database engine instance."""
        return self._engine

    @engine.setter
    def engine(self, other: Engine) -> None:
        """Set database engine instance."""
        if isinstance(other, Engine):
            self._engine = other
        else:
            raise TypeError(f'{self.__class__.__name__}.engine expects {Engine}')

    @property
    def tunnel(self) -> SSHTunnel:
        """SSHTunnel instance."""
        return self._tunnel

    @tunnel.setter
    def tunnel(self, other: SSHTunnel) -> None:
        """Set SSHTunnel instance."""
        if isinstance(other, SSHTunnel):
            self._tunnel = other
            self.server = other.local
        else:
            raise TypeError(f'{self.__class__.__name__}.tunnel expects {SSHTunnel}')

    def connect(self) -> None:
        """Initiate the connection to the database."""
        auth = '' if self.auth is None else f'{self.auth.username}:{self.auth.password}@'
        host, port = tuple(self.server)
        self._engine = create_engine(f'postgresql://{auth}{host}:{port}/{self.database}')
        log.debug(f'connected to "{self.database}" at {self.server.host}:{self.server.port}')

    def close(self) -> None:
        """Close database connection and ssh-tunnel if necessary."""
        self.engine.dispose()
        log.debug(f'disconnected from "{self.database}" at {self.server.host}:{self.server.port}')
        if self.tunnel is not None:
            self.tunnel.forwarder.__exit__()
            log.debug('disconnected tunnel')

    def __enter__(self) -> DatabaseClient:
        """Context manager."""
        self.connect()
        return self

    def __exit__(self, exc_tb, exc_type, exc_value) -> None:
        """Context manager exit."""
        self.close()

    def use_tunnel(self, ssh: ServerAddress, auth: UserAuth = None,
                   local: ServerAddress = ServerAddress('localhost', 54321)) -> DatabaseClient:
        """Establish an ssh-tunnel."""
        auth_ = auth if auth is not None else self.auth
        self.tunnel = SSHTunnel(ssh=ssh, auth=auth_, remote=self.server, local=local)
        self.tunnel.forwarder.start()
        log.debug(f'established tunnel {local.port}:{self.server.host}:{self.server.port} '
                  f'{ssh.host}:{ssh.port}')
        return self

    @classmethod
    def from_config(cls, **kwargs) -> DatabaseClient:
        """Parse config to define client connection."""
        info = connection_info(**kwargs)
        client = cls(**info['database'])
        if 'tunnel' in info:
            client.use_tunnel(**info['tunnel'])
        return client

    def begin(self) -> Connection:
        """
        Execute a multipart transaction.

        Used within a context manager, this allows multipart database
        actions to be defined as part of a whole and automatically rollback
        changes in the event of an error.

        Example
        -------
        >>> from refitt import database
        >>> client = database.connect()
        >>> with client.begin() as transaction:
        ...     transaction.execute('A')
        ...     transaction.execute('B')
        """
        return self.engine.begin()

    def __str__(self) -> str:
        """String representation of database client."""
        if self.tunnel is None:
            return f'<DatabaseClient[{self.server.host}:{self.server.port}]>'
        else:
            ssh = self.tunnel.ssh
            local = self.tunnel.local
            remote = self.tunnel.remote
            return (f'<DatabaseClient[{local.port}:{remote.host}:{remote.port} '
                    f'{ssh.host}:{ssh.port}]>')

    def __repr__(self) -> str:
        """String representation of database client."""
        return str(self)


# Note: The direct client interface allows for safe connection to the database. However,
#       repeatedly acquiring/discarding the connection (especially with SSH tunneling)
#       causes significant delay in the commandline interface. Below, a "persistent"
#       connection is implemented in a way that allows the higher level methods in
#       `refitt.database.interface` (e.g., execute()) to reuse an existing connection if
#       available. It is the responsibility of the user/code to release the connection
#       though!

# global reference
_PERSISTENT_CLIENT: Optional[DatabaseClient] = None


def connect(**kwargs) -> DatabaseClient:
    """
    Establish a client connection to the database. This will create a persistent
    connection that the rest of the library can make use of without the need to
    specify otherwise.

    Options
    -------
    **kwargs:
        Keyword arguments are passed through to `.DatabaseClient.from_config`.

    Returns
    -------
    client: `.DatabaseClient`
        A persistent connection.

    See Also
    --------
    `.DatabaseClient.from_config`

    Note
    ----
    An attempt is made to automatically call :func:`disconnect` at exit.
    However, this is not guaranteed. If possible, call it manually at exit!

    If this method has already been called previously, the existing client
    connection is simply provided back. This is independent of the arguments!

    Example
    -------
    >>> from refitt import database
    >>> database.connect(profile='test')
    <DatabaseClient[localhost:5432]>

    >>> client = database.connect(profile='test')
    >>> client.engine
    Engine(postgresql://localhost:5432/refitt)
    """
    global _PERSISTENT_CLIENT
    if _PERSISTENT_CLIENT is not None:
        return _PERSISTENT_CLIENT

    _PERSISTENT_CLIENT = DatabaseClient.from_config(**kwargs)
    _PERSISTENT_CLIENT.connect()
    return _PERSISTENT_CLIENT


@atexit.register
def disconnect() -> None:
    """Release database client connection."""
    global _PERSISTENT_CLIENT
    if _PERSISTENT_CLIENT is not None:
        _PERSISTENT_CLIENT.close()
        _PERSISTENT_CLIENT = None
