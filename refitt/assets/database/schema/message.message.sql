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

CREATE TABLE IF NOT EXISTS "message"."message"
(
    "message_id"   BIGSERIAL                NOT NULL,
    "topic_id"     BIGINT                   NOT NULL,
    "level_id"     BIGINT                   NOT NULL,
    "host_id"      BIGINT                   NOT NULL,
    "message_time" TIMESTAMP WITH TIME ZONE NOT NULL,
    "message_text" TEXT                     NOT NULL,

    PRIMARY KEY ("message_id"),

    CONSTRAINT "topic_id" FOREIGN KEY ("topic_id")
        REFERENCES "message"."topic" ("topic_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,

    CONSTRAINT "level_id" FOREIGN KEY ("level_id")
        REFERENCES "message"."level" ("level_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID,

    CONSTRAINT "host_id" FOREIGN KEY ("host_id")
        REFERENCES "message"."host" ("host_id") MATCH FULL
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
        NOT VALID
)
WITH (
    OIDS = FALSE
);

CREATE INDEX IF NOT EXISTS "topic_id"
    ON "message"."message" USING btree
    ("topic_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "level_id"
    ON "message"."message" USING btree
    ("level_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "host_id"
    ON "message"."message" USING btree
    ("host_id" ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS "message_time"
    ON "message"."message" USING btree
    ("message_time" ASC NULLS LAST);