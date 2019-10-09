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

CREATE TABLE "Observation"."SupplementalData"
(
    "SupplementalDataID" bigserial NOT NULL,
    "SupplementalData" json,
    "ObservationID" bigint NOT NULL,
    PRIMARY KEY ("SupplementalDataID"),
    CONSTRAINT "ObservationID" FOREIGN KEY ("ObservationID")
        REFERENCES "Observation"."Observation" ("ObservationID") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

COMMENT ON TABLE "Observation"."SupplementalData"
    IS 'Arbitrary JSON blobs linked to "Observation" table.';
COMMENT ON CONSTRAINT "ObservationID" ON "Observation"."SupplementalData"
    IS 'Reference to the unique observation identifier (from "Observation").';

CREATE INDEX "ObservationID"
    ON "Observation"."SupplementalData" USING btree
    ("ObservationID" ASC NULLS LAST)
    TABLESPACE pg_default;

COMMENT ON INDEX "Observation"."ObservationID"
    IS 'Index on foreign key "ObservationID".';
