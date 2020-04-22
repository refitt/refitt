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
-- The user_profile is similar to the metadata fields in other tables and provides
-- a catch-all for adding metadata regarding the user; in this case however, every
-- one of the top-level fields will ALSO be included in the user_profile.

CREATE TABLE IF NOT EXISTS "profile"."user"
(
    "user_id"         BIGSERIAL NOT NULL,
    "user_first_name" TEXT      NOT NULL,                      -- e.g., "Jane"
    "user_last_name"  TEXT      NOT NULL,                      -- e.g., "Smith"
    "user_email"      TEXT      NOT NULL,                      -- e.g., "jane.smith@university.edu"
    "user_alias"      TEXT      NOT NULL,                      -- e.g., "jsmith"
    "user_metadata"   JSONB     NOT NULL  DEFAULT '{}'::jsonb, -- e.g., {"availability": ..., }

    PRIMARY KEY ("user_id"),
	UNIQUE ("user_email"),
	UNIQUE ("user_alias")
)
WITH (
    OIDS = FALSE
);