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

CREATE TABLE IF NOT EXISTS "observation"."source"
(
    "source_id" BIGSERIAL NOT NULL,

    "source_type_id" BIGINT NOT NULL,
    "facility_id" BIGINT,

    "source_name" TEXT NOT NULL,
    "source_description" TEXT,
    "source_reference" TEXT,

    PRIMARY KEY ("source_id"),
	UNIQUE("source_name"),

    CONSTRAINT "source_type_id" FOREIGN KEY ("source_type_id")
        REFERENCES "observation"."source_type" ("source_type_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,

    CONSTRAINT "facility_id" FOREIGN KEY ("facility_id")
        REFERENCES "user"."facility" ("facility_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

CREATE INDEX IF NOT EXISTS "source_type_id"
    ON "observation"."source" USING btree
    ("source_type_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "facility_id"
    ON "observation"."source" USING btree
    ("facility_id" ASC NULLS LAST);
