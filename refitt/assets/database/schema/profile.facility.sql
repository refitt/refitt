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

-- NOTES:
-- The facility_profile is similar to the metadata fields in other tables and provides
-- a catch-all for adding metadata regarding the facility. In this case however, every
-- one of the top-level fields will ALSO be included in the facility_profile.

CREATE TABLE IF NOT EXISTS "profile"."facility"
(
    "facility_id"                 BIGSERIAL        NOT NULL,
    "facility_name"               TEXT             NOT NULL, -- e.g., "keck"
    "facility_latitude"           DOUBLE PRECISION NOT NULL,
    "facility_longitude"          DOUBLE PRECISION NOT NULL,
    "facility_altitude"           DOUBLE PRECISION NOT NULL,
    "facility_limiting_magnitude" DOUBLE PRECISION NOT NULL,
    "facility_metadata"           JSONB            NOT NULL  DEFAULT '{}'::jsonb, -- e.g., {"diameter": ..., }

    PRIMARY KEY ("facility_id"),
	UNIQUE("facility_name")
)
WITH (
    OIDS = FALSE
);

CREATE INDEX IF NOT EXISTS "facility_latitude"
    ON "profile"."facility" USING btree
    ("facility_latitude" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "facility_longitude"
    ON "profile"."facility" USING btree
    ("facility_longitude" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "facility_altitude"
    ON "profile"."facility" USING btree
    ("facility_altitude" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "facility_limiting_magnitude"
    ON "profile"."facility" USING btree
    ("facility_limiting_magnitude" ASC NULLS LAST);