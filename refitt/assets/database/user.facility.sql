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

CREATE TABLE IF NOT EXISTS "user"."facility"
(
    "facility_id" BIGSERIAL NOT NULL,

    "facility_name" TEXT NOT NULL,
    "facility_latitude" DOUBLE PRECISION NOT NULL,
    "facility_longitude" DOUBLE PRECISION NOT NULL,
    "facility_altitude" DOUBLE PRECISION NOT NULL,
    "facility_limiting_magnitude" DOUBLE PRECISION NOT NULL,
    "facility_profile" JSONB NOT NULL,

    PRIMARY KEY ("facility_id"),
	UNIQUE("facility_name")
)
WITH (
    OIDS = FALSE
);
