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

"""Client credential creation end-points."""


# internal libs
from ....database.model import Client, NotFound
from ..app import application
from ..response import endpoint
from ..auth import authenticated, authorization


@application.route('/client/<int:user_id>', methods=['GET'])
@endpoint
@authenticated
@authorization(level=0)
def get_client(admin: Client, user_id: int) -> dict:  # noqa: admin client not used
    try:
        key, secret = Client.new_key(user_id)
    except NotFound:
        key, secret, client = Client.new(user_id)
    return {'client': {'key': key.value, 'secret': secret.value}}


@application.route('/client/secret/<int:user_id>', methods=['GET'])
@endpoint
@authenticated
@authorization(level=0)
def get_client_secret(admin: Client, user_id: int) -> dict:  # noqa: admin client not used
    try:
        key, secret = Client.new_secret(user_id)
    except NotFound:
        key, secret, client = Client.new(user_id)
    return {'client': {'key': key.value, 'secret': secret.value}}
