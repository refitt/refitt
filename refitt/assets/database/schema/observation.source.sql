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
    "source_id"          BIGSERIAL NOT NULL,
    "source_type_id"     BIGINT    NOT NULL,
    "facility_id"        BIGINT,                                 -- IFF from an observer
    "user_id"            BIGINT,                                 -- IFF from an observer
    "source_name"        TEXT      NOT NULL,                     -- e.g., "antares"
    "source_description" TEXT      NOT NULL,                     -- e.g., "The Arizona-NOAO Temporal ... (ANTARES)"
    "source_metadata"    JSONB     NOT NULL DEFAULT '{}'::jsonb, -- e.g., "{"url": https://antares.noao.edu", ...}"

    PRIMARY KEY ("source_id"),
	UNIQUE ("source_name"),

    CONSTRAINT "source_type_id" FOREIGN KEY ("source_type_id")
        REFERENCES "observation"."source_type" ("source_type_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,

    CONSTRAINT "facility_id" FOREIGN KEY ("facility_id")
        REFERENCES "profile"."facility" ("facility_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,
    
    CONSTRAINT "user_id" FOREIGN KEY ("user_id")
        REFERENCES "profile"."user" ("user_id") MATCH FULL
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

CREATE INDEX IF NOT EXISTS "user_id"
    ON "observation"."source" USING btree
    ("user_id" ASC NULLS LAST);