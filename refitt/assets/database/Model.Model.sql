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

CREATE TABLE "Model"."Model"
(
    "ModelID" bigserial NOT NULL,
    "ModelName" text NOT NULL,
    "ModelTime" timestamp with time zone NOT NULL,
    "ModelData" bytea NOT NULL,
    "ModelHash" character(64),
    "ModelTypeID" bigint NOT NULL,
    PRIMARY KEY ("ModelID"),
    CONSTRAINT "ModelTypeID" FOREIGN KEY ("ModelTypeID")
        REFERENCES "Model"."ModelType" ("ModelTypeID") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

COMMENT ON CONSTRAINT "ModelTypeID" ON "Model"."Model"
    IS 'References "ModelType"."ModelTypeID"';

CREATE INDEX "ModelTypeID"
    ON "Model"."Model" USING btree
    ("ModelTypeID" ASC NULLS LAST)
    TABLESPACE pg_default;