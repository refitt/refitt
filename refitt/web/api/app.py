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

"""Initialize Flask application instance."""


# type annotations
from __future__ import annotations

# standard libs
import json

# external libs
from flask import Flask, Response, request

# internal libs
from .response import STATUS


# flask application
application = Flask(__name__)


@application.errorhandler(STATUS['Not Found'])
def not_found() -> Response:
    """Response to an invalid request."""
    return Response(json.dumps({'status': 'error',
                                'message': f'not found: {request.path}'}),
                    status=STATUS['Not Found'],
                    mimetype='application/json')
