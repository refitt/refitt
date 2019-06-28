
CREATE SCHEMA "Observation";


-----------------------------------------------------------------------------------

CREATE TABLE "Observation"."ObjectType" (
    
    "ObjectTypeID"    BIGSERIAL PRIMARY KEY,
    
    "ObjectTypeName"  VARCHAR(80) NOT NULL,
    "ObjectTypeNotes" TEXT
);

INSERT INTO "Observation"."ObjectType" ("ObjectTypeName", "ObjectTypeNotes")
VALUES
    ('supernova', DEFAULT)

RETURNING "ObjectTypeID";

SELECT
    "ObjectTypeID",
    "ObjectTypeName",
    "ObjectTypeNotes"

FROM "Observation"."ObjectType";


-----------------------------------------------------------------------------------

CREATE TABLE "Observation"."ObjectSubType" (
    
    "ObjectSubTypeID"    BIGSERIAL PRIMARY KEY,
    
    "ObjectSubTypeName"  VARCHAR(80) NOT NULL,
    "ObjectSubTypeNotes" TEXT,

    "ObjectTypeID"       BIGINT REFERENCES "Observation"."ObjectType" ("ObjectTypeID")
);

INSERT INTO "Observation"."ObjectSubType" ("ObjectSubTypeName", "ObjectSubTypeNotes", "ObjectTypeID")
VALUES
    ('I-a',  DEFAULT, (SELECT "ObjectTypeID" from "Observation"."ObjectType" as obs where obs."ObjectTypeName" = 'supernova')),
    ('II-b', DEFAULT, (SELECT "ObjectTypeID" from "Observation"."ObjectType" as obs where obs."ObjectTypeName" = 'supernova'))

RETURNING "ObjectSubTypeID";

SELECT
    "ObjectSubTypeID",
    "ObjectSubTypeName",
    "ObjectSubTypeNotes",
    "ObjectTypeID"

FROM "Observation"."ObjectSubType";


-----------------------------------------------------------------------------------

CREATE TABLE "Observation"."Source" (

    "SourceID"     BIGSERIAL PRIMARY KEY,
    "SourceName"   VARCHAR(256) NOT NULL, -- e.g., "Antares", "SDSS-III-dr12"
    "SourceNotes"  TEXT
);

INSERT INTO "Observation"."Source" ("SourceName", "SourceNotes")
VALUES
    ('Antares', DEFAULT)

RETURNING "SourceID";

SELECT
    "SourceID",
    "SourceName",
    "SourceNotes"

FROM "Observation"."Source";


-----------------------------------------------------------------------------------

CREATE TABLE "Observation"."Object" (
    
    "ObjectID"        BIGSERIAL PRIMARY KEY,
    "ObjectName"      VARCHAR(256), -- not necessarily available
    "ObjectRA"        DOUBLE PRECISION, -- decimal degrees
    "ObjectDec"       DOUBLE PRECISION, -- decimal degrees
    "ObjectDistance"  DOUBLE PRECISION, -- Mega parsecs?
    "ObjectNotes"     TEXT,  -- anything

    "ObjectSubTypeID" BIGINT REFERENCES "Observation"."ObjectSubType" ("ObjectSubTypeID"),
    "ObjectTypeID"    BIGINT REFERENCES "Observation"."ObjectType" ("ObjectTypeID"),
    "SourceID"  BIGINT REFERENCES "Observation"."Source" ("SourceID")

);

INSERT INTO "Observation"."Object" ("ObjectName", "ObjectRA", "ObjectDec", "ObjectDistance", 
                                    "ObjectNotes", "ObjectSubTypeID", "ObjectTypeID", "ObjectSourceID")
VALUES
RETURNING "ObjectID";

SELECT
    "ObjectID",
    "ObjectName",
    "ObjectRA",
    "ObjectDec",
    "ObjectDistance",
    "ObjectNotes",
    "ObjectSubTypeID",
    "ObjectTypeID",
    "ObjectSourceID"

FROM "Observation"."Object";

-----------------------------------------------------------------------------------

select * from information_schema.tables;