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

"""User profile endpoints."""


# type annotations
from typing import Union

# external libs
from flask import request

# internal libs
from ....database.model import Client, User, IntegrityError, NotFound
from ..app import application
from ..auth import authenticated, authorization
from ..response import endpoint, ConstraintViolation, PermissionDenied
from ..tools import require_data, collect_parameters, disallow_parameters


info: dict = {
    'Description': 'Request, add, update user profiles',
    'Endpoints': {
        '/whoami': {},
        '/user': {},
        '/user/<user_id>': {},
        '/user/<user_id>/facility': {},
        '/user/<user_id>/facility/<facility_id>': {},
    }
}


@application.route('/whoami', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_profile(client: Client) -> dict:
    """Get user profile for authenticated `client`."""
    disallow_parameters(request)

    return {'user': client.user.to_json(),
            'client': client.to_json(pop=['user_id', 'secret', 'valid'])}


info['Endpoints']['/whoami']['GET'] = {
    'Description': 'Validate token and return user profile',
    'Permissions': 'Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'User profile',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked or token expired'},
        403: {'Description': 'Token not found or invalid'},
    }
}


@application.route('/user', methods=['POST'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def add_user(admin: Client) -> dict:  # noqa: unused client
    """Add new user profile."""
    disallow_parameters(request)
    profile = require_data(request, data_format='json', validate=(lambda data: User.from_dict(data)))
    try:
        user_id = profile.pop('id', None)
        if not user_id:
            user_id = User.add(profile).id
        else:
            User.update(user_id, **profile)
    except IntegrityError as error:
        raise ConstraintViolation(str(error.args[0])) from error
    return {'user': {'id': user_id}}


info['Endpoints']['/user']['POST'] = {
    'Description': 'Add or overwrite user profile',
    'Permissions': 'Admin (level 0)',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Payload': {
            'Description': 'User profile data',
            'Type': 'application/json',
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'New user ID',
                'Type': 'application/json'
            },
        },
        400: {'Description': 'JSON payload missing, malformed, or invalid'},
        401: {'Description': 'Access level insufficient, revoked, or token expired'},
        403: {'Description': 'Token not found or invalid'},
    }
}


@application.route('/user/<id_or_alias>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def get_user(admin: Client, id_or_alias: Union[int, str]) -> dict:  # noqa: unused client
    """Query for existing user profile."""
    disallow_parameters(request)
    if id_or_alias.isdigit():
        user = User.from_id(id_or_alias)
    else:
        user = User.from_alias(id_or_alias)
    return {'user': user.to_json()}


info['Endpoints']['/user/<user_id>']['GET'] = {
    'Description': 'Request user profile',
    'Permissions': 'Admin (level 0)',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'user_id': {
                'Description': 'Unique ID for user (or `alias`)',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'User profile',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access level insufficient, revoked, or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'User does not exist'},
    }
}


@application.route('/user/<int:user_id>', methods=['PUT'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def update_user(admin: Client, user_id: int) -> dict:  # noqa: unused client
    """Update user profile attributes."""
    try:
        profile = User.update(user_id, **collect_parameters(request, allow_any=True))
    except IntegrityError as error:
        raise ConstraintViolation(str(error.args[0])) from error
    return {'user': profile.to_json()}


info['Endpoints']['/user/<user_id>']['PUT'] = {
    'Description': 'Update user profile attributes',
    'Permissions': 'Admin (level 0)',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'user_id': {
                'Description': 'Unique ID for user',
                'Type': 'Integer',
            }
        },
    },
    'Optional': {
        'Parameters': {
            'first_name': {
                'Description': 'First name for user',
                'Type': 'String'
            },
            'last_name': {
                'Description': 'Last name for user',
                'Type': 'String'
            },
            'email': {
                'Description': 'Email address for user',
                'Type': 'String'
            },
            'alias': {
                'Description': 'Unique alias for user',
                'Type': 'String'
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
                'Description': 'Updated user profile',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access level insufficient, revoked, or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'User does not exist'},
    }
}


@application.route('/user/<int:user_id>', methods=['DELETE'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def delete_user(admin: Client, user_id: int) -> dict:  # noqa: unused client
    """Delete a user profile (assuming no existing relationships)."""
    disallow_parameters(request)
    try:
        User.delete(user_id)
    except IntegrityError as error:
        raise ConstraintViolation(str(error.args[0])) from error
    return {'user': {'id': user_id}}


info['Endpoints']['/user/<user_id>']['DELETE'] = {
    'Description': 'Delete user profile (assuming no existing relationships)',
    'Permissions': 'Admin (level 0)',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
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
        404: {'Description': 'User does not exist'},
    }
}


@application.route('/user/<int:user_id>/facility', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def get_all_user_facilities(admin: Client, user_id: int) -> dict:  # noqa: unused client
    """Query for facilities related to the given user."""
    disallow_parameters(request)
    return {
        'facility': [
            facility.to_json()
            for facility in User.from_id(user_id).facilities()
        ]
    }


info['Endpoints']['/user/<user_id>/facility']['GET'] = {
    'Description': 'Request facility profiles associated with this user',
    'Permissions': 'Admin (level 0)',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
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
                'Description': 'List of facility profiles',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access level insufficient, revoked, or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'User does not exist'},
    }
}


@application.route('/user/<int:user_id>/facility/<int:facility_id>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def get_user_facility(admin: Client, user_id: int, facility_id: int) -> dict:  # noqa: unused client
    """Query for a facility related to the given user."""
    disallow_parameters(request)
    facilities = [facility.to_json() for facility in User.from_id(user_id).facilities() if facility.id == facility_id]
    if not facilities:
        raise NotFound(f'Facility ({facility_id}) not associated with user ({user_id})')
    else:
        return {'facility': facilities[0]}


info['Endpoints']['/user/<user_id>/facility/<facility_id>']['GET'] = {
    'Description': 'Check facility is associated with this user',
    'Permissions': 'Admin (level 0)',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'user_id': {
                'Description': 'Unique ID for user',
                'Type': 'Integer',
            },
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
                'Description': 'Associated facility profile',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access level insufficient, revoked, or token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'User does not exist or facility not associated with this user'},
    }
}


@application.route('/user/<int:user_id>/facility/<int:facility_id>', methods=['PUT'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def add_user_facility_association(admin: Client, user_id: int, facility_id: int) -> dict:  # noqa: unused client
    """Associate the user with the given facility."""
    disallow_parameters(request)
    User.from_id(user_id).add_facility(facility_id)
    return {}


info['Endpoints']['/user/<user_id>/facility/<facility_id>']['PUT'] = {
    'Description': 'Associate facility with user',
    'Permissions': 'Admin (level 0)',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'user_id': {
                'Description': 'Unique ID for user',
                'Type': 'Integer',
            },
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
        404: {'Description': 'User or facility does not exist'},
    }
}


@application.route('/user/<int:user_id>/facility/<int:facility_id>', methods=['DELETE'])
@endpoint('application/json')
@authenticated
@authorization(level=0)
def delete_user_facility_association(admin: Client, user_id: int, facility_id: int) -> dict:  # noqa: unused client
    """Dissociate the user with the given facility."""
    disallow_parameters(request)
    User.from_id(user_id).delete_facility(facility_id)
    return {}


info['Endpoints']['/user/<user_id>/facility/<facility_id>']['DELETE'] = {
    'Description': 'Disassociate facility with user',
    'Permissions': 'Admin (level 0)',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'user_id': {
                'Description': 'Unique ID for user',
                'Type': 'Integer',
            },
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
        404: {'Description': 'User or facility does not exist'},
    }
}
