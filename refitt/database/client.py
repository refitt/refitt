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

# standard libs
import os
from typing import Tuple

# internal libs
from ..__meta__ import __appname__
from ..core.config import HOME
from ..core.logging import logger

# external libs
from sshtunnel import SSHTunnelForwarder
import psycopg2 as psql


# initialize module level logger
log = logger.with_name(f'{__appname__}.database.client')


class ServerAddress:
    """Combines a `host` and `port`."""

    _host: str
    _port: int

    def __init__(self, host: str, port: int) -> None:
        """Initialize address."""
        self.host = host
        self.port = port

    @property
    def host(self) -> str:
        return self._host

    @host.setter
    def host(self, other: str) -> None:
        self._host = str(other)

    @property
    def port(self) -> int:
        return self._port

    @port.setter
    def port(self, other: int) -> None:
        self._port = int(other)

    def __str__(self) -> str:
        """String representation."""
        return f'{self.__class__.__name__}(host={self.host}, port={self.port})'

    def __repr__(self) -> str:
        """String representation."""
        return str(self)


class UserAuth:
    """A username and password pair."""

    _username: str
    _password: str = None

    def __init__(self, username: str, password: str = None) -> None:
        """Initialize address."""
        self.username = username
        self.password = password

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, other: str) -> None:
        self._username = str(other)

    @property
    def password(self) -> str:
        return self._password

    @password.setter
    def password(self, other: str) -> None:
        if other is None:
            self._password = None
        else:
            self._password = str(other)

    def __str__(self) -> str:
        """String representation."""
        return f'{self.__class__.__name__}(username={self.username}, password=...)'

    def __repr__(self) -> str:
        """String representation."""
        return str(self)



class SSHTunnel:
    """Wraps `sshtunnel.SSHTunnelForwarder`."""

    # host:port configuration
    _ssh: ServerAddress = None
    _remote: ServerAddress = None
    _local: ServerAddress = None

    # username/password
    _auth: UserAuth = None
    _pkey: str = None  # for password-less

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
    _auth: UserAuth = None
    _database: str = None

    # connection instance
    _connection: psql.extensions.connection = None

    # tunnel instance
    _tunnel: SSHTunnel = None

    def __init__(self, server: ServerAddress, auth: UserAuth,
                 database: str) -> None:
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
        if isinstance(other, UserAuth):
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
    def connection(self) -> psql.extensions.connection:
        """Database connection instance."""
        return self._connection

    @connection.setter
    def connection(self, other: psql.extensions.connection) -> None:
        """Set database connection instance."""
        if isinstance(other, psql.extensions.connection):
            self._connection = other
        else:
            raise TypeError(f'{self.__class__.__name__}.connection expects {psql.extensions.connection}')

    @property
    def tunnel(self) -> SSHTunnel:
        """SSHTunnel instance."""
        return self._tunnel

    @tunnel.setter
    def tunnel(self, other: SSHTunnel) -> None:
        """Set SSHTunnel instance."""
        if isinstance(other, SSHTunnel):
            self._tunnel = other
            self.server.host = other.local.host
            self.server.port = other.local.port
        else:
            raise TypeError(f'{self.__class__.__name__}.tunnel expects {SSHTunnel}')

    def connect(self) -> None:
        """Initiate the connection to the database."""
        log.debug(f'connecting to "{self.database}" at {self.server.host}:{self.server.port}')
        self._connection = psql.connect(host=self.server.host, port=self.server.port,
                                        database=self.database, user=self.auth.username,
                                        password=self.auth.password)
        log.debug(f'established connected to "{self.database}" at {self.server.host}:{self.server.port}')

    def close(self) -> None:
        """Close database connection and ssh-tunnel if necessary."""
        if self.connection is not None and not self.connection.closed:
            self.connection.close()
            log.debug(f'disconnected from "{self.database}" at {self.server.host}:{self.server.port}')
        if self.tunnel is not None:
            self.tunnel.forwarder.__exit__()
            self._tunnel = None
            log.debug(f'disconnected SSH tunnel')
            # if self.tunnel.forwarder.is_active:
            #     self.tunnel.forwarder.stop()
            #     log.debug(f'disconnected SSH tunnel')
            # if self.tunnel.forwarder.is_alive:
            #     self.tunnel.forwarder.close()
            #     log.debug(f'disconnecting SSH')

    def __enter__(self) -> 'DatabaseConnection':
        """Context manager."""
        self.connect()
        return self

    def __exit__(self, exc_tb, exc_type, exc_value) -> None:
        """Context manager exit."""
        self.close()

    def use_tunnel(self, ssh: ServerAddress, auth: UserAuth = None,
                   local: ServerAddress=ServerAddress('localhost', 54320)) -> None:
        """Establish an ssh-tunnel."""
        auth_ = auth if auth is not None else self.auth
        self.tunnel = SSHTunnel(ssh=ssh, auth=auth_, remote=self.server, local=local)
        self.tunnel.forwarder.start()
        return self