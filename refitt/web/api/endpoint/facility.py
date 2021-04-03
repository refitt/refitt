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

"""Facility profile endpoints."""


# type annotations
from typing import Union

# external libs
from flask import request

# internal libs
from ....database.model import Client, Facility, IntegrityError, NotFound
from ..app import application
from ..auth import authenticated, authorization
from ..response import endpoint, ConstraintViolation
from ..tools import require_data, collect_parameters, disallow_parameters


info: dict = {
    'Description': 'Request, add, update facility profiles',
    'Endpoints': {
        '/facility': {},
        '/facility/<facility_id>': {},
        '/facility/<facility_id>/user': {},
        '/facility/<facility_id>/user/<user_id>': {},
    }
}


@application.route('/facility', methods=['POST'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def add_facility(admin: Client) -> dict:  # noqa: unused client
    """Add new facility profile."""
    disallow_parameters(request)
    profile = require_data(request, data_format='json', validate=(lambda data: Facility.from_dict(data)))
    try:
        facility_id = profile.pop('id', None)
        if not facility_id:
            facility_id = Facility.add(profile).id
        else:
            Facility.update(facility_id, **profile)
    except IntegrityError as error:
        raise ConstraintViolation(str(error.args[0])) from error
    return {'facility': {'id': facility_id}}


info['Endpoints']['/facility']['POST'] = {
    'Description': 'Add or overwrite facility profile',
    'Permissions': 'Admin (level 0)',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Payload': {
            'Description': 'Facility profile data',
            'Type': 'application/json',
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'New facility ID',
                'Type': 'application/json'
            },
        },
        400: {'Description': 'JSON payload missing, malformed, or invalid'},
        401: {'Description': 'Access level insufficient, revoked, or token expired'},
        403: {'Description': 'Token not found or invalid'},
    }
}


@application.route('/facility/<id_or_name>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def get_facility(admin: Client, id_or_name: Union[int, str]) -> dict:  # noqa: unused client
    """Query for existing facility profile."""
    disallow_parameters(request)
    try:
        facility_id = int(id_or_name)
        return {'facility': Facility.from_id(facility_id).to_json()}
    except ValueError:
        facility_name = str(id_or_name)
        return {'facility': Facility.from_name(facility_name).to_json()}


info['Endpoints']['/facility/<facility_id>']['GET'] = {
    'Description': 'Request facility profile',
    'Permissions': 'Admin (level 0)',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'facility_id': {
                'Description': 'Unique ID for facility (or `name`)',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Facility profile',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access level insufficient, revoked, or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Facility does not exist'},
    }
}


@application.route('/facility/<int:facility_id>', methods=['PUT'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def update_facility(admin: Client, facility_id: int) -> dict:  # noqa: unused client
    """Update facility profile attributes."""
    try:
        profile = Facility.update(facility_id, **collect_parameters(request, allow_any=True))
    except IntegrityError as error:
        raise ConstraintViolation(str(error.args[0])) from error
    return {'facility': profile.to_json()}


info['Endpoints']['/facility/<facility_id>']['PUT'] = {
    'Description': 'Update facility profile attributes',
    'Permissions': 'Admin (level 0)',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'facility_id': {
                'Description': 'Unique ID for facility',
                'Type': 'Integer',
            }
        },
    },
    'Optional': {
        'Parameters': {
            'name': {
                'Description': 'Unique name for facility',
                'Type': 'Float'
            },
            'latitude': {
                'Description': 'Decimal latitude in degrees North',
                'Type': 'Float'
            },
            'longitude': {
                'Description': 'Decimal longitude in degrees West',
                'Type': 'Float'
            },
            'elevation': {
                'Description': 'Decimal elevation in meters above sea-level',
                'Type': 'Float'
            },
            'limiting_magnitude': {
                'Description': 'Decimal apparent magnitude',
                'Type': 'Float'
            },
            '*': {
                'Description': 'Arbitrary field added to JSON `data`',
                'Type': '*'
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Updated facility profile',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access level insufficient, revoked, or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Facility does not exist'},
    }
}


@application.route('/facility/<int:facility_id>', methods=['DELETE'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def delete_facility(admin: Client, facility_id: int) -> dict:  # noqa: unused client
    """Delete a facility profile (assuming no existing relationships)."""
    disallow_parameters(request)
    try:
        Facility.delete(facility_id)
    except IntegrityError as error:
        raise ConstraintViolation(str(error.args[0])) from error
    return {'facility': {'id': facility_id}}


info['Endpoints']['/facility/<facility_id>']['DELETE'] = {
    'Description': 'Delete facility profile (assuming no existing relationships)',
    'Permissions': 'Admin (level 0)',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'facility_id': {
                'Description': 'Unique ID for facility',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {'Description': 'Success'},
        401: {'Description': 'Access level insufficient, revoked, or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Facility does not exist'},
    }
}


@application.route('/facility/<int:facility_id>/user', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def get_all_facility_users(admin: Client, facility_id: int) -> dict:  # noqa: unused client
    """Query for users related to the given facility."""
    disallow_parameters(request)
    return {
        'user': [
            user.to_json()
            for user in Facility.from_id(facility_id).users()
        ]
    }


info['Endpoints']['/facility/<facility_id>/user']['GET'] = {
    'Description': 'Request user profiles associated with this facility',
    'Permissions': 'Admin (level 0)',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'facility_id': {
                'Description': 'Unique ID for facility',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'List of user profiles',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access level insufficient, revoked, or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Facility does not exist'},
    }
}


@application.route('/facility/<int:facility_id>/user/<int:user_id>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def get_facility_user(admin: Client, facility_id: int, user_id: int) -> dict:  # noqa: unused client
    """Query for a user related to the given facility."""
    disallow_parameters(request)
    users = [user.to_json() for user in Facility.from_id(facility_id).users() if user.id == user_id]
    if not users:
        raise NotFound(f'User ({user_id}) not associated with facility ({facility_id})')
    else:
        return {'user': users[0]}


info['Endpoints']['/facility/<facility_id>/user/<user_id>']['GET'] = {
    'Description': 'Check user is associated with this facility',
    'Permissions': 'Admin (level 0)',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'facility_id': {
                'Description': 'Unique ID for facility',
                'Type': 'Integer',
            },
            'user_id': {
                'Description': 'Unique ID for user',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Associated user profile',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access level insufficient, revoked, or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Facility does not exist or user not associated with this facility'},
    }
}


@application.route('/facility/<int:facility_id>/user/<int:user_id>', methods=['PUT'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def add_facility_user_association(admin: Client, facility_id: int, user_id: int) -> dict:  # noqa: unused client
    """Associate facility with the given user."""
    disallow_parameters(request)
    Facility.from_id(facility_id).add_user(user_id)
    return {}


info['Endpoints']['/facility/<facility_id>/user/<user_id>']['PUT'] = {
    'Description': 'Associate user with facility',
    'Permissions': 'Admin (level 0)',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'facility_id': {
                'Description': 'Unique ID for facility',
                'Type': 'Integer',
            },
            'user_id': {
                'Description': 'Unique ID for user',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {'Description': 'Success'},
        401: {'Description': 'Access level insufficient, revoked, or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Facility or user does not exist'},
    }
}


@application.route('/facility/<int:facility_id>/user/<int:user_id>', methods=['DELETE'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def delete_facility_user_association(admin: Client, facility_id: int, user_id: int) -> dict:  # noqa: unused client
    """Dissociate the facility for the given user."""
    disallow_parameters(request)
    Facility.from_id(facility_id).delete_user(user_id)
    return {}


info['Endpoints']['/facility/<facility_id>/user/<user_id>']['DELETE'] = {
    'Description': 'Disassociate user with facility',
    'Permissions': 'Admin (level 0)',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'facility_id': {
                'Description': 'Unique ID for facility',
                'Type': 'Integer',
            },
            'user_id': {
                'Description': 'Unique ID for user',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {'Description': 'Success'},
        401: {'Description': 'Access level insufficient, revoked, or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Facility or user does not exist'},
    }
}
