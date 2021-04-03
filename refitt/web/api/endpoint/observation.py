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

"""Observation endpoints."""


# type annotations
from typing import Tuple, IO

# standard libs
from io import BytesIO
from functools import partial

# external libs
from flask import request

# internal libs
from ....database.core import Session
from ....database.model import Client, Source, Observation, ObservationType, Alert, Forecast, File, FileType
from ..app import application
from ..response import endpoint, PermissionDenied, PayloadTooLarge
from ..auth import authenticated, authorization
from ..tools import collect_parameters, disallow_parameters


info: dict = {
    'Description': 'Request observations',
    'Endpoints': {
        '/observation': {},
        '/observation/<id>': {},
        '/observation/<id>/object': {},
        '/observation/<id>/object/type': {},
        '/observation/<id>/type': {},
        '/observation/<id>/source': {},
        '/observation/<id>/source/type': {},
        '/observation/<id>/source/user': {},
        '/observation/<id>/source/facility': {},
        '/observation/<id>/alert': {},
        '/observation/<id>/forecast': {},
        '/observation/<id>/file': {},
        '/observation/<id>/file/type': {},
        '/observation/type/<id>': {},
        '/observation/alert/<id>': {},
        '/observation/forecast/<id>': {},
        '/observation/file/<id>': {},
        '/observation/file/<id>/type': {},
        '/observation/file/type/<id>': {},
    }
}


def is_public(obs: Observation, client: Client) -> bool:
    """Filter out user sourced observations if not admin."""
    return not (obs.source.user_id is not None and obs.source.user_id != client.user_id and client.user_id > 1)


@application.route('/observation', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_many(client: Client) -> dict:
    """Query for observations with filters."""
    filters = ['source_id', 'object_id', 'limit']
    params = collect_parameters(request, optional=filters+['join', ], defaults={'join': False})
    join = params.pop('join')
    if not params:
        raise PayloadTooLarge(f'Must specify at least one of {filters}')
    query = Session.query(Observation).order_by(Observation.id)
    if 'source_id' in params:
        source_id = params['source_id']
        query = query.filter(Observation.source_id == source_id)
        if Source.from_id(source_id).type.name == 'broker' and 'limit' not in params and 'object_id' not in params:
            raise PayloadTooLarge(f'Cannot query all observations for broker (source_id={source_id})')
    if 'object_id' in params:
        query = query.filter(Observation.object_id == params['object_id'])
    if 'limit' in params:
        query = query.limit(params['limit'])
    return {'observation': [obs.to_json(join=join)
                            for obs in filter(partial(is_public, client=client), query.all())]}


info['Endpoints']['/observation']['GET'] = {
    'Description': 'Request observation data',
    'Permissions': 'Public',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for forecast',
                'Type': 'Integer',
            }
        },
    },
    'Optional': {
        'Parameters': {
            'source_id': {
                'Description': 'Unique ID for source',
                'Type': 'Integer'
            },
            'object_id': {
                'Description': 'Unique ID for object',
                'Type': 'Integer'
            },
            'limit': {
                'Description': 'Limit on number of returned observations (default: none)',
                'Type': 'Integer'
            },
            'join': {
                'Description': 'Include related data',
                'Type': 'Boolean'
            },
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Observation data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired'},
        403: {'Description': 'Token not found or invalid'},
        413: {'Description': 'Too few filters'}
    }
}


def _get_observation(id: int, client: Client) -> Observation:
    obs = Observation.from_id(id)
    if obs.source.user_id and obs.source.user_id != client.user_id and client.level != 0:
        raise PermissionDenied(f'Observation is not public')
    else:
        return obs


@application.route('/observation/<int:id>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_observation(client: Client, id: int) -> dict:
    """Query for observation by `id`."""
    params = collect_parameters(request, optional=['join'], defaults={'join': False})
    return {'observation': _get_observation(id, client).to_json(**params)}


info['Endpoints']['/observation/<id>']['GET'] = {
    'Description': 'Request observation by ID',
    'Permissions': 'Public/Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for observation',
                'Type': 'Integer',
            }
        },
    },
    'Optional': {
        'Parameters': {
            'join': {
                'Description': 'Include related data',
                'Type': 'Boolean'
            }
        }
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Observation data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Observation does not exist'},
    }
}


@application.route('/observation/<int:id>/object', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_observation_object(client: Client, id: int) -> dict:
    """Query for object of observation by `id`."""
    params = collect_parameters(request, optional=['join'], defaults={'join': False})
    return {'object': _get_observation(id, client).object.to_json(**params)}


info['Endpoints']['/observation/<id>/object']['GET'] = {
    'Description': 'Request object of observation by ID',
    'Permissions': 'Public/Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for observation',
                'Type': 'Integer',
            }
        },
    },
    'Optional': {
        'Parameters': {
            'join': {
                'Description': 'Include related data',
                'Type': 'Boolean'
            }
        }
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Object data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Observation does not exist'},
    }
}


@application.route('/observation/<int:id>/object/type', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_observation_object_type(client: Client, id: int) -> dict:
    """Query for object type of observation by `id`."""
    disallow_parameters(request)
    return {'object_type': _get_observation(id, client).object.type.to_json()}


info['Endpoints']['/observation/<id>/object/type']['GET'] = {
    'Description': 'Request object type of observation by ID',
    'Permissions': 'Public/Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for observation',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Object type data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Observation does not exist'},
    }
}


@application.route('/observation/<int:id>/type', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_observation_type(client: Client, id: int) -> dict:
    """Query for observation type of observation by `id`."""
    disallow_parameters(request)
    return {'observation_type': _get_observation(id, client).type.to_json()}


info['Endpoints']['/observation/<id>/type']['GET'] = {
    'Description': 'Request observation type of observation by ID',
    'Permissions': 'Public/Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for observation',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Observation type data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Observation does not exist'},
    }
}


@application.route('/observation/<int:id>/source', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_observation_source(client: Client, id: int) -> dict:
    """Query for source of observation by `id`."""
    params = collect_parameters(request, optional=['join'], defaults={'join': False})
    return {'source': _get_observation(id, client).source.to_json(**params)}


info['Endpoints']['/observation/<id>/source']['GET'] = {
    'Description': 'Request source of observation by ID',
    'Permissions': 'Public/Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for observation',
                'Type': 'Integer',
            }
        },
    },
    'Optional': {
        'Parameters': {
            'join': {
                'Description': 'Include related data',
                'Type': 'Boolean'
            }
        }
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Source data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Observation does not exist'},
    }
}


@application.route('/observation/<int:id>/source/type', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_observation_source_type(client: Client, id: int) -> dict:
    """Query for source type of observation by `id`."""
    disallow_parameters(request)
    return {'source_type': _get_observation(id, client).source.type.to_json()}


info['Endpoints']['/observation/<id>/source/type']['GET'] = {
    'Description': 'Request source type of observation by ID',
    'Permissions': 'Public/Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for observation',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Source type data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Observation does not exist'},
    }
}


@application.route('/observation/<int:id>/source/user', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_observation_source_user(client: Client, id: int) -> dict:
    """Query for source user of observation by `id`."""
    disallow_parameters(request)
    return {'user': _get_observation(id, client).source.user.to_json()}


info['Endpoints']['/observation/<id>/source/user']['GET'] = {
    'Description': 'Request source user of observation by ID',
    'Permissions': 'Public/Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for observation',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'User profile data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Observation does not exist'},
    }
}


@application.route('/observation/<int:id>/source/facility', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_observation_source_facility(client: Client, id: int) -> dict:
    """Query for source facility of observation by `id`."""
    disallow_parameters(request)
    return {'facility': _get_observation(id, client).source.facility.to_json()}


info['Endpoints']['/observation/<id>/source/facility']['GET'] = {
    'Description': 'Request source facility of observation by ID',
    'Permissions': 'Public/Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for observation',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Facility profile data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Observation does not exist'},
    }
}


@application.route('/observation/<int:id>/alert', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_observation_alert(client: Client, id: int) -> dict:
    """Query for alert related to observation by `id`."""
    disallow_parameters(request)
    return {'alert': Alert.from_observation(_get_observation(id, client).id).data}


info['Endpoints']['/observation/<id>/alert']['GET'] = {
    'Description': 'Request alert related to observation by ID',
    'Permissions': 'Public/Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for observation',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Alert data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Observation or alert does not exist'},
    }
}


@application.route('/observation/<int:id>/forecast', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_observation_forecast(client: Client, id: int) -> dict:
    """Query for forecast related to observation by `id`."""
    disallow_parameters(request)
    return {'forecast': Forecast.from_observation(_get_observation(id, client).id).data}


info['Endpoints']['/observation/<id>/forecast']['GET'] = {
    'Description': 'Request forecast related to observation by ID',
    'Permissions': 'Public/Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for observation',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Forecast data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired, or unauthorized'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Observation or forecast does not exist'},
    }
}


@application.route('/observation/<int:id>/file', methods=['GET'])
@endpoint('application/octet-stream')
@authenticated
@authorization(level=None)
def get_observation_file(client: Client, id: int) -> Tuple[IO, dict]:
    """Query for file related to observation by `id`."""
    disallow_parameters(request)
    file = File.from_observation(id)
    if file.observation.source.user_id != client.user_id and client.level > 1:
        raise PermissionDenied('File is not public')
    return BytesIO(file.data), {
        'as_attachment': True,
        'attachment_filename': f'observation_{id}.{file.type.name}',
        'conditional': False,
    }


info['Endpoints']['/observation/<id>/file']['GET'] = {
    'Description': 'Request file related to observation by ID',
    'Permissions': 'Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for observation',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'File attachment',
                'Type': 'application/octet-stream'
            },
        },
        401: {'Description': 'Access revoked, token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Observation or file does not exist'},
    }
}


@application.route('/observation/<int:id>/file/type', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_observation_file_type(client: Client, id: int) -> dict:
    """Query for file type of file related to observation by `id`."""
    disallow_parameters(request)
    file = File.from_observation(id)
    if file.observation.source.user_id != client.user_id and client.level > 1:
        raise PermissionDenied('File is not public')
    return {'file_type': file.type.to_json(), }


info['Endpoints']['/observation/<id>/file/type']['GET'] = {
    'Description': 'Request type for file related to observation by ID',
    'Permissions': 'Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for observation',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'File type data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Observation or file does not exist'},
    }
}


@application.route('/observation/type/<int:id>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_type(client: Client, id: int) -> dict:  # noqa: unused client
    """Query for observation type by `id`."""
    disallow_parameters(request)
    return {'observation_type': ObservationType.from_id(id).to_json()}


info['Endpoints']['/observation/type/<id>']['GET'] = {
    'Description': 'Request observation type by ID',
    'Permissions': 'Public',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for observation type',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Observation type data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Observation type does not exist'},
    }
}


@application.route('/observation/alert/<int:id>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_alert(client: Client, id: int) -> dict:  # noqa: unused client
    """Query for alert by `id`."""
    disallow_parameters(request)
    return {'alert': Alert.from_id(id).data}


info['Endpoints']['/observation/alert/<id>']['GET'] = {
    'Description': 'Request alert by ID',
    'Permissions': 'Public',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for alert',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Alert data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Alert does not exist'},
    }
}


@application.route('/observation/forecast/<int:id>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_forecast(client: Client, id: int) -> dict:  # noqa: unused client
    """Query for forecast by `id`."""
    disallow_parameters(request)
    return {'forecast': Forecast.from_id(id).data}


info['Endpoints']['/observation/forecast/<id>']['GET'] = {
    'Description': 'Request forecast by ID',
    'Permissions': 'Public',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for forecast',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'Forecast data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'Forecast does not exist'},
    }
}


@application.route('/observation/file/<int:id>', methods=['GET'])
@endpoint('application/octet-stream')
@authenticated
@authorization(level=None)
def get_file(client: Client, id: int) -> Tuple[IO, dict]:
    """Query for observation file by `id`."""
    disallow_parameters(request)
    file = File.from_id(id)
    if file.observation.source.user_id != client.user_id and client.level > 1:
        raise PermissionDenied('File is not public')
    return BytesIO(file.data), {
        'as_attachment': True,
        'attachment_filename': f'observation_{file.observation_id}.{file.type.name}',
        'conditional': False,
    }


info['Endpoints']['/observation/file/<id>']['GET'] = {
    'Description': 'Request observation file by ID',
    'Permissions': 'Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for file',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'File attachment',
                'Type': 'application/octet-stream'
            },
        },
        401: {'Description': 'Access revoked, token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'File does not exist'},
    }
}


@application.route('/observation/file/<int:id>/type', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_type_for_file(client: Client, id: int) -> dict:
    """Query for file type of observation file by file `id`."""
    disallow_parameters(request)
    file = File.from_id(id)
    if file.observation.source.user_id != client.user_id and client.level > 1:
        raise PermissionDenied('File is not public')
    return {'file_type': file.type.to_json(), }


info['Endpoints']['/observation/file/<id>/type']['GET'] = {
    'Description': 'Request file type for observation file by file ID',
    'Permissions': 'Owner',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for file',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'File type data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'File does not exist'},
    }
}


@application.route('/observation/file/type/<int:id>', methods=['GET'])
@endpoint('application/json')
@authenticated
@authorization(level=None)
def get_file_type(client: Client, id: int) -> dict:  # noqa: unused client
    """Query for file type by `id`."""
    disallow_parameters(request)
    return {'file_type': FileType.from_id(id).to_json(), }


info['Endpoints']['/observation/file/type/<id>']['GET'] = {
    'Description': 'Request file type by ID',
    'Permissions': 'Public',
    'Requires': {
        'Auth': 'Authorization Bearer Token',
        'Path': {
            'id': {
                'Description': 'Unique ID for file type',
                'Type': 'Integer',
            }
        },
    },
    'Responses': {
        200: {
            'Description': 'Success',
            'Payload': {
                'Description': 'File type data',
                'Type': 'application/json'
            },
        },
        401: {'Description': 'Access revoked, token expired'},
        403: {'Description': 'Token not found or invalid'},
        404: {'Description': 'File type does not exist'},
    }
}
