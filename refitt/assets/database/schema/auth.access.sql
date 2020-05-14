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
-- Tokens are meant to expire at some point in time. Some tokens may be given an
-- expiration time so far in to the future as to suggest non-expiration.

CREATE TABLE IF NOT EXISTS "auth"."access"
(
    "access_id"      BIGSERIAL                NOT NULL,
    "client_id"      BIGINT                   NOT NULL,
    "access_token"   CHARACTER(64)            NOT NULL, -- SHA256 hash of JWT
    "access_expires" TIMESTAMP WITH TIME ZONE,  -- null means never

    PRIMARY KEY ("access_id"),

    CONSTRAINT "client_id" FOREIGN KEY ("client_id")
        REFERENCES "auth"."client" ("client_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

CREATE INDEX IF NOT EXISTS "client_id"
    ON "auth"."access" USING btree
    ("client_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "access_expires"
    ON "auth"."access" USING btree
    ("access_expires" ASC NULLS LAST);