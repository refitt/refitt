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

"""Set of database query templates."""

USER = """\
SELECT
    "User"."UserID"                as "user_id",
    "User"."UserName"              as "user_name",
    "User"."UserProfile"           as "user_profile",
    "User"."UserLatitude"          as "user_latitude",
    "User"."UserLongitude"         as "user_longitude",
    "User"."UserElevation"         as "user_elevation",
    "User"."UserLimitingMagnitude" as "user_limiting_magnitude"

FROM
    "User"."User" as "User"
"""

USER_WHERE_USER_ID = """\
    "User"."UserID" = {user_id}
"""

USER_WHERE_USER_NAME = """\
    "User"."UserName" = {user_name}
"""

# TODO: a better scheme for doing comparative filtering (e.g., range based).


AUTH = """\
SELECT
    "Auth"."AuthID"    as "auth_id",
    "Auth"."AuthLevel" as "auth_level",
    "Auth"."AuthKey"   as "auth_key",
    "Auth"."AuthToken" as "auth_token",
    "Auth"."AuthValid" as "auth_valid",
    "Auth"."AuthTime"  as "auth_time",
    "Auth"."UserID"    as "user_id"

FROM
    "User"."Auth" as "Auth"
"""

AUTH_WHERE_AUTH_ID = """\
    "Auth"."AuthID" = {auth_id}
"""

AUTH_WHERE_AUTH_LEVEL = """\
    "Auth"."AuthLevel" = {auth_level}
"""

AUTH_WHERE_AUTH_KEY = """\
    "Auth"."AuthKey" = '{auth_key}'
"""

AUTH_WHERE_AUTH_TOKEN = """\
    "Auth"."AuthToken" = '{auth_token}'
"""

AUTH_WHERE_AUTH_VALID = """\
    "Auth"."AuthValid" = {auth_valid}
"""

AUTH_WHERE_AUTH_TIME = """\
    "Auth"."AuthTime" = '{auth_time}'
"""

AUTH_WHERE_USER_ID = """\
    "Auth"."UserID" = {user_id}
"""

OBJECT_TYPE = """\
SELECT
    "ObjectType"."ObjectTypeID"   AS "object_type_id",
    "ObjectType"."ObjectTypeName" AS "object_type_name",
    "ObjectType"."ObjectTypeDescription" AS "object_type_description"

FROM 
    "Observation"."ObjectType" as "ObjectType"
"""

OBJECT_TYPE_WHERE_OBJECT_TYPE_ID = """\
    "ObjectType"."ObjectTypeID" = {object_type_id}
"""

OBJECT_TYPE_WHERE_OBJECT_TYPE_NAME = """\
    "ObjectType"."ObjectTypeName" = '{object_type_name}'
"""

OBJECT_TYPE_WHERE_OBJECT_TYPE_DESCRIPTION = """\
    "ObjectType"."ObjectTypeDescription" LIKE '{object_type_description}'
"""

OBJECT = """\
SELECT
    "Object"."ObjectID"           AS "object_id",
    "Object"."ObjectName"         AS "object_name",
    "Object"."ObjectRA"           AS "object_ra",
    "Object"."ObjectDec"          AS "object_dec",
    "Object"."ObjectRedShift"     AS "object_redshift",
    "ObjectType"."ObjectTypeName" AS "object_typename"

FROM
    "Observation"."Object" AS "Object"

LEFT JOIN
    "Observation"."ObjectType" AS "ObjectType"
    ON "Object"."ObjectTypeID" = "ObjectType"."ObjectTypeID"
"""

OBJECT_WHERE_OBJECTTYPE = """\
    "Object"."ObjectTypeID"
    IN (
        SELECT
            "ObjectType"."ObjectTypeID"
        FROM
            "Observation"."ObjectType" as "ObjectType"
        WHERE
            "ObjectTypeName" LIKE '{object_type}'
    )
"""

OBJECT_WHERE_OBJECTRA = """\
    "Object"."ObjectRA" {OP} {VALUE}
"""
