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
-- The client_level is used to distinguish levels of privilege in the system, lower levels
-- are more privileged. Level-0 is REFITT itself. Level-1 is for administrators. Level-2
-- is for sophisticated observers that have been given more privilege. Level-3+ is a bit
-- open ended at this point and just means un-privileged.

CREATE TABLE IF NOT EXISTS "auth"."client"
(
    "client_id"      BIGSERIAL                NOT NULL,
    "user_id"        BIGINT                   NOT NULL,
    "client_level"   SMALLINT                 NOT NULL,  -- 0 is root, 1 is admin, 2+ is other
    "client_key"     CHARACTER(16)            NOT NULL,  -- 128bit hex token (clear)
    "client_secret"  CHARACTER(64)            NOT NULL,  -- SHA256 hash of 256bit hex token
    "client_valid"   BOOLEAN                  NOT NULL  DEFAULT TRUE, -- new credentials are valid on creation
    "client_created" TIMESTAMP WITH TIME ZONE NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY ("client_id"),
    UNIQUE ("client_key"),

    CONSTRAINT "user_id" FOREIGN KEY ("user_id")
        REFERENCES "profile"."user" ("user_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

CREATE INDEX IF NOT EXISTS "user_id"
    ON "auth"."client" USING btree
    ("user_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "client_level"
    ON "auth"."client" USING btree
    ("client_level" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "client_valid"
    ON "auth"."client" USING btree
    ("client_valid" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "client_created"
    ON "auth"."client" USING btree
    ("client_created" ASC NULLS LAST);
