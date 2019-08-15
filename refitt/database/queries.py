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

OBJECT_TYPE = """\
SELECT *
FROM "Observation"."ObjectType"
"""

OBJECT = """\
SELECT
	"Object"."ObjectID"           AS "ObjectID",
	"Object"."ObjectName"         AS "ObjectName",
	"Object"."ObjectRA"           AS "ObjectRA",
	"Object"."ObjectDec"          AS "ObjectDec",
	"Object"."ObjectRedShift"     AS "ObjectRedShift",
	"ObjectType"."ObjectTypeName" AS "ObjectTypeName"

FROM
	"Observation"."Object" AS "Object"

LEFT JOIN
	"Observation"."ObjectType" AS "ObjectType"
	ON "Object"."ObjectTypeID" = "ObjectType"."ObjectTypeID"
"""

OBJECT_WHERE_OBJECTTYPE = """\
	"Object"."ObjectTypeID"
	IN (
		SELECT "ObjectType"."ObjectTypeID"
		FROM "Observation"."ObjectType" as "ObjectType"	
		WHERE "ObjectTypeName" LIKE '{object_type}'
    )
"""

OBJECT_WHERE_OBJECTRA = """\
	"Object"."ObjectRA" {OP} {VALUE}
"""

