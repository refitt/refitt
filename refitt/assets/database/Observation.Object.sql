-- Copyright REFITT Team 2019. All rights reserved.
--
-- This program is free software: you can redistribute it and/or modify it under the
-- terms of the Apache License (v2.0) as published by the Apache Software Foundation.
--
-- This program is distributed in the hope that it will be useful, but WITHOUT ANY
-- WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
-- PARTICULAR PURPOSE. See the Apache License for more details.
--
-- You should have received a copy of the Apache License along with this program.
-- If not, see <https://www.apache.org/licenses/LICENSE-2.0>.

CREATE TABLE "Observation"."Object"
(
    "ObjectID" bigserial NOT NULL,
    "ObjectTypeID" bigint NOT NULL,
    "ObjectRA" double precision NOT NULL,
    "ObjectDec" double precision NOT NULL,
    "ObjectRedShift" double precision,
    "ObjectName" character varying (80) NOT NULL,
    PRIMARY KEY ("ObjectID"),
    CONSTRAINT "ObjectTypeID" FOREIGN KEY ("ObjectTypeID")
        REFERENCES "Observation"."ObjectType" ("ObjectTypeID") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

COMMENT ON TABLE "Observation"."Object"
    IS 'All unique objects (from "Data").';

COMMENT ON CONSTRAINT "ObjectTypeID" ON "Observation"."Object"
    IS 'Associates with "ObjectType"."ObjectTypeID"';
