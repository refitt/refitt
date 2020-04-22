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

CREATE TABLE IF NOT EXISTS "profile"."facility_map"
(
    "facility_map_id" BIGSERIAL NOT NULL,
    "facility_id"     BIGINT    NOT NULL,
    "user_id"         BIGINT    NOT NULL,

    PRIMARY KEY ("facility_map_id"),
    UNIQUE ("user_id", "facility_id"),  -- only need to record relationship once

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

CREATE INDEX IF NOT EXISTS "facility_id"
    ON "profile"."facility_map" USING btree
    ("facility_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "user_id"
    ON "profile"."facility_map" USING btree
    ("user_id" ASC NULLS LAST);