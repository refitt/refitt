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

CREATE TABLE IF NOT EXISTS "message"."server"
(
    "server_id"   BIGSERIAL     NOT NULL,
    "host_id"     BIGINT        NOT NULL,
    "server_port" INT           NOT NULL, -- e.g., 8000
    "server_key"  CHARACTER(64) NOT NULL, -- e.g., e09d...c488

    PRIMARY KEY ("server_id"),
	UNIQUE ("host_id", "server_port"),

    CONSTRAINT "host_id" FOREIGN KEY ("host_id")
        REFERENCES "message"."host" ("host_id") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);