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

CREATE TABLE IF NOT EXISTS "model"."type"
(
    "type_id"          BIGSERIAL NOT NULL,
    "type_name"        TEXT      NOT NULL, -- e.g., "auto-encoder"
    "type_format"      TEXT      NOT NULL, -- e.g., "hdf5"
    "type_description" TEXT      NOT NULL, -- e.g., "Convolutional auto-encoder weights."

    PRIMARY KEY ("type_id"),
	UNIQUE ("type_name")
)
WITH (
    OIDS = FALSE
);