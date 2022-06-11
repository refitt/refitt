# SPDX-FileCopyrightText: 2019-2022 REFITT Team
# SPDX-License-Identifier: Apache-2.0

"""REFITT's REST-API implementation."""


# internal libs
from refitt.web.api.app import application
from refitt.web.api.endpoint import token, client, user, facility, object, source, observation, epoch, recommendation
