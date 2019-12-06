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

CREATE TABLE IF NOT EXISTS "observation"."object"
(
    "object_id" BIGSERIAL NOT NULL,

    "object_type_id" BIGINT NOT NULL,

    "object_name" TEXT NOT NULL,
    "object_aliases" JSONB,
    "object_ra" DOUBLE PRECISION NOT NULL,
    "object_dec" DOUBLE PRECISION NOT NULL,
    "object_redshift" DOUBLE PRECISION,

    PRIMARY KEY ("object_id"),
	UNIQUE("object_name"),

    CONSTRAINT "object_type_id" FOREIGN KEY ("object_type_id")
        REFERENCES "observation"."object_type" ("object_type_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

CREATE INDEX IF NOT EXISTS "object_type_id"
    ON "observation"."object" USING btree
    ("object_type_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "object_name"
    ON "observation"."object" USING btree
    ("object_name" ASC NULLS LAST);
