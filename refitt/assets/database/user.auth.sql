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

CREATE TABLE IF NOT EXISTS "user"."auth"
(
    "auth_id" BIGSERIAL NOT NULL,

    "user_id" BIGINT NOT NULL,

    "auth_level" SMALLINT NOT NULL,
    "auth_key" CHARACTER(16) NOT NULL,
    "auth_token" CHARACTER(64) NOT NULL,
    "auth_valid" BOOLEAN NOT NULL,
    "auth_time" TIMESTAMP WITH TIME ZONE NOT NULL,
    
    PRIMARY KEY ("auth_id"),

    CONSTRAINT "user_id" FOREIGN KEY ("user_id")
        REFERENCES "user"."user" ("user_id") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

CREATE INDEX IF NOT EXISTS "user_id"
    ON "user"."auth" USING btree
    ("user_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "auth_key"
	ON "user"."auth" USING btree
	("auth_key" ASC NULLS LAST);
