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

CREATE TABLE "User"."Auth"
(
    "AuthID" bigserial NOT NULL,
    "AuthLevel" smallint NOT NULL,
    "AuthKey" character(16) NOT NULL,
    "AuthToken" character(64) NOT NULL,
    "AuthValid" boolean NOT NULL,
    "UserID" bigint NOT NULL,
    PRIMARY KEY ("AuthID"),
    CONSTRAINT "UserID" FOREIGN KEY ("AuthID")
        REFERENCES "User"."User" ("UserID") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

COMMENT ON TABLE "User"."Auth"
    IS 'User (admin or observing agent) authorization.';

COMMENT ON CONSTRAINT "UserID" ON "User"."Auth"
    IS 'References unique user identification (from "User").';

CREATE INDEX "UserID"
    ON "User"."Auth" USING btree
    ("UserID" ASC NULLS LAST)
    TABLESPACE pg_default;