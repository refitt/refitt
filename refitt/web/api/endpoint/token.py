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

"""Token creation end-points."""


# internal libs
from ....database.model import Client, Session
from ..app import application
from ..response import endpoint
from ..auth import authenticate, authenticated, authorization


@application.route('/token', methods=['GET'])
@endpoint
@authenticate
def get_token(client: Client) -> dict:
    return {'token': Session.new(client.user_id).encrypt()}


@application.route('/token/<int:user_id>', methods=['GET'])
@endpoint
@authenticated
@authorization(level=0)
def get_token_for_user(admin: Client, user_id: int) -> dict:  # noqa: client not used
    return {'token': Session.new(user_id).encrypt()}
