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

CREATE TABLE "Observation"."Observation"
(
    "ObservationID" bigserial NOT NULL,
    "ObservationTime" timestamp with time zone NOT NULL,
    "ObservationValue" double precision NOT NULL,
    "ObservationUncertainty" double precision NOT NULL,
    "ObservationReferenceTime" timestamp with time zone NOT NULL,
    "ObservationTypeID" bigint NOT NULL,
    "ObjectID" bigint NOT NULL,
    "SourceID" bigint NOT NULL,
    PRIMARY KEY ("ObservationID"),
    CONSTRAINT "ObservationTypeID" FOREIGN KEY ("ObservationTypeID")
        REFERENCES "Observation"."ObservationType" ("ObservationTypeID") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,
    CONSTRAINT "ObjectID" FOREIGN KEY ("ObjectID")
        REFERENCES "Observation"."Object" ("ObjectID") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,
    CONSTRAINT "SourceID" FOREIGN KEY ("SourceID")
        REFERENCES "Observation"."Source" ("SourceID") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

COMMENT ON TABLE "Observation"."Observation"
    IS 'All observational data.';
COMMENT ON CONSTRAINT "ObservationTypeID" ON "Observation"."Observation"
    IS 'Reference to the unique observation type identifier (from "ObservationType").';
COMMENT ON CONSTRAINT "ObjectID" ON "Observation"."Observation"
    IS 'Reference to the unique object identifier (from "Object").';
COMMENT ON CONSTRAINT "SourceID" ON "Observation"."Observation"
    IS 'Reference to the unique source identifier (from "Source").';

CREATE INDEX "ObservationTypeID"
    ON "Observation"."Observation" USING btree
    ("ObservationTypeID" ASC NULLS LAST)
    TABLESPACE pg_default;

COMMENT ON INDEX "Observation"."ObservationTypeID"
    IS 'Index on foreign key "ObservationTypeID".';

CREATE INDEX "ObjectID"
    ON "Observation"."Observation" USING btree
    ("ObjectID" ASC NULLS LAST)
    TABLESPACE pg_default;

COMMENT ON INDEX "Observation"."ObjectID"
    IS 'Index on foreign key "ObjectID".';

CREATE INDEX "SourceID"
    ON "Observation"."Observation" USING btree
    ("SourceID" ASC NULLS LAST)
    TABLESPACE pg_default;

COMMENT ON INDEX "Observation"."SourceID"
    IS 'Index on foreign key "SourceID".';
