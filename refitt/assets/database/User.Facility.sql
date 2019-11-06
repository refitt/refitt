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

CREATE TABLE "User"."Facility"
(
    "FacilityID" bigserial NOT NULL,
    "FacilityName" text NOT NULL,
    "FacilityProfile" jsonb NOT NULL,
    "FacilityLatitude" double precision NOT NULL,
    "FacilityLongitude" double precision NOT NULL,
    "FacilityAltitude" double precision NOT NULL,
    "FacilityLimitingMagnitude" double precision NOT NULL,
    PRIMARY KEY ("FacilityID")
)
WITH (
    OIDS = FALSE
);

COMMENT ON TABLE "User"."Facility"
    IS 'Facility specifications used by observing agents';